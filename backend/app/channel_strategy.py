"""The Jowi Code editorial strategy and schedule defaults.

This module is the single source of truth for the planned editorial mix. It does
not itself schedule or publish videos; the worker/scheduler must enforce these
settings before the strategy is operational.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryPolicy:
    key: str
    label: str
    format: str
    daily_target: int | None
    preferred_local_times: tuple[str, ...]
    storytelling: bool
    notes: str


# Uganda local time is East Africa Time (UTC+3). News is event-driven, not a
# fixed daily quota; polling frequency is not the same as permission to publish.
CATEGORY_POLICIES = {
    "breaking_news": CategoryPolicy(
        key="breaking_news",
        label="International breaking news",
        format="Fast, factual vertical update with date/time, primary-source context, "
               "original narration, and source links in the description.",
        daily_target=None,
        preferred_local_times=(),
        storytelling=False,
        notes="Poll every 15 minutes; publish only genuinely material, corroborated "
              "developments. Deduplicate events and updates. Never invent missing facts, "
              "copy article text, or use unlicensed broadcast footage.",
    ),
    "ai_technology": CategoryPolicy(
        key="ai_technology",
        label="AI and technology",
        format="Practical demo or screen-led explainer; show the tool/workflow and "
               "a concrete result, with original narration.",
        daily_target=1,
        preferred_local_times=("15:00",),
        storytelling=False,
        notes="Evergreen how-to videos plus timely product updates. Verify capabilities "
              "and disclose meaningful limitations; do not fabricate demos.",
    ),
    "comedy": CategoryPolicy(
        key="comedy",
        label="Comedy",
        format="Original visual gag or relatable situation with an immediate hook, "
               "clear escalation, and a payoff; no borrowed skits.",
        daily_target=1,
        preferred_local_times=("12:30",),
        storytelling=False,
        notes="Use original scenarios, dialogue, characters, and sound or properly "
              "licensed audio. Avoid repetitive template spam.",
    ),
    "entertainment": CategoryPolicy(
        key="entertainment",
        label="Entertainment",
        format="Original, trend-aware commentary, reactions, or explainers using "
               "licensed/original visuals rather than re-uploaded clips.",
        daily_target=1,
        preferred_local_times=("18:00",),
        storytelling=False,
        notes="Trends are prompts for original work, not permission to reuse copyrighted "
              "clips, music, or another creator's video.",
    ),
    "money_success": CategoryPolicy(
        key="money_success",
        label="Money and success",
        format="Jowi-led cinematic storytelling with a specific lesson and practical takeaway.",
        daily_target=1,
        preferred_local_times=("17:00",),
        storytelling=True,
        notes="Educational, balanced claims; no guaranteed returns, fabricated success stories, "
              "or misleading financial promises.",
    ),
    "psychology": CategoryPolicy(
        key="psychology",
        label="Psychology and human behaviour",
        format="Jowi-led story with a relatable behavioural question, evidence-based explanation, "
              "and actionable conclusion.",
        daily_target=1,
        preferred_local_times=("19:00",),
        storytelling=True,
        notes="Avoid diagnosing viewers or presenting pop-psychology claims as established science.",
    ),
}

# These are candidate local-time slots, not a live scheduler. News has no fixed
# upload cap, but every candidate must pass the editorial and deduplication gates.
NEWS_POLL_INTERVAL_MINUTES = 15
LOCAL_TIMEZONE = "Africa/Kampala"
SHORTS_DAILY_BASELINE = 2
SHORTS_DAILY_TARGET = 3
PERFORMANCE_REVIEW_DAYS = 30
PERFORMANCE_MINIMUM_VIEWS = 100
PERFORMANCE_MINIMUM_PUBLISHED_VIDEOS = 5
PERFORMANCE_METRICS = (
    "engaged_views",
    "average_view_duration",
    "audience_retention",
    "viewed_vs_swiped_away",
    "subscribers_gained",
    "returning_viewers",
)

# Only categories with enough comparable evidence should have their production
# share adjusted. Never automatically chase a single outlier or weaken safeguards.
PERFORMANCE_RULES = {
    "review_window_days": PERFORMANCE_REVIEW_DAYS,
    "minimum_views_per_video": PERFORMANCE_MINIMUM_VIEWS,
    "minimum_videos_per_category": PERFORMANCE_MINIMUM_PUBLISHED_VIDEOS,
    "increase_share_when": (
        "category beats channel median on retention and subscribers gained "
        "across multiple videos",
    ),
    "decrease_share_when": (
        "category consistently underperforms across the review window",
    ),
    "preserve_category_diversity": True,
    "preserve_originality_and_policy_checks": True,
    "never_auto_enable_public_publishing": True,
}
