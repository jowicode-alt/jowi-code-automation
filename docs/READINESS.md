# Readiness checklist

Items marked complete have been implemented or verified; they do not imply that the whole system is production-ready.

## Repository and CI
- [x] Separate repository exists.
- [x] No per-run workflow artifact uploads; no APK build workflow is configured.
- [x] Checks-only workflow runs pytest and does not upload artifacts.
- [x] Previous CI checks passed; the new editorial change still requires its own green CI run.
- [x] Added a manual-only private worker workflow; it has no artifact upload and requires the operator to type PRIVATE before a single normal job can be processed.
- [x] Added a separate scheduled RSS news monitor (every 30 minutes) with cross-publisher headline matching and queue deduplication; it does not upload videos.
- [ ] Configure `JOWI_DATABASE_URL` and verify a successful scheduled news-monitor run.
- [ ] Verify scheduled workflow syntax and behavior after required secrets are configured.
- [x] Android source messaging says queueing does not automatically start the manual worker; source has not been compiled or device-tested.

## Backend
- [x] Public liveness endpoint.
- [x] Bearer-token authentication for protected endpoints; fails closed if token is absent.
- [x] Bounded job enqueue/list/detail API; maximum three regular jobs per UTC day; detail endpoint is authenticated.
- [x] Job lifecycle schema tracks status, last update, error, and JSON result.
- [x] PostgreSQL adapter for hosted queue state; SQLite is local-development fallback only.
- [x] Category-aware planner for breaking news, AI/technology, comedy, and entertainment.
- [x] Removed money/success and psychology categories and removed the Jowi lion/storytelling presentation.
- [x] News candidates bypass the regular daily queue cap and duplicate exact headlines are suppressed for 48 hours.
- [ ] Implement fact-grounded news summarization and source verification before any automatic draft/upload step.
- [x] Voiceover generation endpoint and authenticated audio download.
- [x] FFmpeg vertical MP4 renderer function.
- [x] Pipeline connects narration, rendering, and private-only YouTube upload; mocked-provider tests cover the pipeline.
- [x] YouTube upload adapter restricted to private uploads.
- [x] One-shot worker implemented and covered by mocked tests.
- [ ] Configure and verify a durable database.
- [x] Render free-tier deployment exists; verify the latest deploy after the editorial change.
- [ ] Configure automatic regular-video scheduling only after durable storage and end-to-end tests pass.
- [ ] Implement YouTube Analytics read access and tested reversible performance optimization.

## Video and voice
- [x] Deep male voiceover adapter with configurable voice/rate/pitch; online service availability is not guaranteed.
- [x] Four-scene topic-specific planner for vertical 9:16 output; no lion character or storytelling format.
- [ ] Live-generate and review scene assets; real-media quality is not yet verified.
- [ ] Test full render quality, audio sync, duration, file size, and cleanup on the deployed host.

## YouTube
- [x] Upload adapter restricted to private uploads.
- [ ] Configure YouTube OAuth and refresh token securely.
- [ ] Obtain owner-approved `yt-analytics.readonly` OAuth scope for read-only performance analysis.
- [ ] Test a real private upload with owner-approved credentials.
- [ ] Verify quota, metadata, duplicate prevention, and retries.
- [ ] Owner approval required before public publishing.

## Release gate
- [ ] New CI run is green.
- [ ] No secrets in repository or logs.
- [ ] No unapproved public upload possible.
- [ ] No per-workflow artifacts.
- [ ] End-to-end pipeline verified against real media and YouTube services.
- [ ] Owner approves live publishing.
