# The Jowi Code: channel strategy

## Editorial direction
- **Breaking international news:** event-driven, continuous monitoring; no fixed daily upload quota. A poll is not an upload. Only distinct, material, verified developments qualify.
- **AI and technology:** practical demos, screen-led explainers, tool comparisons, and useful how-to Shorts.
- **Comedy:** original visual gags and relatable situations with a fast hook and payoff.
- **Entertainment:** original commentary, reactions, and trend explainers; do not repost third-party clips as a substitute for original work.
- **Money and success:** keep the established Jowi lion and use storytelling with a practical takeaway.
- **Psychology and human behaviour:** keep the established Jowi lion and use storytelling grounded in reliable evidence.

## Candidate schedule (Africa/Kampala, UTC+3)
These are initial test slots, not yet an operational scheduler:
- Comedy: 12:30
- AI and technology: 15:00
- Money and success: 17:00
- Entertainment: 18:00
- Psychology: 19:00
- Breaking news: check sources every 15 minutes; queue only significant new developments, without a daily cap.

The initial target remains 2–3 planned Shorts/day across the regular categories. News is event-driven and can add more when warranted, so total daily uploads can exceed the regular target. Avoid flooding viewers with repeated updates of the same story.

## News verification and copyright
1. Monitor reputable international sources and primary sources (official statements, public agencies, court filings, company announcements, and direct reports).
2. Corroborate important claims with independent sources where feasible. Label developing or unconfirmed details clearly; include publication/update time.
3. Write original summaries and narration. Headlines and facts can be reported, but do not copy article paragraphs, scripts, thumbnails, or another creator's video.
4. Use original graphics, licensed material, or footage explicitly cleared for the intended use. A public video or social-media post is not automatically free to reuse.
5. Keep a source list in the description. Correct or withdraw a draft if a key fact changes.
6. Deduplicate by event and material change; never create a new video solely because the polling interval elapsed.

## Performance-led optimization
Review the last 30 days, comparing categories only when each has at least five published videos and enough views to reduce noise. Consider engaged views, average view duration, audience retention, viewed-vs-swiped-away, subscribers gained, and returning viewers. Shift the content mix gradually toward categories outperforming the channel median on both retention and subscriber conversion. Do not make decisions from one viral outlier, and keep testing every category.

Automation may adjust topic selection, format, and schedule within the policy above. It must not:
- generate fabricated statistics, quotations, news, or demonstrations;
- make unsupported financial or medical/psychological claims;
- imitate another creator's distinctive work or reuse unlicensed content;
- mass-produce near-identical videos to game discovery;
- change channel ownership/security settings or delete content without explicit owner approval;
- enable public publishing until end-to-end tests are passed and the owner explicitly approves it.

## Current implementation status (important)
The existing repository currently has a manual one-job GitHub Actions worker, a generic topic-to-motivation script, a hard three-job-per-UTC-day queue cap, and a private-only YouTube upload adapter. The strategy defaults are documented in `backend/app/channel_strategy.py`, but they are **not yet wired into live scheduling, RSS/news monitoring, YouTube Analytics, category-aware script generation, or automatic channel adjustments**. Do not treat this document or config alone as proof that continuous monitoring or automated optimization is running.

The next engineering work must implement and test:
- source polling, corroboration, event deduplication, and safe candidate creation;
- category-aware original scripts and topic-appropriate visual formats;
- category-aware quotas (no fixed news cap, with duplicate/materiality controls);
- a durable scheduler/queue that respects free-tier limits and avoids overlapping workers;
- read-only YouTube Analytics integration for performance reports;
- gradual, reversible schedule/topic adjustments with logs and owner controls.

Public uploads remain disabled during validation. The existing worker uploads private drafts only. No workflow artifact uploads should be added.
