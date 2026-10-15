"""Category-aware original Shorts planner for The Jowi Code.

Uses topic-appropriate visuals and direct presentation, without the Jowi lion or
storytelling format. News remains a private draft and requires source review.
"""
from __future__ import annotations

from app.channel_strategy import CATEGORY_POLICIES

VALID_CATEGORIES = set(CATEGORY_POLICIES)


def _category(topic: str, category: str | None) -> tuple[str, str]:
    clean = " ".join(topic.split()).strip(" .!?")
    if category is None and clean.startswith("[") and "]" in clean:
        marker, remainder = clean[1:].split("]", 1)
        if marker in VALID_CATEGORIES:
            category, clean = marker, remainder.strip()
    category = category or "comedy"
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unsupported content category: {category}")
    if len(clean) < 3:
        raise ValueError("Topic must contain at least three non-space characters")
    return category, clean


def _scenes(category: str) -> list[tuple[str, str]]:
    if category == "ai_technology":
        return [
            ("Hook", "Show the real tool or workflow immediately in a vertical screen-led frame; no fabricated interface or claims."),
            ("Problem", "Show the task or user problem before the tool is used, with a clear visual hierarchy."),
            ("Demo", "Show a practical step-by-step workflow using original screen capture or licensed visuals; only verified capabilities."),
            ("Result", "Show the actual outcome and one useful limitation or takeaway; clean end frame."),
        ]
    if category == "comedy":
        return [
            ("Hook", "Open on an instantly recognizable everyday situation using original characters and a strong visual reaction."),
            ("Setup", "Show the relatable problem clearly with natural comedic timing."),
            ("Twist", "Deliver an original unexpected visual gag; no copied meme, skit, or borrowed footage."),
            ("Punchline", "Hold the final reaction briefly for the payoff; clean end frame."),
        ]
    if category == "entertainment":
        return [
            ("Hook", "Use a bold original visual that quickly introduces the entertainment topic or trend."),
            ("Context", "Show original or licensed visuals that establish the relevant facts."),
            ("Commentary", "Give a concise original observation or reaction, not a re-upload of third-party clips."),
            ("Close", "Finish with a clear takeaway and clean branded end frame."),
        ]
    return [
        ("What happened", "Use a neutral original newsroom-style graphic with date and location; never present generated imagery as authentic event footage."),
        ("Confirmed facts", "Show a clean timeline or map-style illustration; include only verified facts and label uncertainty."),
        ("Why it matters", "Explain the significance with original graphics that separate confirmed facts from analysis."),
        ("Sources and update", "Show source names and update time; include working source links in the description."),
    ]


def _narration(category: str, topic: str) -> str:
    if category == "ai_technology":
        return (
            f"Here is a practical demonstration of {topic}. Start with the task, test the tool on a real example, "
            "check the output, and compare it with your current workflow. Features and free-plan limits can change, "
            "so verify them before relying on the tool. Subscribe to The Jowi Code. Thanks for watching."
        )
    if category == "comedy":
        return (
            f"POV: {topic}. You had one simple job. Somehow it became a full operation, three excuses, "
            "and a problem nobody remembers starting. And the funniest part? The solution was obvious from the beginning. "
            "Subscribe to The Jowi Code. Thanks for watching."
        )
    if category == "entertainment":
        return (
            f"Here is the key detail about {topic}. What is confirmed, what is reaction, and what is still opinion? "
            "The context matters more than repeating a trend. Follow The Jowi Code for original commentary. Thanks for watching."
        )
    return (
        f"Here is the latest verified update on {topic}. We are separating confirmed information from details that are still developing. "
        "Check the source links in the description for original statements and further updates. If key facts change, this update should be corrected. "
        "Subscribe to The Jowi Code for clear, sourced updates. Thanks for watching."
    )


def build_short_plan(topic: str, category: str | None = None) -> dict:
    selected, clean_topic = _category(topic, category)
    policy = CATEGORY_POLICIES[selected]
    sources = []
    if selected == "breaking_news":
        try:
            from app.news_monitor import sources_for_topic
            sources = sources_for_topic(clean_topic)
        except Exception:
            sources = []
    scenes = [
        {
            "number": index,
            "beat": beat,
            "visual_prompt": f"{visual} Vertical 9:16. No captions baked into imagery, no copied logos, no unauthorized footage.",
        }
        for index, (beat, visual) in enumerate(_scenes(selected), start=1)
    ]
    return {
        "channel": "The Jowi Code",
        "tagline": "Master Your Mind. Build Your Future.",
        "category": selected,
        "format": "YouTube Short, vertical 9:16",
        "presentation": policy.format,
        "title": clean_topic[:90],
        "topic": clean_topic,
        "voice": "Deep male voiceover; clear, natural delivery; readable captions burned into the video."
        "narration": _narration(selected, clean_topic),
        "scenes": scenes,
        "generation_status": "plan_only_provider_not_configured",
        "publishing_enabled": False,
        "requires_source_review": selected == "breaking_news",
        "source_review_ready": selected != "breaking_news" or len(sources) >= 2,
        "sources": sources,
        "copyright_safeguard": "Use original or appropriately licensed visuals and audio; do not copy third-party video or article text.",
    }
