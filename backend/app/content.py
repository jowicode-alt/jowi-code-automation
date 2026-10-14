"""Brand-safe deterministic Shorts planner; media generation is a separate provider step."""

CHARACTER_STYLE = (
    "Photorealistic anthropomorphic black male lion, black suit, crisp white shirt, "
    "gold tie, gold eyes, serious expression with no smile; cinematic realistic lighting. "
    "Vertical 9:16 framing. Keep the same character identity across every scene."
)


def build_short_plan(topic: str) -> dict:
    clean_topic = " ".join(topic.split()).strip(" .!?")
    if len(clean_topic) < 3:
        raise ValueError("Topic must contain at least three non-space characters")
    title = clean_topic[:90]
    narration = (
        f"Your future will not change just because you wish for it. Start taking action on {clean_topic.lower()} today. "
        "Small disciplined steps, repeated when motivation fades, build real progress. "
        "Stop waiting for perfect conditions. Learn, act, review, and improve every day. "
        "Master your mind. Build your future. Subscribe to The Jowi Code. Thanks for watching."
    )
    scene_beats = [
        ("Hook", "The lion stands still in a dark, elegant office, direct serious gaze, slow cinematic push-in."),
        ("Challenge", "The lion walks one measured step forward through a minimal modern office, controlled camera tracking."),
        ("Action", "The lion studies a notebook at a desk, closes it decisively, then looks toward the horizon; no readable text."),
        ("Close", "The lion faces camera in a confident, composed pose with subtle warm gold rim light; hold for the closing line."),
    ]
    scenes = [
        {
            "number": index,
            "beat": beat,
            "visual_prompt": f"{CHARACTER_STYLE} {visual} No captions, subtitles, logos, typing effects, snapping effects, or ether effects.",
        }
        for index, (beat, visual) in enumerate(scene_beats, start=1)
    ]
    return {
        "channel": "The Jowi Code",
        "tagline": "Master Your Mind. Build Your Future.",
        "format": "YouTube Short, vertical 9:16",
        "title": title,
        "topic": clean_topic,
        "voice": "Deep male voiceover; steady, deliberate delivery; no on-screen captions.",
        "narration": narration,
        "scenes": scenes,
        "generation_status": "plan_only_provider_not_configured",
        "publishing_enabled": False,
    }
