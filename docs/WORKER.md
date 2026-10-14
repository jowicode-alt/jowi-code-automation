# One-shot worker

Run from the `backend` directory:

```bash
python -m app.worker
```

The worker claims at most one queued job per invocation and builds the branded four-scene plan.

## Scene images

The worker first checks `SCENE_ASSETS_DIR` for four files named `scene-1.png` through `scene-4.png`. If those are not all present, it uses the AI Horde adapter in `app/image_provider.py` to request four 512×768 images in parallel. The adapter polls the volunteer-powered service with a bounded timeout and downloads the returned images into a temporary directory.

AI Horde is a free, community-powered option, not a guaranteed production SLA. Anonymous requests have the lowest priority and may wait or time out. Requests use the anonymous key by default; anonymous prompts/images may be shared by the service. Do not send confidential prompts through anonymous access. Register for an API key if you want higher priority, but that still does not guarantee fast or uninterrupted generation. Review the service's terms and output suitability before using generated images commercially. The four separate prompts may not preserve the lion's identity perfectly across scenes.

## Rendering and YouTube

After four images exist, the worker invokes the pipeline: deep male voiceover, FFmpeg vertical rendering, then a YouTube upload requested as **private**. A job is marked `completed` only if the pipeline returns a video ID and confirms private visibility. Generation/provider errors are recorded as `blocked`; rendering or upload failures are recorded as `failed`. Public publishing is not implemented.

The worker is not deployed or scheduled. Run one worker instance until concurrency and crash recovery are tested. Hosted operation needs durable database storage and secure environment secrets. CI remains checks-only and must not upload artifacts.
