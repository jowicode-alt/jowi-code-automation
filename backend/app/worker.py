"""One-shot queue worker with explicit asset and upload verification."""
import asyncio
import os
from pathlib import Path

from app.content import build_short_plan
from app.jobs import claim_next_job, update_job_status

BLOCKED_REASON = (
    "Four scene images are unavailable. Configure SCENE_ASSETS_DIR with "
    "scene-1.png through scene-4.png; automatic image generation is not integrated."
)


def _scene_images() -> list[str]:
    """Resolve four pre-generated scene images in a deterministic order."""
    raw_dir = os.getenv("SCENE_ASSETS_DIR", "").strip()
    if not raw_dir:
        return []
    directory = Path(raw_dir)
    images = [directory / f"scene-{index}.png" for index in range(1, 5)]
    if any(not image.is_file() for image in images):
        return []
    return [str(image) for image in images]


def run_once() -> dict:
    """Process one job; completion requires a confirmed private YouTube upload."""
    job = claim_next_job()
    if job is None:
        return {"state": "idle", "message": "No queued jobs."}

    try:
        plan = build_short_plan(job["topic"])
        images = _scene_images()
        if len(images) != 4:
            update_job_status(
                job["id"], "blocked", error=BLOCKED_REASON,
                result={"plan": plan, "media_created": False, "youtube_upload": None},
            )
            return {"state": "blocked", "job_id": job["id"], "reason": BLOCKED_REASON}

        # Imported lazily so the planning/blocked path needs no media or YouTube setup.
        from app.pipeline import build_private_draft
        pipeline_result = asyncio.run(build_private_draft(job["topic"], images))
        if (
            pipeline_result.get("status") != "uploaded_private"
            or pipeline_result.get("privacy_status") != "private"
            or not pipeline_result.get("video_id")
        ):
            raise RuntimeError("Pipeline did not confirm a private YouTube upload")

        result = {
            "plan": plan,
            "media_created": True,
            "youtube_upload": {
                "video_id": pipeline_result["video_id"],
                "privacy_status": "private",
                "title": pipeline_result.get("title", plan["title"]),
            },
        }
        update_job_status(job["id"], "completed", result=result)
        return {"state": "completed", "job_id": job["id"], "result": result}
    except Exception as exc:
        message = f"Worker failed before verified completion: {type(exc).__name__}: {exc}"
        update_job_status(job["id"], "failed", error=message)
        return {"state": "failed", "job_id": job["id"], "reason": message}


if __name__ == "__main__":
    import json
    print(json.dumps(run_once(), ensure_ascii=False))
