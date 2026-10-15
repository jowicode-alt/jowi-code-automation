# The Jowi Code: channel strategy

## Editorial direction
- **Breaking international news:** event-driven monitoring, with no fixed daily candidate quota. A poll is not an upload. Only distinct, material developments with credible corroboration qualify for review.
- **AI and technology:** practical demos, screen-led explainers, tool comparisons, and useful how-to Shorts.
- **Comedy:** original visual gags and relatable situations with a fast hook and payoff.
- **Entertainment:** original commentary, reactions, and trend explainers; do not repost third-party clips as a substitute for original work.
- Money/success and psychology categories are removed.
- The established Jowi lion character and storytelling-led presentation are removed; each topic uses a direct, topic-appropriate format.

## Candidate schedule (Africa/Kampala, UTC+3)
These are initial test slots, not an operational scheduler:
- Comedy: 12:30
- AI and technology: 15:00
- Entertainment: 18:00
- Breaking news: monitor every 30 minutes and queue only significant new developments, without a daily candidate cap.

The initial target remains 2–3 planned regular Shorts/day. News is event-driven and can add candidates when warranted. Avoid flooding viewers with repeated updates of the same story.

## News verification and copyright
1. Monitor reputable international sources and primary sources (official statements, public agencies, court filings, company announcements, and direct reports).
2. Corroborate important claims with independent sources where feasible. Label developing or unconfirmed details clearly; include publication/update time.
3. Write original summaries and narration. Headlines and facts can be reported, but do not copy article paragraphs, scripts, thumbnails, or another creator's video.
4. Use original graphics, licensed material, or footage explicitly cleared for the intended use. A public video or social-media post is not automatically free to reuse.
5. Keep a source list in the description. Correct or withdraw a draft if a key fact changes.
6. Deduplicate by event and material change; never create a new video solely because the polling interval elapsed.

## Performance-led optimization
Review the last 30 days, comparing categories only when each has at least five published videos and enough views to reduce noise. Consider engaged views, average view duration, audience retention, viewed-vs-swiped-away, subscribers gained, and returning viewers. Shift the content mix gradually toward categories outperforming the channel median on both retention and subscriber conversion. Do not make decisions from one viral outlier.

Automation may adjust topic selection, format, and schedule within the policy above. It must not:
- generate fabricated statistics, quotations, news, or demonstrations;
- make unsupported factual claims;
- imitate another creator's distinctive work or reuse unlicensed content;
- mass-produce near-identical videos to game discovery;
- change channel ownership/security settings or delete content without explicit owner approval;
- enable public publishing until end-to-end tests are passed and the owner explicitly approves it.

## Current implementation status
The repository has a manual one-job GitHub Actions worker, category-aware planners, an RSS news discovery workflow, and a private-only YouTube upload adapter. News discovery only queues candidates; it does not generate a fully source-grounded news report or publish it. The scheduled monitor requires `JOWI_DATABASE_URL` and its first successful scheduled run is not yet confirmed. YouTube Analytics and automatic performance-based schedule/topic changes are not implemented.

Remaining engineering work:
- verify the scheduled monitor with a successful run;
- add source-grounded news summarization and factual review before any automatic news draft/upload;
- add a durable scheduler/queue respecting free-tier limits and avoiding overlapping workers;
- integrate read-only YouTube Analytics;
- implement gradual, reversible schedule/topic adjustments with logs and owner controls;
- complete end-to-end real-media tests for each topic format.

Public uploads remain disabled during validation. The existing worker uploads private drafts only. No workflow artifact uploads should be added.
