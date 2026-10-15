"""Render vertical Shorts with safe framing and no on-screen captions."""
from pathlib import Path
import subprocess
import tempfile


def _probe_duration(audio: Path) -> float:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
         "default=noprint_wrappers=1:nokey=1", str(audio)],
        check=True, capture_output=True, text=True, timeout=20,
    )
    duration = float(probe.stdout.strip())
    if duration <= 0:
        raise ValueError("Voiceover audio has invalid duration")
    return duration


def _render(command: list[str], target: Path, timeout: int = 240) -> str:
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("FFmpeg did not produce a video file")
    return str(target)


def render_short(scene_images: list[str], audio_path: str, output_path: str, narration: str = "", word_boundaries: list[dict] | None = None) -> str:
    """Render four scene images with voiceover, without captions or subtitles."""
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
    duration = _probe_duration(audio)
    scene_duration = duration / len(images)
    with tempfile.TemporaryDirectory(prefix="jowi-scenes-") as temp:
        command = ["ffmpeg", "-y"]
        for image in images:
            command += ["-loop", "1", "-framerate", "30", "-t", f"{scene_duration:.3f}", "-i", str(image)]
        command += ["-i", str(audio)]
        filters = []
        for index in range(len(images)):
            filters.append(
                f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
                f"fps=30,format=yuv420p[v{index}]"
            )
        joined = "".join(f"[v{index}]" for index in range(len(images)))
        filters.append(f"{joined}concat=n={len(images)}:v=1:a=0[vout]")
        command += [
            "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", f"{len(images)}:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac",
            "-b:a", "128k", "-t", f"{duration:.3f}", "-movflags", "+faststart", str(target),
        ]
        return _render(command, target)


def render_news_short(video_clips: list[str], audio_path: str, output_path: str, narration: str = "", word_boundaries: list[dict] | None = None) -> str:
    """Render a 9:16 news Short with licensed moving footage and voiceover, no captions."""
    if not video_clips:
        raise ValueError("At least one licensed moving news clip is required")
    clips = [Path(item) for item in video_clips]
    audio = Path(audio_path)
    if any(not clip.is_file() or clip.stat().st_size == 0 for clip in clips):
        raise FileNotFoundError("One or more licensed news clips are missing or empty")
    if not audio.is_file():
        raise FileNotFoundError("News voiceover audio is missing")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    duration = _probe_duration(audio)
    scene_duration = duration / len(clips)
    with tempfile.TemporaryDirectory(prefix="jowi-news-scenes-") as temp:
        command = ["ffmpeg", "-y"]
        for clip in clips:
            command += ["-stream_loop", "-1", "-i", str(clip)]
        command += ["-i", str(audio)]
        filters = []
        for index in range(len(clips)):
            filters.append(
                f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30,"
                f"trim=duration={scene_duration:.3f},setpts=PTS-STARTPTS,format=yuv420p[v{index}]"
            )
        joined = "".join(f"[v{index}]" for index in range(len(clips)))
        filters.append(f"{joined}concat=n={len(clips)}:v=1:a=0[vout]")
        command += [
            "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", f"{len(clips)}:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-c:a", "aac",
            "-b:a", "128k", "-t", f"{duration:.3f}", "-movflags", "+faststart", str(target),
        ]
        return _render(command, target, timeout=240)
