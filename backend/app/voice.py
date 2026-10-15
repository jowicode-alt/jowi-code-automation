"""Optional no-key neural voiceover adapter with word-level timing metadata."""
import os
from pathlib import Path


async def generate_voiceover_with_boundaries(text: str, output_path: str) -> tuple[str, list[dict]]:
    """Save the exact synthesized audio and collect its provider word-boundary timings."""
    if not text.strip():
        raise ValueError("Voiceover text cannot be empty")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    voice = os.getenv("TTS_VOICE", "en-US-GuyNeural")
    rate = os.getenv("TTS_RATE", "-5%")
    pitch = os.getenv("TTS_PITCH", "-8Hz")
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    audio_parts = []
    boundaries = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            audio_parts.append(chunk["data"])
        elif chunk.get("type") == "WordBoundary":
            boundaries.append({
                "text": chunk.get("text", ""),
                "offset": int(chunk.get("offset", 0)),
                "duration": int(chunk.get("duration", 0)),
            })
    target.write_bytes(b"".join(audio_parts))
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("Voice provider returned no audio file")
    return str(target), boundaries


async def generate_voiceover(text: str, output_path: str) -> str:
    """Backward-compatible voiceover API."""
    path, _ = await generate_voiceover_with_boundaries(text, output_path)
    return path
