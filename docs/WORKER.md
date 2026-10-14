# One-shot worker

Run from the `backend` directory:

```bash
python -m app.worker
```

The worker claims at most one queued job per invocation. It always builds the branded content plan first. To continue to rendering, configure `SCENE_ASSETS_DIR` to a directory containing exactly these four existing files:

- `scene-1.png`
- `scene-2.png`
- `scene-3.png`
- `scene-4.png`

These are pre-generated assets; the repository does not yet include an automatic image-generation provider. If any file is missing, the worker stores the plan and marks the job `blocked`. No video is claimed to exist in that case.

When all four images exist, the worker invokes the existing pipeline: voiceover, FFmpeg vertical render, then a YouTube upload requested as **private**. A job is marked `completed` only if the pipeline returns a video ID and explicitly confirms private visibility. Provider errors or unverified results are recorded as failures. Public publishing is not implemented.

The worker is not deployed or scheduled. Run one worker instance until concurrency and crash recovery are tested. Hosted operation needs durable database storage and secure environment secrets. CI remains checks-only and must not upload artifacts.
