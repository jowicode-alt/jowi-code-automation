# Readiness checklist

Items marked complete have been implemented or verified; they do not imply that the whole system is production-ready.

## Repository and CI
- [x] Separate repository exists.
- [x] No per-run workflow artifact uploads; no APK build workflow is configured.
- [x] Checks-only workflow runs pytest; latest recorded backend test run passed.
- [ ] Verify CI after Android and documentation changes.

## Backend
- [x] Public liveness endpoint.
- [x] Bearer-token authentication for protected endpoints; fails closed if token is absent.
- [x] Bounded job enqueue/list/detail API; maximum three jobs per UTC day; detail endpoint is authenticated.
- [x] Job lifecycle schema tracks status, last update, error, and JSON result; legacy SQLite queues are migrated on access.
- [x] Lifecycle transitions are validated; blocked/failed jobs can be explicitly re-queued.
- [x] PostgreSQL adapter for hosted queue state; SQLite is local-development fallback only.
- [x] Brand-safe script and scene-prompt planner.
- [x] Voiceover generation endpoint and authenticated audio download.
- [x] FFmpeg vertical MP4 renderer function.
- [x] Pipeline function connects narration, rendering, and private-only YouTube upload; tested with mocked providers.
- [x] YouTube upload adapter restricted to private uploads.
- [ ] Add and deploy a single worker process to consume queued jobs; lifecycle storage is ready but jobs are not processed automatically yet.
- [ ] Configure and verify a durable free-tier database.
- [ ] Deploy to a free-tier host and verify sleep/restart/resource limitations.

## Video and voice
- [x] Deep male voiceover adapter with configurable voice/rate/pitch; online service availability is not guaranteed.
- [x] Four-scene brand prompt planner and FFmpeg assembly function for 9:16 output.
- [ ] Select an affordable, rights-compliant programmatic image provider; no $0 provider is confirmed.
- [ ] Generate consistent lion scene assets automatically.
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
- [ ] Latest CI green after all current changes.
- [ ] No secrets in repository or logs.
- [ ] No unapproved public upload possible.
- [ ] No per-workflow artifacts.
- [ ] End-to-end pipeline verified against real media and YouTube services.
- [ ] Owner approves live publishing.
