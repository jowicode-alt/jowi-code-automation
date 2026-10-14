# The Jowi Code Automation

A phone-managed automation system for **The Jowi Code** YouTube channel.

## Brand and targets
- Target 2–3 Shorts per day, with a hard queue limit of three jobs per UTC day.
- Keep the photorealistic black anthropomorphic male lion, black suit, white shirt, gold tie, gold eyes, and serious expression.
- Vertical 9:16, deep male voiceover, no captions, no typing/snap/ether effects.
- Preserve the tagline “Master Your Mind. Build Your Future.” and a subscribe / “Thanks for watching” close.
- Prefer $0 services and disclose reliability or quota limitations.

## Artifact policy
**No downloadable artifact should be uploaded or retained for every workflow run.** CI runs checks only and must not use `actions/upload-artifact`. The APK should be built only after the backend contract and readiness checks are complete, and only for a deliberate release.

## Implemented foundation
- FastAPI health endpoint and bearer-token-protected status endpoint.
- Authenticated job enqueue/list endpoints with a three-job daily limit.
- SQLite local development queue and PostgreSQL support through `DATABASE_URL`.
- Brand-consistent script and four-scene prompt planner.
- Optional no-key Edge TTS voiceover endpoint; it requires outbound internet and can be unavailable because it uses a third-party online service.
- FFmpeg vertical 9:16 renderer that combines four scene images and audio.
- Pipeline function that creates narration, renders a Short, uploads it to YouTube as private, and removes temporary audio/video files after the attempt.
- YouTube Data API adapter that uploads videos as **private only**.
- Docker-based Render blueprint with auto-deploy disabled.
- Checks-only GitHub Actions workflow with no artifact uploads. Latest recorded run passed: [workflow run](https://github.com/jowicode-alt/jowi-code-automation/actions/runs/38631982045). That run tested the pipeline with mocked media/YouTube providers, not with live services.

## Important limitations — not production-ready yet
- No programmatic AI scene-image/video provider has been selected or configured. The planner currently produces scene prompts; it does not generate the lion images itself. The private-draft pipeline requires four existing scene images.
- Queue jobs are not yet connected to a background worker that runs the full workflow and updates queued/running/completed/failed states.
- YouTube OAuth credentials and channel-owner consent have not been configured or tested against the real channel.
- The backend has not been deployed, and the Android app is still a dashboard scaffold with only a health check.
- The Render blueprint expects a strong `API_ACCESS_TOKEN` and a durable PostgreSQL `DATABASE_URL` to be set privately. SQLite on a free web service is not durable across restarts. Select a suitable free database and check its limits before deploying.
- Automatic public publishing is intentionally disabled. The YouTube adapter can only upload as private; public scheduling must wait for owner review and separate readiness approval.

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

Never commit API keys, OAuth secrets, access tokens, signing keys, or keystores. Do not put provider credentials in the Android source code.
