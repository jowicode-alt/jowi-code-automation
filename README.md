# The Jowi Code Automation

A phone-managed automation system for **The Jowi Code** YouTube channel.

## Channel strategy
- Regular Shorts target: 2–3 per day across comedy, entertainment, and AI/technology.
- International news monitoring is event-driven and configured to poll every 30 minutes; there is no daily news candidate quota.
- AI and technology: practical demonstrations and useful explainers.
- Comedy: original visual gags and relatable situations.
- Entertainment: original commentary and trend explainers, not re-uploads.
- Presentation is topic-specific and direct: no Jowi lion character and no storytelling-led format.
- Candidate schedule and policy: see `docs/CHANNEL_STRATEGY.md` and `backend/app/channel_strategy.py`.

## Artifact policy
**No downloadable artifact should be uploaded or retained for every workflow run.** CI runs checks only and must not use `actions/upload-artifact`. Do not build an APK until readiness checks pass and a deliberate release is appropriate.

## Implemented foundation
- FastAPI health endpoint and protected status endpoint.
- Authenticated job queue with three regular-content jobs per UTC day; corroborated news jobs are exempt from that daily cap and duplicate headlines are suppressed for 48 hours.
- Category-aware original script and scene planning for comedy, entertainment, AI/technology, and breaking news.
- Conservative RSS news discovery across BBC World, The Guardian World, NPR World, and UN News.
- News candidates require a similar headline from at least two different publishers, are deduplicated across matching headline clusters, and retain source URLs for source-aware private draft planning.
- Scheduled GitHub Actions workflow polls feeds every 30 minutes and queues corroborated candidates. It requires the dedicated `JOWI_DATABASE_URL` secret and a successful scheduled run before monitoring can be considered active.
- AI Horde image generation adapter with bounded retries and an illustrated local fallback.
- Optional Edge TTS voiceover endpoint and FFmpeg vertical 9:16 renderer.
- Private-only YouTube upload adapter. Public publishing remains disabled.

## Important limitations
- **The news monitor discovers and queues candidates; it does not automatically publish news.** Headline similarity across feeds is only a discovery safeguard, not proof that every factual claim is verified. The current deterministic news script does not yet generate a detailed, source-grounded summary of the reported facts, so news candidates must not be auto-published.
- The monitor workflow requires `JOWI_DATABASE_URL` to be configured in GitHub Actions. Until a successful scheduled run is confirmed, do not assume continuous monitoring is running.
- Automatic YouTube Analytics review and performance-led schedule/topic adjustments are not implemented yet.
- The category-specific schedule values are initial test slots, not evidence-based optimal times.
- AI Horde is a free volunteer service; anonymous requests are low-priority, may time out, and image consistency is not guaranteed.
- The private worker remains manual-only for normal video jobs. A successful past run proved one video could be generated and uploaded privately, not that all category formats work end-to-end.
- Hosted use needs a strong private `API_ACCESS_TOKEN` and durable `DATABASE_URL`; SQLite on an ephemeral web service is not suitable for production.
- No workflow artifacts are uploaded. Public publishing is disabled.

## Local backend
From `backend/`:
```sh
python -m venv .venv
# activate the virtual environment
pip install -r requirements-dev.txt
export API_ACCESS_TOKEN="use-a-long-random-local-secret"
uvicorn app.main:app --reload
```
`GET /health` is public. `/api/status`, `/api/jobs`, `/api/scripts/plan`, and `/api/voiceover` require `Authorization: Bearer <API_ACCESS_TOKEN>`.

Never commit API keys, OAuth secrets, access tokens, signing keys, or keystores. Never place provider credentials in Android source.
