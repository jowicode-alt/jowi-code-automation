# Android controller

Development dashboard only; not a release APK.

Implemented: HTTPS health check, authenticated backend status, queue a Short job, and refresh the job list. The access token is held in screen state only and is not intentionally saved to disk.

Limitations: queued jobs are not yet processed by a background media worker. The app does not generate images, render videos, or publish to YouTube. Public publishing remains disabled. The dashboard has not been built or tested on a physical device.

Security: never commit API keys, OAuth secrets, signing keys, or tokens. Use HTTPS only. Do not create or upload APKs during routine workflow runs. Configure release signing and create one APK only after end-to-end readiness checks pass.
