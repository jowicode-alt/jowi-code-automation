"""One-shot queue worker with bounded image generation and private-upload verification."""
import asyncio
import os
from pathlib import Path
import tempfile

from app.content import build_short_plan
from app.jobs import claim_next_job, update_job_status

BLOCKED_REASON = (
    "Image generation could not produce four usable scene images. "
    "Check AI Horde availability, model support, queue time, and network access."
)


def _existing_scene_images() -> list[str]:
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

    plan = build_short_plan(job["topic"])
    temp_assets = None
    try:
        images = _existing_scene_images()
        if not images:
            from app.image_provider import generate_scene_images
            temp_assets = tempfile.TemporaryDirectory(prefix="jowi-scenes-")
            prompts = [scene["visual_prompt"] for scene in plan["scenes"]]
            try:
                images = asyncio.run(generate_scene_images(prompts, temp_assets.name))
            except Exception as exc:
                message = f"{BLOCKED_REASON} Provider detail: {type(exc).__name__}: {exc}"
                update_job_status(
                    job["id"], "blocked", error=message,
                    result={"plan": plan, "media_created": False, "youtube_upload": None},
                )
                return {"state": "blocked", "job_id": job["id"], "reason": message}

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
    finally:
        if temp_assets is not None:
            temp_assets.cleanup()


if __name__ == "__main__":
    import json
    print(json.dumps(run_once(), ensure_ascii=False))
