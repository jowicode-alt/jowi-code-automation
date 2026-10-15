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


def _write_captions(text: str, duration: float, directory: Path, word_boundaries: list[dict] | None = None) -> Path:
    """Write compact captions aligned to actual TTS word timings where available."""
    path = directory / "captions.srt"
    entries = []
    timed_words = []
    for item in word_boundaries or []:
        word = str(item.get("text", "")).strip()
        if not word:
            continue
        offset = int(item.get("offset", 0))
        length = int(item.get("duration", 0))
        start = max(0.0, offset / 10_000_000)
        finish = min(duration, max(start + 0.08, (offset + length) / 10_000_000))
        timed_words.append((word, start, finish))

    if timed_words:
        groups, group = [], []
        for item in timed_words:
            proposed = " ".join([part[0] for part in group] + [item[0]])
            if group and (len(group) >= 5 or len(proposed) > 30 or item[1] - group[0][1] > 2.8):
                groups.append(group)
                group = []
            group.append(item)
        if group:
            groups.append(group)
        for index, group in enumerate(groups, start=1):
            phrase = " ".join(part[0] for part in group)
            start_time = max(0.0, group[0][1] - 0.04)
            end_time = min(duration, max(group[-1][2] + 0.12, start_time + 0.35))
            if index < len(groups):
                end_time = min(end_time, max(start_time + 0.2, groups[index][0][1] - 0.02))
            entries.extend([str(index), f"{_timestamp(start_time)} --> {_timestamp(end_time)}", phrase, ""])
    else:
        # Fallback when the speech provider does not expose word boundaries.
        clean = re.sub(r"\s+", " ", text).strip()
        words = clean.split()
        chunks, current = [], []
        for word in words:
            proposed = " ".join(current + [word])
            if current and (len(current) >= 5 or len(proposed) > 30):
                chunks.append(" ".join(current))
                current = []
            current.append(word)
        if current:
            chunks.append(" ".join(current))
        weights = [max(1, len(re.sub(r"\W", "", chunk))) for chunk in chunks]
        total_weight = sum(weights) or 1
        cursor = 0.0
        for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
            finish = duration if index == len(chunks) else cursor + duration * weight / total_weight
            entries.extend([str(index), f"{_timestamp(cursor)} --> {_timestamp(finish)}", chunk, ""])
            cursor = finish

    path.write_text("\n".join(entries), encoding="utf-8")
    return path

def _caption_filter(srt_path: Path) -> str:
    escaped = str(srt_path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return (
        f"subtitles='{escaped}':force_style="
        "'FontName=Arial,FontSize=27,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101010,BorderStyle=1,Outline=2,Shadow=1,"
        "Alignment=5,MarginL=140,MarginR=140,MarginV=0,"
        "WrapStyle=2,Bold=0'"
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


def render_short(scene_images: list[str], audio_path: str, output_path: str, narration: str = "", word_boundaries: list[dict] | None = None) -> str:
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
        srt = _write_captions(narration, duration, Path(temp), word_boundaries)
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


def render_news_short(video_clips: list[str], audio_path: str, output_path: str, narration: str = "", word_boundaries: list[dict] | None = None) -> str:
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
