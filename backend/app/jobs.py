"""SQLite-backed development job queue. Use managed PostgreSQL for production durability."""
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import uuid


def _connect() -> sqlite3.Connection:
    path = Path(os.getenv("JOB_DB_PATH", "./data/jobs.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        job_type TEXT NOT NULL,
        topic TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at_utc TEXT NOT NULL
    )""")
    return connection


def enqueue_job(job_type: str, topic: str) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    job_id = str(uuid.uuid4())
    with _connect() as db:
        count = db.execute(
            "SELECT COUNT(*) FROM jobs WHERE created_at_utc >= ?",
            (now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),),
        ).fetchone()[0]
        if count >= 3:
            raise ValueError("Daily job limit reached (maximum 3 jobs per UTC day)")
        db.execute(
            "INSERT INTO jobs (id, job_type, topic, status, created_at_utc) VALUES (?, ?, ?, ?, ?)",
            (job_id, job_type, topic.strip(), "queued", now.isoformat()),
        )
    return {"id": job_id, "job_type": job_type, "topic": topic.strip(), "status": "queued", "created_at_utc": now.isoformat()}


def list_jobs(limit: int = 20) -> list[dict[str, str]]:
    with _connect() as db:
        rows = db.execute(
            "SELECT id, job_type, topic, status, created_at_utc FROM jobs ORDER BY created_at_utc DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
