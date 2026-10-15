"""Pipeline orchestration for a private draft from pre-generated scene images."""
import asyncio
from pathlib import Path
import uuid

from app.content import build_short_plan
from app.render import render_short
from app.voice import generate_voiceover
from app.youtube import upload_video_private


async def build_private_draft(
    topic: str,
    scene_images: list[str],
    output_dir: str = "/tmp/jowi-code-output",
    category: str | None = None,
) -> dict[str, str]:
    """Create narration, render a vertical Short, and upload it to YouTube as PRIVATE.

    Scene images must already exist. This function deliberately has no public-publish path.
    """
    if len(scene_images) != 4 or any(not Path(item).is_file() for item in scene_images):
        raise ValueError("Four existing scene images are required; image generation is not part of this step")
    plan = build_short_plan(topic, category=category)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    audio_path = directory / f"{run_id}.mp3"
    video_path = directory / f"{run_id}.mp4"
    try:
        await generate_voiceover(plan["narration"], str(audio_path))
        await asyncio.to_thread(render_short, scene_images, str(audio_path), str(video_path))
        source_lines = [
            f'{source.get("source", "Source")}: {source.get("url", "")}'
            for source in plan.get("sources", [])
            if source.get("url", "").startswith(("https://", "http://"))
        ]
        source_section = (
            "Sources checked during draft preparation:\\n" + "\\n".join(source_lines)
            if source_lines else
            "Sources must be checked before any public release."
        )
        description = (
            f'{plan["tagline"]}\\n\\n{plan["narration"]}\\n\\n'
            f'{source_section}\\n\\n'
            "This video is an original summary; consult linked sources for primary reporting.\\n\\n"
            "Subscribe to The Jowi Code. Thanks for watching."
        )
        tags_by_category = {
            "breaking_news": ["The Jowi Code", "world news", "news update", "explainer"],
            "ai_technology": ["The Jowi Code", "AI tools", "technology", "tutorial"],
            "comedy": ["The Jowi Code", "comedy", "original comedy", "shorts"],
            "entertainment": ["The Jowi Code", "entertainment", "commentary", "shorts"],
            "money_success": ["The Jowi Code", "success", "personal development", "shorts"],
            "psychology": ["The Jowi Code", "psychology", "human behaviour", "shorts"],
        }
        result = await asyncio.to_thread(
            upload_video_private,
            str(video_path),
            plan["title"],
            description,
            tags_by_category.get(plan["category"], ["The Jowi Code", "shorts"]),
        )
        return {
            "video_id": result["video_id"],
            "privacy_status": "private",
            "title": plan["title"],
            "category": plan["category"],
            "status": "uploaded_private",
        }
    finally:
        audio_path.unlink(missing_ok=True)
        video_path.unlink(missing_ok=True)
