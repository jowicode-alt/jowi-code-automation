# The Jowi Code Automation

A phone-managed automation system for **The Jowi Code** YouTube channel.

## Brand and targets
- Target 2–3 Shorts per day; queue limit: three jobs per UTC day.
- Photorealistic black anthropomorphic male lion, black suit, white shirt, gold tie, gold eyes, serious expression.
- Vertical 9:16, deep male voiceover, no captions, no typing/snap/ether effects.
- Tagline: “Master Your Mind. Build Your Future.” Close with subscribe / “Thanks for watching”.
- Prefer $0 services and disclose reliability or quota limitations.

## Artifact policy
**No downloadable artifact should be uploaded or retained for every workflow run.** CI runs checks only and must not use `actions/upload-artifact`. Do not build an APK until readiness checks pass and a deliberate release is appropriate.

## Implemented foundation
- FastAPI health endpoint and protected status endpoint.
- Authenticated job enqueue/list API with a three-job daily limit.
- SQLite local development queue and PostgreSQL support via `DATABASE_URL`.
- Brand-consistent script and four-scene prompt planner.
- Optional free AI Horde image generation adapter using volunteer workers, with bounded polling and timeouts.
- Optional Edge TTS voiceover endpoint; requires outbound internet and relies on a third-party service.
- FFmpeg vertical 9:16 renderer for four scene images and audio.
- Private-draft pipeline that combines narration, rendering, and private-only YouTube upload; tested with mocked providers.
- YouTube upload adapter that only requests private visibility.
- Render Docker blueprint with auto-deploy disabled.
- Android source now includes HTTPS health check, authenticated status, job queue submission, and queue refresh. It has not yet been compiled or device-tested.

## Important limitations
- AI Horde can generate scene images at no direct API cost, but anonymous requests have low priority, can time out, and may share prompts/images. Character consistency is not guaranteed. Alternatively, supply four pre-generated files named `scene-1.png` through `scene-4.png` in `SCENE_ASSETS_DIR`.
- A one-shot worker processes one job when manually invoked. It can request four scenes from AI Horde or use pre-generated images; it is not deployed or scheduled.
- YouTube OAuth and channel-owner consent have not been configured or tested against the real channel.
- The backend has not been deployed. The Android app is still a development scaffold, not a built APK.
- Hosted use needs a strong private `API_ACCESS_TOKEN` and durable `DATABASE_URL`; SQLite on an ephemeral web service is not suitable for production.
- Public publishing is disabled. Upload adapter only creates private videos.

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
