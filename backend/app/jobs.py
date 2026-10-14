"""Durable job queue with explicit lifecycle fields.

PostgreSQL is used when DATABASE_URL is configured; SQLite is for local development.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import uuid

JOB_FIELDS = (
    "id", "job_type", "topic", "status", "created_at_utc",
    "updated_at_utc", "error", "result_json",
)
ALLOWED_TRANSITIONS = {
    "queued": {"running", "blocked", "failed"},
    "running": {"completed", "blocked", "failed"},
    "blocked": {"queued"},
    "failed": {"queued"},
    "completed": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        import psycopg
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url[len("postgres://"):]
        connection = psycopg.connect(database_url)
        connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, job_type TEXT NOT NULL, topic TEXT NOT NULL,
            status TEXT NOT NULL, created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT, error TEXT, result_json TEXT
        )""")
        connection.commit()
        columns = {row[0] for row in connection.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'jobs' AND table_schema = current_schema()"
        ).fetchall()}
        for name, sql_type in (("updated_at_utc", "TEXT"), ("error", "TEXT"), ("result_json", "TEXT")):
            if name not in columns:
                connection.execute(f"ALTER TABLE jobs ADD COLUMN {name} {sql_type}")
        connection.commit()
        return connection, True

    path = Path(os.getenv("JOB_DB_PATH", "./data/jobs.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, job_type TEXT NOT NULL, topic TEXT NOT NULL,
        status TEXT NOT NULL, created_at_utc TEXT NOT NULL,
        updated_at_utc TEXT, error TEXT, result_json TEXT
    )""")
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(jobs)").fetchall()}
    for name, sql_type in (("updated_at_utc", "TEXT"), ("error", "TEXT"), ("result_json", "TEXT")):
        if name not in columns:
            connection.execute(f"ALTER TABLE jobs ADD COLUMN {name} {sql_type}")
    return connection, False


@contextmanager
def _database():
    connection, is_postgres = _connect()
    try:
        yield connection, is_postgres
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _query(sql: str, is_postgres: bool) -> str:
    return sql.replace("?", "%s") if is_postgres else sql


def _as_dict(row, is_postgres: bool) -> dict:
    return dict(zip(JOB_FIELDS, row)) if is_postgres else dict(row)


def enqueue_job(job_type: str, topic: str) -> dict:
    now = _now()
    job_id = str(uuid.uuid4())
    with _database() as (db, is_postgres):
        count = db.execute(
            _query("SELECT COUNT(*) FROM jobs WHERE created_at_utc >= ?", is_postgres),
            (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),),
        ).fetchone()[0]
        if count >= 3:
            raise ValueError("Daily job limit reached (maximum 3 jobs per UTC day)")
        db.execute(
            _query("INSERT INTO jobs (id, job_type, topic, status, created_at_utc, updated_at_utc, error, result_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", is_postgres),
            (job_id, job_type, topic.strip(), "queued", now, now, None, None),
        )
    return {
        "id": job_id, "job_type": job_type, "topic": topic.strip(),
        "status": "queued", "created_at_utc": now, "updated_at_utc": now,
        "error": None, "result": None,
    }


def list_jobs(limit: int = 20) -> list[dict]:
    with _database() as (db, is_postgres):
        rows = db.execute(
            _query("SELECT id, job_type, topic, status, created_at_utc, updated_at_utc, error, result_json FROM jobs ORDER BY created_at_utc DESC LIMIT ?", is_postgres),
            (limit,),
        ).fetchall()
    jobs = [_as_dict(row, is_postgres) for row in rows]
    for job in jobs:
        raw = job.pop("result_json")
        job["result"] = json.loads(raw) if raw else None
    return jobs


def get_job(job_id: str) -> dict | None:
    with _database() as (db, is_postgres):
        row = db.execute(
            _query("SELECT id, job_type, topic, status, created_at_utc, updated_at_utc, error, result_json FROM jobs WHERE id = ?", is_postgres),
            (job_id,),
        ).fetchone()
    if row is None:
        return None
    job = _as_dict(row, is_postgres)
    raw = job.pop("result_json")
    job["result"] = json.loads(raw) if raw else None
    return job



def claim_next_job() -> dict | None:
    """Atomically claim the oldest queued job; suitable for a single worker process.

    The conditional update prevents two workers from both claiming the same row.
    A deployment should still run only one worker until concurrency is load-tested.
    """
    with _database() as (db, is_postgres):
        row = db.execute(
            _query(
                "SELECT id FROM jobs WHERE status = ? ORDER BY created_at_utc ASC LIMIT 1",
                is_postgres,
            ),
            ("queued",),
        ).fetchone()
        if row is None:
            return None
        job_id = row[0]
        cursor = db.execute(
            _query(
                "UPDATE jobs SET status = ?, updated_at_utc = ?, error = NULL "
                "WHERE id = ? AND status = ?",
                is_postgres,
            ),
            ("running", _now(), job_id, "queued"),
        )
        if cursor.rowcount != 1:
            return None
    return get_job(job_id)


def update_job_status(job_id: str, status: str, *, error: str | None = None, result: dict | None = None) -> dict | None:
    """Apply a valid lifecycle transition and return the updated job."""
    with _database() as (db, is_postgres):
        row = db.execute(
            _query("SELECT status FROM jobs WHERE id = ?", is_postgres), (job_id,)
        ).fetchone()
        if row is None:
            return None
        current = row[0]
        if status not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(f"Invalid job status transition: {current} -> {status}")
        db.execute(
            _query("UPDATE jobs SET status = ?, updated_at_utc = ?, error = ?, result_json = ? WHERE id = ?", is_postgres),
            (status, _now(), error, json.dumps(result) if result is not None else None, job_id),
        )
    return get_job(job_id)
