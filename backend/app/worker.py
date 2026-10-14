"""One-shot queue worker. It never claims success without real media and upload verification."""
from app.content import build_short_plan
from app.jobs import claim_next_job, update_job_status

BLOCKED_REASON = (
    "Automatic scene-image generation is not implemented/configured. "
    "The script and scene prompts were saved, but no video was rendered or uploaded."
)


def run_once() -> dict:
    """Process at most one queued job, failing closed when required providers are absent."""
    job = claim_next_job()
    if job is None:
        return {"state": "idle", "message": "No queued jobs."}
    try:
        plan = build_short_plan(job["topic"])
        # A key alone does not mean a working provider adapter exists. Do not fabricate media.
        update_job_status(
            job["id"], "blocked", error=BLOCKED_REASON,
            result={"plan": plan, "media_created": False, "youtube_upload": None},
        )
        return {"state": "blocked", "job_id": job["id"], "reason": BLOCKED_REASON}
    except Exception as exc:
        message = f"Worker could not prepare this job: {type(exc).__name__}: {exc}"
        update_job_status(job["id"], "failed", error=message)
        return {"state": "failed", "job_id": job["id"], "reason": message}


if __name__ == "__main__":
    import json
    print(json.dumps(run_once(), ensure_ascii=False))
