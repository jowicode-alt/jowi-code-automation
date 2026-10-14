# Readiness checklist

No item below should be considered complete until tested and recorded.

## Repository and CI
- [x] Separate repository exists.
- [x] Artifact policy documented: no per-run workflow artifacts.
- [ ] Add checks-only CI after the initial code layout stabilizes.
- [ ] Confirm no workflow uploads artifacts or triggers Android release builds.

## Backend
- [x] Minimal liveness endpoint scaffold.
- [x] Status endpoint reports configuration presence only.
- [ ] Add authentication before any control endpoint is exposed publicly.
- [ ] Add persistent job state and bounded queues.
- [ ] Add render pipeline with cleanup and resource limits.
- [ ] Add tests for health/status and failure handling.
- [ ] Deploy to a free-tier host and verify sleep/restart limitations.

## Video and voice
- [ ] Confirm usable free generation options and quotas.
- [ ] Preserve Jowi character/style constraints.
- [ ] Render vertical 9:16 output with voiceover and no captions.
- [ ] Validate duration, audio, framing, and file size.
- [ ] Ensure temporary media is cleaned up and never uploaded as workflow artifacts.

## YouTube
- [ ] Complete channel-owner OAuth consent securely.
- [ ] Implement dry-run mode first.
- [ ] Test upload as private/unlisted before public scheduling.
- [ ] Verify quota, metadata, privacy, duplicate prevention, and retry behavior.
- [ ] Enable automatic publishing only after explicit readiness approval.

## Android
- [ ] Implement status and job dashboard.
- [ ] Securely configure backend URL and authentication.
- [ ] Handle offline/network errors and expired credentials.
- [ ] Build and test APK only after backend contract stabilizes.
- [ ] Produce one release APK after all readiness gates pass.

## Release gate
- [ ] Tests pass.
- [ ] No secrets in repository or logs.
- [ ] No unapproved public upload possible.
- [ ] No per-workflow artifacts.
- [ ] Owner approves live publishing.
