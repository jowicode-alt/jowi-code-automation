"""Durable queue adapter: PostgreSQL when DATABASE_URL is set, SQLite for local development."""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import uuid


def _connect():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        import psycopg
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url[len("postgres://"):]
        connection = psycopg.connect(database_url)
        connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, job_type TEXT NOT NULL, topic TEXT NOT NULL,
            status TEXT NOT NULL, created_at_utc TEXT NOT NULL
        )""")
        connection.commit()
        return connection, True
    path = Path(os.getenv("JOB_DB_PATH", "./data/jobs.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, job_type TEXT NOT NULL, topic TEXT NOT NULL,
        status TEXT NOT NULL, created_at_utc TEXT NOT NULL
    )""")
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


def enqueue_job(job_type: str, topic: str) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    job_id = str(uuid.uuid4())
    with _database() as (db, is_postgres):
        count = db.execute(
            _query("SELECT COUNT(*) FROM jobs WHERE created_at_utc >= ?", is_postgres),
            (now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),),
        ).fetchone()[0]
        if count >= 3:
            raise ValueError("Daily job limit reached (maximum 3 jobs per UTC day)")
        db.execute(
            _query("INSERT INTO jobs (id, job_type, topic, status, created_at_utc) VALUES (?, ?, ?, ?, ?)", is_postgres),
            (job_id, job_type, topic.strip(), "queued", now.isoformat()),
        )
    return {"id": job_id, "job_type": job_type, "topic": topic.strip(), "status": "queued", "created_at_utc": now.isoformat()}


def list_jobs(limit: int = 20) -> list[dict[str, str]]:
    with _database() as (db, is_postgres):
        rows = db.execute(
            _query("SELECT id, job_type, topic, status, created_at_utc FROM jobs ORDER BY created_at_utc DESC LIMIT ?", is_postgres),
            (limit,),
        ).fetchall()
    if is_postgres:
        return [dict(zip(("id", "job_type", "topic", "status", "created_at_utc"), row)) for row in rows]
    return [dict(row) for row in rows]
