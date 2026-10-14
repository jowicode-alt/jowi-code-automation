# Readiness checklist

Items marked complete have been implemented or verified; they do not imply that the whole system is production-ready.

## Repository and CI
- [x] Separate repository exists.
- [x] No per-run workflow artifact uploads; no APK build workflow is configured.
- [x] Checks-only workflow runs pytest; latest recorded run passed.
- [ ] Verify workflow remains green after documentation changes.

## Backend
- [x] Public liveness endpoint.
- [x] Bearer-token authentication for status and control endpoints; fails closed if token is absent.
- [x] Bounded job enqueue/list API; maximum three jobs per UTC day.
- [x] PostgreSQL adapter for hosted queue state; SQLite is local-development fallback only.
- [x] Brand-safe script and scene-prompt planner.
- [x] Voiceover generation endpoint and authenticated audio download.
- [x] FFmpeg vertical MP4 renderer function.
- [x] YouTube upload adapter restricted to private uploads.
- [ ] Add background worker to connect jobs to media pipeline, retry safely, and mark completed/failed states.
- [ ] Configure and verify a durable free-tier database; do not rely on ephemeral SQLite for hosted production.
- [ ] Deploy to a free-tier host and verify sleep/restart/resource limitations.

## Video and voice
- [x] Deep male voiceover adapter with configurable voice/rate/pitch (online provider availability is not guaranteed).
- [x] Four-scene brand prompt planner and FFmpeg assembly function for 9:16 output.
- [ ] Select a programmatic image/video provider that fits the $0 target and has acceptable usage rights/limits.
- [ ] Generate consistent lion scene assets automatically.
- [ ] Test full render quality, audio sync, duration, file size, and cleanup on the deployed host.

## YouTube
- [x] Upload adapter is restricted to private visibility.
- [ ] Configure YouTube OAuth consent and refresh token securely.
- [ ] Test a real private upload with owner-approved credentials.
- [ ] Verify quota, metadata, duplicate prevention, and retries.
- [ ] Implement an owner-reviewed route from private draft to public scheduling only after approval.

## Android
- [x] Initial dashboard scaffold and HTTPS health check.
- [ ] Implement authenticated status and job dashboard without embedding provider secrets.
- [ ] Connect job progress and audio/video draft review.
- [ ] Handle offline/network errors and expired credentials.
- [ ] Build and test APK only after backend contract stabilizes.
- [ ] Produce one release APK only after readiness gates pass.

## Release gate
- [ ] Latest CI green after final changes.
- [ ] No secrets in repository or logs.
- [ ] No unapproved public upload possible.
- [ ] No per-workflow artifacts.
- [ ] End-to-end pipeline verified.
- [ ] Owner approves live publishing.
