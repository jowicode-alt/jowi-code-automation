"""Render vertical Shorts with safe framing and burned-in, readable captions."""
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap


def _timestamp(seconds: float) -> str:
    milliseconds = max(0, int(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def _write_captions(text: str, duration: float, directory: Path) -> Path:
    """Create evenly paced, wrapped SRT captions from the spoken narration."""
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        clean = "The Jowi Code — Master Your Mind. Build Your Future."
    words = clean.split()
    chunks = []
    current = []
    for word in words:
        current.append(word)
        if len(current) >= 7 or len(" ".join(current)) >= 38:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    chunks = ["\n".join(textwrap.wrap(chunk, width=38)) for chunk in chunks]
    weights = [max(1, len(re.sub(r"\W", "", chunk))) for chunk in chunks]
    total_weight = sum(weights)
    cursor = 0.0
    entries = []
    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        end = duration if index == len(chunks) else cursor + duration * weight / total_weight
        entries.extend([str(index), f"{_timestamp(cursor)} --> {_timestamp(end)}", chunk, ""])
        cursor = end
    path = directory / "captions.srt"
    path.write_text("\n".join(entries), encoding="utf-8")
    return path


def _caption_filter(srt_path: Path) -> str:
    escaped = str(srt_path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return (
        f"subtitles='{escaped}':force_style="
        "'FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101010,BorderStyle=1,Outline=3,Shadow=1,"
        "Alignment=2,MarginL=100,MarginR=100,MarginV=300,"
        "WrapStyle=2,Bold=1'"
    )


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


def render_short(scene_images: list[str], audio_path: str, output_path: str, narration: str = "") -> str:
    """Render four scene images without cropping their edges, with on-screen captions."""
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
    with tempfile.TemporaryDirectory(prefix="jowi-captions-") as temp:
        srt = _write_captions(narration, duration, Path(temp))
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
        filters.append(f"{joined}concat=n={len(images)}:v=1:a=0[vconcat]")
        filters.append(f"[vconcat]{_caption_filter(srt)}[vout]")
        command += [
            "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", f"{len(images)}:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac",
            "-b:a", "128k", "-t", f"{duration:.3f}", "-movflags", "+faststart", str(target),
        ]
        return _render(command, target)


def render_news_short(video_clips: list[str], audio_path: str, output_path: str, narration: str = "") -> str:
    """Render a 9:16 news Short with licensed moving footage, safe framing, and captions."""
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
    with tempfile.TemporaryDirectory(prefix="jowi-news-captions-") as temp:
        srt = _write_captions(narration, duration, Path(temp))
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
        filters.append(f"{joined}concat=n={len(clips)}:v=1:a=0[vconcat]")
        filters.append(f"[vconcat]{_caption_filter(srt)}[vout]")
        command += [
            "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", f"{len(clips)}:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-c:a", "aac",
            "-b:a", "128k", "-t", f"{duration:.3f}", "-movflags", "+faststart", str(target),
        ]
        return _render(command, target, timeout=240)
