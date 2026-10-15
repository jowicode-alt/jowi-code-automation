"""Create private Shorts from original scene art or licensed moving news footage."""
import asyncio
from pathlib import Path
import uuid

from app.content import build_short_plan
from app.render import render_news_short, render_short
from app.voice import generate_voiceover
from app.youtube import upload_video_private


async def build_private_draft(
    topic: str,
    scene_images: list[str] | None = None,
    output_dir: str = "/tmp/jowi-code-output",
    category: str | None = None,
    news_package: dict | None = None,
) -> dict[str, str]:
    """Create narration, render a vertical Short, and upload it as PRIVATE only.

    Breaking-news jobs must supply a source-reviewed package with licensed moving clips.
    """
    scene_images = scene_images or []
    if news_package is None:
        if len(scene_images) != 4 or any(not Path(item).is_file() for item in scene_images):
            raise ValueError("Four existing scene images are required for a non-news Short")
    else:
        clips = news_package.get("clips", [])
        sources = news_package.get("sources", [])
        if not clips or len(sources) < 2 or not news_package.get("narration", "").strip():
            raise ValueError("News package requires moving footage, article facts, and two sources")
        if any(not Path(item).is_file() for item in clips):
            raise FileNotFoundError("One or more licensed news clips are missing")

    plan = build_short_plan(topic, category=category)
    narration = news_package["narration"] if news_package else plan["narration"]
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    audio_path = directory / f"{run_id}.mp3"
    video_path = directory / f"{run_id}.mp4"
    try:
        await generate_voiceover(narration, str(audio_path))
        if news_package:
            await asyncio.to_thread(render_news_short, news_package["clips"], str(audio_path), str(video_path))
        else:
            await asyncio.to_thread(render_short, scene_images, str(audio_path), str(video_path))

        source_lines = [
            f'{source.get("source", "Source")}: {source.get("url", "")}'
            for source in (news_package.get("sources", []) if news_package else plan.get("sources", []))
            if source.get("url", "").startswith(("https://", "http://"))
        ]
        clip_lines = []
        if news_package:
            for clip in news_package.get("clip_attributions", []):
                clip_lines.append(
                    f'{clip.get("title", "Video clip")} — creator: {clip.get("creator", "Unknown")}; '
                    f'license: {clip.get("license", "See source")}; {clip.get("source_url", "")}'
                )
        source_section = (
            "Reporting sources:\n" + "\n".join(source_lines)
            if source_lines else "Sources must be checked before any public release."
        )
        if clip_lines:
            source_section += "\n\nMoving-footage credits (Wikimedia Commons):\n" + "\n".join(clip_lines)
        description = (
            f'{plan["tagline"]}\n\n{narration}\n\n'
            f'{source_section}\n\n'
            "This is a source-based news summary, not a live broadcast. Details can change; "
            "consult the linked reporting and footage licenses.\n\n"
            "Subscribe to The Jowi Code. Thanks for watching."
        )
        tags_by_category = {
            "breaking_news": ["The Jowi Code", "world news", "news update", "explainer"],
            "ai_technology": ["The Jowi Code", "AI tools", "technology", "tutorial"],
            "comedy": ["The Jowi Code", "comedy", "original comedy", "shorts"],
            "entertainment": ["The Jowi Code", "entertainment", "commentary", "shorts"],
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
