# The Jowi Code Automation

A phone-managed automation system for **The Jowi Code** YouTube channel.

## Goals
- Target 2–3 Shorts per day.
- Preserve the established Jowi lion brand: photorealistic black anthropomorphic male lion, black suit, white shirt, gold tie, gold eyes, serious expression.
- Vertical 9:16 videos, deep male voiceover, no captions, no typing/snap/ether effects.
- End videos with the channel's subscribe / “Thanks for watching” call to action.
- Prefer free services and disclose any unavoidable costs before enabling them.
- Android app + backend, controlled from a phone.

## Artifact policy
**Do not upload or retain a downloadable artifact for each workflow run.** During development, CI should run checks only and must not use the GitHub Actions `upload-artifact` action. A release APK should be built and retained only after readiness checks pass and a release is deliberately requested.

## Current status
This repository is being initialized. No production video generation, YouTube upload, scheduled publishing, or APK release is enabled yet. Do not claim the system is ready until the readiness checklist is complete.

## Planned structure
- `backend/` — API service and automation orchestration.
- `android/` — Android control app.
- `docs/READINESS.md` — launch gates and validation checklist.
- `.github/workflows/` — later, checks-only workflows; no per-run artifacts.

## Development sequence
1. Establish backend health/status endpoints.
2. Define secure configuration and authentication before exposing control endpoints.
3. Implement draft/script and render-job orchestration.
4. Integrate video/voice providers only after validating free-tier limits and fallback behavior.
5. Add YouTube OAuth and private upload/scheduling, initially in dry-run mode.
6. Build the Android controller and connect it to the secured backend.
7. Run readiness checks; then produce one final APK only after approval.

## Required configuration (not set up yet)
Never commit API keys, OAuth client secrets, access tokens, signing keys, or keystores. Use hosting environment variables / GitHub Secrets. YouTube upload requires the channel owner to complete OAuth consent.

## Local backend check
From `backend/`:
```sh
python -m venv .venv
# activate the virtual environment
pip install -r requirements.txt
uvicorn app.main:app --reload
``
Then open `/health` on the local server.
