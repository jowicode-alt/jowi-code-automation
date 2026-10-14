"""Optional no-key neural voiceover adapter; requires outbound internet at generation time."""
import os
from pathlib import Path


async def generate_voiceover(text: str, output_path: str) -> str:
    if not text.strip():
        raise ValueError("Voiceover text cannot be empty")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    voice = os.getenv("TTS_VOICE", "en-US-GuyNeural")
    rate = os.getenv("TTS_RATE", "-5%")
    pitch = os.getenv("TTS_PITCH", "-8Hz")
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(target))
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("Voice provider returned no audio file")
    return str(target)
