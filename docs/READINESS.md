# Readiness checklist

Items marked complete have been implemented or verified; they do not imply that the whole system is production-ready.

## Repository and CI
- [x] Separate repository exists.
- [x] No per-run workflow artifact uploads; no APK build workflow is configured.
- [x] Checks-only workflow runs pytest and does not upload artifacts.
- [x] Latest verified CI run #85 passed; see https://github.com/jowicode-alt/jowi-code-automation/actions/runs/38637036727.
- [x] Image signature validation, anonymous-versus-registered sharing mode, worker planning failure handling, and partial AI Horde submission cleanup have regression tests.
- [x] Added a manual-only private worker workflow; it has no cron schedule, no artifact upload, and requires the operator to type PRIVATE before a single job can be processed.
- [ ] Verify the new workflow's GitHub Actions syntax and behavior in a controlled run after required secrets and a queued test job exist.
- [x] Android source messaging now accurately says queueing does not automatically start the manual worker; source has not yet been compiled or device-tested.

## Backend
- [x] Public liveness endpoint.
- [x] Bearer-token authentication for protected endpoints; fails closed if token is absent.
- [x] Bounded job enqueue/list/detail API; maximum three jobs per UTC day; detail endpoint is authenticated.
- [x] Job lifecycle schema tracks status, last update, error, and JSON result; legacy SQLite queues are migrated on access.
- [x] Worker re-queues jobs left running for over 45 minutes, with a regression test; the threshold exceeds the current 20-minute workflow timeout.
- [x] Lifecycle transitions are validated; blocked/failed jobs can be explicitly re-queued.
- [x] PostgreSQL adapter for hosted queue state; SQLite is local-development fallback only.
- [x] Brand-safe script and scene-prompt planner.
- [x] Voiceover generation endpoint and authenticated audio download.
- [x] FFmpeg vertical MP4 renderer function.
- [x] Pipeline function connects narration, rendering, and private-only YouTube upload; tested with mocked providers.
- [x] YouTube upload adapter restricted to private uploads.
- [x] One-shot worker implemented and covered by mocked tests.
- [x] Manual worker workflow fails before processing if its required database or YouTube OAuth secrets are missing.
- [ ] Configure and verify a durable free-tier database.
- [x] Render blueprint aligned with active backend variables; auto-deploy remains disabled.
- [x] Render account inspection found no Jowi Code service or database; existing services and database belong to the separate Forex project and are not reused.
- [ ] Deploy to a free-tier host and verify sleep/restart/resource limitations.
- [ ] Configure an automatic schedule only after durable storage, real-media generation, and private-upload tests pass.

### Manual worker setup (not yet configured)
The GitHub Actions workflow `.github/workflows/private-worker.yml` is manual-only. It processes at most one already-queued job and uploads only with YouTube privacy set to PRIVATE. Before use, configure repository Actions secrets:
- `JOWI_DATABASE_URL`: a dedicated durable PostgreSQL connection string for this project (never the Forex database).
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`: owner-approved YouTube OAuth credentials with upload scope.
- `AI_HORDE_API_KEY`: optional; anonymous mode is slower/shared and image generation is not guaranteed.

The workflow is deliberately not scheduled and cannot create a working queue by itself. A separate API deployment and a queued job are required. Do not store secrets in source files or commit them. It creates private drafts only; public publishing is not implemented.

## Video and voice
- [x] Deep male voiceover adapter with configurable voice/rate/pitch; online service availability is not guaranteed.
- [x] Four-scene brand prompt planner and FFmpeg assembly function for 9:16 output.
- [x] Optional AI Horde volunteer-powered image provider adapter implemented; free availability/latency is not guaranteed.
- [ ] Live-generate and review four scene assets; character consistency is not yet guaranteed.
- [ ] Test full render quality, audio sync, duration, file size, and cleanup on the deployed host.

## YouTube
- [x] Upload adapter restricted to private uploads.
- [ ] Configure YouTube OAuth consent and refresh token securely.
- [ ] Test a real private upload with owner-approved credentials.
- [ ] Verify quota, metadata, duplicate prevention, and retries.
- [ ] Add an owner-reviewed route to public scheduling only after approval.

## Android
- [x] HTTPS health check.
- [x] Authenticated status check, job queue submission, and job list refresh added to source.
- [ ] Compile and test Android source; no APK has been built.
- [ ] Improve expired-token and offline error handling.
- [ ] Connect job progress and audio/video draft review.
- [ ] Build one release APK only after backend and end-to-end readiness checks pass.

## Release gate
- [x] Latest recorded CI run #85 is green; new commits trigger checks-only CI.
- [ ] No secrets in repository or logs.
- [ ] No unapproved public upload possible.
- [ ] No per-workflow artifacts.
- [ ] End-to-end pipeline verified against real media and YouTube services.
- [ ] Owner approves live publishing.
