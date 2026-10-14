"""Pipeline orchestration for a private draft from pre-generated scene images."""
import asyncio
from pathlib import Path
import uuid

from app.content import build_short_plan
from app.render import render_short
from app.voice import generate_voiceover
from app.youtube import upload_video_private


async def build_private_draft(topic: str, scene_images: list[str], output_dir: str = "/tmp/jowi-code-output") -> dict[str, str]:
    """Create narration, render a vertical Short, and upload it to YouTube as PRIVATE.

    Scene images must already exist. This function deliberately has no public-publish path.
    """
    if len(scene_images) != 4 or any(not Path(item).is_file() for item in scene_images):
        raise ValueError("Four existing scene images are required; image generation is not part of this step")
    plan = build_short_plan(topic)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    audio_path = directory / f"{run_id}.mp3"
    video_path = directory / f"{run_id}.mp4"
    try:
        await generate_voiceover(plan["narration"], str(audio_path))
        await asyncio.to_thread(render_short, scene_images, str(audio_path), str(video_path))
        description = f'{plan["tagline"]}\\n\\n{plan["narration"]}\\n\\nSubscribe to The Jowi Code. Thanks for watching.'
        result = await asyncio.to_thread(upload_video_private, str(video_path), plan["title"], description, ["The Jowi Code", "discipline", "mindset", "motivation", "shorts"])
        return {"video_id": result["video_id"], "privacy_status": "private", "title": plan["title"], "status": "uploaded_private"}
    finally:
        audio_path.unlink(missing_ok=True)
        video_path.unlink(missing_ok=True)
