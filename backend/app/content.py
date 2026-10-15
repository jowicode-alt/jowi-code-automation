"""Category-aware original Shorts planner for The Jowi Code.

The planner deliberately uses templates as structure, not repeated scripts. News
is a private draft only and must be source-checked before public release.
"""
from __future__ import annotations

from app.channel_strategy import CATEGORY_POLICIES

CHARACTER_STYLE = (
    "Photorealistic anthropomorphic black male lion, black suit, crisp white shirt, "
    "gold tie, gold eyes, serious expression with no smile; cinematic realistic lighting. "
    "Vertical 9:16 framing. Keep the same character identity across every scene."
)

VALID_CATEGORIES = set(CATEGORY_POLICIES)


def _category(topic: str, category: str | None) -> tuple[str, str]:
    clean = " ".join(topic.split()).strip(" .!?")
    if category is None and clean.startswith("[") and "]" in clean:
        marker, remainder = clean[1:].split("]", 1)
        if marker in VALID_CATEGORIES:
            category, clean = marker, remainder.strip()
    category = category or "money_success"
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unsupported content category: {category}")
    if len(clean) < 3:
        raise ValueError("Topic must contain at least three non-space characters")
    return category, clean


def _story_scenes(category: str) -> list[tuple[str, str]]:
    if category in {"money_success", "psychology"}:
        return [
            ("Hook", f"{CHARACTER_STYLE} Jowi faces camera in a dark cinematic office, serious direct gaze, slow push-in."),
            ("Conflict", f"{CHARACTER_STYLE} Jowi pauses at a meaningful choice in a restrained modern setting; thoughtful body language."),
            ("Lesson", f"{CHARACTER_STYLE} Jowi takes a deliberate practical action at a desk; realistic props, no readable text."),
            ("Close", f"{CHARACTER_STYLE} Jowi faces camera with composed confidence and subtle warm gold rim light."),
        ]
    if category == "ai_technology":
        return [
            ("Hook", "Vertical screen-led demonstration of the relevant tool or workflow, clean interface, no fabricated UI or readable fake claims."),
            ("Problem", "Show the real task before the tool is used; crisp close-up and clear visual hierarchy."),
            ("Demo", "Show a simple step-by-step workflow with original screen capture or licensed visuals; only show verified capabilities."),
            ("Result", "Show the actual result and a concise limitation or takeaway; clean vertical end frame."),
        ]
    if category == "comedy":
        return [
            ("Hook", "Original relatable situation shown immediately in a vertical frame; expressive original characters, no copied meme."),
            ("Setup", "Escalate the situation with a clear visual reaction and natural timing."),
            ("Twist", "Deliver an unexpected but understandable visual gag; original dialogue and no borrowed footage."),
            ("Punchline", "Hold on the original character reaction for the punchline; clean end frame."),
        ]
    if category == "entertainment":
        return [
            ("Hook", "Original visual metaphor or licensed/original visual that quickly introduces the entertainment topic."),
            ("Context", "Show original illustrative visuals supporting a concise factual explanation."),
            ("Insight", "Present an original observation or commentary, not a re-upload of third-party clips."),
            ("Close", "Finish with a clear takeaway and clean branded end frame."),
        ]
    # News uses neutral original graphics/illustrations; never imply that a generated
    # image is authentic footage of the event.
    return [
        ("What happened", "Neutral original newsroom-style graphic with date and location placeholders; do not fabricate event footage."),
        ("What is confirmed", "Clean timeline or map-style illustration; include only verified facts and clearly label uncertainty."),
        ("Why it matters", "Original explanatory graphic that distinguishes confirmed information from analysis."),
        ("Sources and update", "Clean source-card visual listing outlet names in the rendered plan; provide source links in the description."),
    ]


def _narration(category: str, topic: str) -> str:
    if category == "money_success":
        return (
            f"Here is the lesson behind {topic.lower()}. Success is not a single dramatic moment; "
            "it is a series of decisions repeated when nobody is watching. Identify one action you "
            "can control, make it small enough to do today, and measure whether it helps. "
            "Master your mind. Build your future. Subscribe to The Jowi Code. Thanks for watching."
        )
    if category == "psychology":
        return (
            f"Let's examine {topic.lower()}. Our behaviour is shaped by habits, context, and the "
            "choices we repeat—not by one simple rule. Look for the evidence, notice what changes "
            "your behaviour, and test one practical adjustment. This is general education, not a "
            "diagnosis. Master your mind. Build your future. Subscribe to The Jowi Code. Thanks for watching."
        )
    if category == "ai_technology":
        return (
            f"Here is a practical look at {topic}. First, identify the task you want to solve. "
            "Then test the tool on a real example, check the output, and compare the result with "
            "your current workflow. Features and free-plan limits can change, so verify them before "
            "you rely on the tool. Subscribe to The Jowi Code. Thanks for watching."
        )
    if category == "comedy":
        return (
            f"POV: {topic}. It starts like a normal day, then one small thing goes completely "
            "off plan. The confidence disappears, the excuses arrive, and somehow the simplest "
            "solution was right there the whole time. You know someone who does this. Subscribe "
            "to The Jowi Code. Thanks for watching."
        )
    if category == "entertainment":
        return (
            f"Here is the interesting part about {topic}. Instead of just repeating the trend, "
            "let's look at what makes people notice it, what is actually known, and what is still "
            "opinion. The context matters as much as the headline. Subscribe to The Jowi Code. Thanks for watching."
        )
    return (
        f"Here is the latest verified update on {topic}. We are separating confirmed information "
        "from details that are still developing. Check the source links in the description for the "
        "original statements and further updates. If key facts change, this update should be corrected. "
        "Subscribe to The Jowi Code for clear, sourced explainers."
    )


def build_short_plan(topic: str, category: str | None = None) -> dict:
    selected, clean_topic = _category(topic, category)
    policy = CATEGORY_POLICIES[selected]
    title = clean_topic[:90]
    sources = []
    if selected == "breaking_news":
        try:
            from app.news_monitor import sources_for_topic
            sources = sources_for_topic(clean_topic)
        except Exception:
            # Planning must remain available locally, but an empty source list is
            # an explicit review blocker for any news draft.
            sources = []
    scenes = [
        {
            "number": index,
            "beat": beat,
            "visual_prompt": f"{visual} Vertical 9:16. No captions baked into imagery, no copied logos, no unauthorized footage.",
        }
        for index, (beat, visual) in enumerate(_story_scenes(selected), start=1)
    ]
    return {
        "channel": "The Jowi Code",
        "tagline": "Master Your Mind. Build Your Future.",
        "category": selected,
        "format": "YouTube Short, vertical 9:16",
        "presentation": policy.format,
        "title": title,
        "topic": clean_topic,
        "voice": "Deep male voiceover; clear, natural delivery; no on-screen captions.",
        "narration": _narration(selected, clean_topic),
        "scenes": scenes,
        "generation_status": "plan_only_provider_not_configured",
        "publishing_enabled": False,
        "requires_source_review": selected == "breaking_news",
        "source_review_ready": selected != "breaking_news" or len(sources) >= 2,
        "sources": sources,
        "copyright_safeguard": "Use original or appropriately licensed visuals and audio; do not copy third-party video or article text.",
    }
