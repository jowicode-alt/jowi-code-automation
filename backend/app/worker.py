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

    plan = None
    temp_assets = None
    media_source = "pre_generated_assets"
    try:
        category = job.get("job_type", "money_success")
        if category == "short_video":
            category = "money_success"
        plan = build_short_plan(job["topic"], category=category)
        if category == "breaking_news" and not plan.get("source_review_ready", False):
            message = (
                "News draft blocked: fewer than two corroborating publisher sources were "
                "found for this exact topic. No media was generated or uploaded."
            )
            update_job_status(
                job["id"], "blocked", error=message,
                result={"plan": plan, "media_created": False, "youtube_upload": None},
            )
            return {"state": "blocked", "job_id": job["id"], "reason": message}
        images = _existing_scene_images()
        if not images:
            from app.image_provider import generate_scene_images
            temp_assets = tempfile.TemporaryDirectory(prefix="jowi-scenes-")
            prompts = [scene["visual_prompt"] for scene in plan["scenes"]]
            try:
                images = asyncio.run(generate_scene_images(prompts, temp_assets.name))
                media_source = "ai_horde"
            except Exception as provider_exc:
                from app.fallback_art import generate_fallback_scene_images
                try:
                    images = generate_fallback_scene_images(temp_assets.name)
                    media_source = "local_branded_fallback"
                    print(
                        "Image provider unavailable; continuing with local branded "
                        f"fallback. Provider error: {type(provider_exc).__name__}: {provider_exc}"
                    )
                except Exception as fallback_exc:
                    message = (
                        f"{BLOCKED_REASON} Provider detail: {type(provider_exc).__name__}: "
                        f"{provider_exc}. Local fallback also failed: "
                        f"{type(fallback_exc).__name__}: {fallback_exc}"
                    )
                    update_job_status(
                        job["id"], "blocked", error=message,
                        result={"plan": plan, "media_created": False, "youtube_upload": None},
                    )
                    return {"state": "blocked", "job_id": job["id"], "reason": message}

        from app.pipeline import build_private_draft
        pipeline_result = asyncio.run(
            build_private_draft(job["topic"], images, category=category)
        )
        if (
            pipeline_result.get("status") != "uploaded_private"
            or pipeline_result.get("privacy_status") != "private"
            or not pipeline_result.get("video_id")
        ):
            raise RuntimeError("Pipeline did not confirm a private YouTube upload")

        result = {
            "plan": plan,
            "media_created": True,
            "media_source": media_source,
            "youtube_upload": {
                "video_id": pipeline_result["video_id"],
                "privacy_status": "private",
                "title": pipeline_result.get("title", plan["title"]),
                "category": category,
            },
        }
        update_job_status(job["id"], "completed", result=result)
        return {"state": "completed", "job_id": job["id"], "result": result}
    except Exception as exc:
        message = f"Worker failed before verified completion: {type(exc).__name__}: {exc}"
        update_job_status(
            job["id"], "failed", error=message,
            result={"plan": plan, "media_created": False, "youtube_upload": None}
            if plan is not None else {"media_created": False, "youtube_upload": None},
        )
        return {"state": "failed", "job_id": job["id"], "reason": message}
    finally:
        if temp_assets is not None:
            temp_assets.cleanup()


if __name__ == "__main__":
    import json
    print(json.dumps(run_once(), ensure_ascii=False))
