# The Jowi Code Automation

A phone-managed automation system for **The Jowi Code** YouTube channel.

## Channel strategy
- Regular Shorts target: 2–3 per day, with candidate time slots by category.
- International breaking news is event-driven and intended to be monitored continuously; no fixed news upload quota, but duplicate/materiality checks and source verification are required.
- AI and technology: practical demos and useful explainers.
- Comedy: original visual gags and relatable situations.
- Entertainment: original commentary and trend explainers, not re-uploads.
- Money and success + psychology and human behaviour: preserve the Jowi lion and storytelling format.
- Candidate schedule and safety rules: see `docs/CHANNEL_STRATEGY.md` and `backend/app/channel_strategy.py`.
- **Important:** strategy config exists, but continuous news monitoring, scheduling, YouTube Analytics integration, category-aware script generation, and automatic performance adjustments are not yet implemented.

## Brand
- Photorealistic black anthropomorphic male lion, black suit, white shirt, gold tie, gold eyes, serious expression.
- Vertical 9:16, deep male voiceover, no captions, no typing/snap/ether effects.
- Tagline: “Master Your Mind. Build Your Future.” Close with subscribe / “Thanks for watching”.
- Prefer $0 services and disclose reliability or quota limitations.

## Artifact policy
**No downloadable artifact should be uploaded or retained for every workflow run.** CI runs checks only and must not use `actions/upload-artifact`. Do not build an APK until readiness checks pass and a deliberate release is appropriate.

## Implemented foundation
- FastAPI health endpoint and protected status endpoint.
- Authenticated job enqueue/list API with a three-job daily limit (this cap still needs to be changed before news automation can run as designed).
- SQLite local development queue and PostgreSQL support via `DATABASE_URL`.
- Current generic script and four-scene prompt planner.
- AI Horde image generation adapter with sequential submissions, bounded 429 retries honoring Retry-After, bounded polling, and cancellation on failure.
- Offline Pillow-based branded illustrated scene fallback when the free volunteer image API is throttled or unavailable.
- Optional Edge TTS voiceover endpoint.
- FFmpeg vertical 9:16 renderer for four scene images and audio.
- Private-draft pipeline and YouTube upload adapter that only requests private visibility.
- Render Docker blueprint with auto-deploy disabled.

## Important limitations
- AI Horde is a free volunteer service; anonymous requests are low-priority, may time out, and may share prompts/images. Character consistency is not guaranteed.
- The GitHub Actions worker is manual-only and processes at most one queued job. It is not continuously scheduled.
- The last successful run created a private draft. That verifies one manual pipeline run, not continuous scheduling or public publishing.
- YouTube Analytics read access is not yet configured; automatic performance-based adjustments cannot be truthfully claimed until that integration is implemented and tested.
- Hosted use needs a strong private `API_ACCESS_TOKEN` and durable `DATABASE_URL`; SQLite on an ephemeral web service is not suitable for production.
- Public publishing remains disabled during validation. The current worker uploads private drafts only.
- News automation must use original summaries, source corroboration, event deduplication, and original/licensed visuals; it must not copy article text or reuse unlicensed clips.

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
