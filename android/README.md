# Android controller

This is an early development scaffold, not a release APK. It currently provides a dashboard and an HTTPS backend health check only. It cannot generate or publish videos.

Security and release rules:
- No API keys, OAuth secrets, signing keys, or tokens belong in the app source.
- Cleartext HTTP is disabled.
- Do not create/upload APK artifacts for routine workflow runs.
- Add authenticated control endpoints and secure session handling before adding buttons that start jobs or publish videos.
- Configure release signing only for the final approved release.
