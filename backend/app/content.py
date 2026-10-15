"""High-retention original Shorts planner for The Jowi Code.

Scripts use a hook, escalation/proof, payoff, and a concise close. No burned-in
captions or subtitles; use original or appropriately licensed visuals.
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
            ("Cold open", "Start on the most visually surprising real technology shot; immediate close framing and movement."),
            ("Challenge", "Cut to a specific everyday task or problem; show a clear visual change, not a generic stock montage."),
            ("Test", "Use relevant computer, phone, robotics, or human-workflow footage; never fabricate a product interface."),
            ("Payoff", "End on the practical lesson or limitation with a visually distinct final shot."),
        ]
    if category == "comedy":
        return [
            ("Cold open", "Open mid-action on a relatable awkward moment with a clear expressive reaction."),
            ("Escalation", "Show the situation getting more complicated through a different action and tighter shot."),
            ("Twist", "Use a contrasting visual beat that sets up an unexpected punchline."),
            ("Payoff", "Land on the strongest reaction or consequence; give the joke a short beat to breathe."),
        ]
    if category == "entertainment":
        return [
            ("Cold open", "Lead with the most energetic relevant performance, crowd, or pop-culture visual."),
            ("Build", "Show a contrasting angle or moment that raises the question."),
            ("Reveal", "Use a clear visual that supports the original observation; do not imply footage depicts an event it does not."),
            ("Payoff", "Finish on the most memorable relevant visual and a sharp takeaway."),
        ]
    return [
        ("What happened", "Use relevant verified event footage, date/location context, and no fabricated visuals."),
        ("Confirmed facts", "Show a distinct angle or source-grounded visual that supports confirmed details."),
        ("Why it matters", "Cut to a visual that explains real-world impact; separate fact from analysis."),
        ("Latest status", "End with the newest verified development and source context."),
    ]


def _narration(category: str, topic: str) -> str:
    if category == "ai_technology":
        return (
            f"Stop trusting an AI answer just because it sounds confident. Take {topic}: "
            "give the tool one specific task, then ask it to list what it assumed. "
            "Now verify the most important claim somewhere independent. That tiny extra step can expose "
            "a polished mistake before it becomes your problem. AI is useful; blind trust is not. "
            "Use the tool, challenge the answer, then decide. Subscribe to The Jowi Code. Thanks for watching."
        )
    if category == "comedy":
        return (
            f"You know when {topic.lower()}? It starts with, 'Relax, this will take two seconds.' "
            "Cut to ten minutes later: everyone is involved, nobody knows the plan, and the original problem "
            "has somehow become a group project. Then the one person who caused it says, 'So what's the issue?' "
            "That's not confidence. That's a talent. Be honest—who in your group does this? "
            "Subscribe to The Jowi Code. Thanks for watching."
        )
    if category == "entertainment":
        return (
            f"Here's why {topic.lower()} can take over your feed so quickly. First, one moment is easy to copy. "
            "Then everyone adds their own twist, so you see it everywhere without seeing the exact same thing. "
            "But once the surprise disappears, people move on just as fast. The trick is spotting what made "
            "the moment shareable—not just copying the trend after it's already everywhere. "
            "What trend do you think is next? Follow The Jowi Code. Thanks for watching."
        )
    return (
        f"Here is the latest verified update on {topic}. First, what sources confirm; second, what remains "
        "unclear; and third, why it matters. We will not fill gaps with guesses. Check the source links in "
        "the description for original reporting and later corrections. Subscribe to The Jowi Code for clear, "
        "sourced updates. Thanks for watching."
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
        "voice": "Deep male voiceover; energetic, conversational delivery with deliberate pauses; no on-screen captions, subtitles, or text anywhere in the final video.",
        "narration": _narration(selected, clean_topic),
        "scenes": scenes,
        "generation_status": "plan_only_provider_not_configured",
        "publishing_enabled": False,
        "requires_source_review": selected == "breaking_news",
        "source_review_ready": selected != "breaking_news" or len(sources) >= 2,
        "sources": sources,
        "copyright_safeguard": "Use original or appropriately licensed visuals and audio; do not copy third-party video or article text.",
    }
