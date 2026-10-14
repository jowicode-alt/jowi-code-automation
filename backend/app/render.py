"""Assemble four scene images and voiceover into a vertical MP4 using FFmpeg."""
from pathlib import Path
import subprocess


def render_short(scene_images: list[str], audio_path: str, output_path: str) -> str:
    if len(scene_images) != 4:
        raise ValueError("A Jowi Code Short requires exactly four scene images")
    images = [Path(item) for item in scene_images]
    audio = Path(audio_path)
    if any(not image.is_file() for image in images):
        raise FileNotFoundError("One or more scene images are missing")
    if not audio.is_file():
        raise FileNotFoundError("Voiceover audio is missing")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
        check=True, capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip())
    if duration <= 0:
        raise ValueError("Voiceover audio has invalid duration")
    scene_duration = duration / len(images)
    command = ["ffmpeg", "-y"]
    for image in images:
        command += ["-loop", "1", "-framerate", "30", "-t", f"{scene_duration:.3f}", "-i", str(image)]
    command += ["-i", str(audio)]
    filters = []
    for index in range(len(images)):
        filters.append(f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,format=yuv420p[v{index}]")
    joined = "".join(f"[v{index}]" for index in range(len(images)))
    filters.append(f"{joined}concat=n={len(images)}:v=1:a=0[vout]")
    command += [
        "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", f"{len(images)}:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac",
        "-b:a", "128k", "-t", f"{duration:.3f}", "-movflags", "+faststart", str(target),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("FFmpeg did not produce a video file")
    return str(target)
