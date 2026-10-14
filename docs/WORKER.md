# One-shot worker

The backend queue worker can be run from the `backend` directory with:

```bash
python -m app.worker
```

It claims at most one queued job and records the generated script and four scene prompts. It then marks the job `blocked` because no working image-generation adapter is implemented. It does not claim to have generated a video, and it does not upload to YouTube.

This is deliberately fail-closed. A configured API key alone is not proof that an image provider is integrated. To complete automation, implement and test a provider adapter, persist or supply the resulting scene images, verify the rendered MP4, and only then connect the private YouTube upload path.

The worker is not deployed or scheduled. Use a single worker instance until queue concurrency and recovery behavior have been tested. No workflow artifacts are uploaded by the checks workflow.
