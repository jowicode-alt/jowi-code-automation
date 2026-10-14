"""AI Horde image adapter using its free volunteer-powered API.

Anonymous requests have low priority and may be shared by the service. Do not send
private or sensitive prompts through the anonymous key.
"""
import asyncio
import os
from pathlib import Path
import time

import httpx

BASE_URL = os.getenv("AI_HORDE_BASE_URL", "https://aihorde.net/api").rstrip("/")
ANON_KEY = "0000000000"
DEFAULT_MODEL = "AlbedoBase XL (SDXL)"


def _headers() -> dict[str, str]:
    key = os.getenv("AI_HORDE_API_KEY", ANON_KEY).strip() or ANON_KEY
    return {
        "apikey": key,
        "Client-Agent": "TheJowiCodeAutomation:0.1.0:github.com/jowicode-alt/jowi-code-automation",
        "Content-Type": "application/json",
    }


def _is_anonymous(headers: dict[str, str]) -> bool:
    return headers.get("apikey", ANON_KEY) == ANON_KEY


def _image_extension(content_type: str, content: bytes) -> str:
    """Choose an extension from verified image bytes rather than assuming PNG."""
    media_type = content_type.split(";", 1)[0].strip().lower()
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    raise RuntimeError(f"AI Horde returned an unsupported or invalid image ({media_type or 'unknown type'})")


async def generate_scene_images(
    prompts: list[str],
    output_dir: str,
    *,
    timeout_seconds: int = 300,
    poll_seconds: float = 4.0,
) -> list[str]:
    """Generate one image per prompt, with bounded polling and download timeouts."""
    if len(prompts) != 4:
        raise ValueError("Exactly four scene prompts are required")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    headers = _headers()
    model = os.getenv("AI_HORDE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    request_timeout = httpx.Timeout(30.0, connect=15.0)

    async with httpx.AsyncClient(timeout=request_timeout, follow_redirects=True) as client:
        async def submit(index: int, prompt: str) -> tuple[int, str]:
            response = await client.post(
                f"{BASE_URL}/v2/generate/async",
                headers=headers,
                json={
                    "prompt": prompt + " ### text, captions, watermark, extra limbs, blurry, low quality",
                    "params": {
                        "width": 512,
                        "height": 768,
                        "steps": 20,
                        "n": 1,
                        "cfg_scale": 7,
                    },
                    "models": [model],
                    "nsfw": False,
                    "censor_nsfw": True,
                    "r2": True,
                    "shared": _is_anonymous(headers),
                    "dry_run": False,
                },
            )
            response.raise_for_status()
            request_id = response.json().get("id")
            if not request_id:
                raise RuntimeError("AI Horde did not return a generation ID")
            return index, str(request_id)

        submission_results = await asyncio.gather(
            *(submit(index, prompt) for index, prompt in enumerate(prompts, start=1)),
            return_exceptions=True,
        )
        submitted = [result for result in submission_results if not isinstance(result, BaseException)]
        submission_errors = [
            result for result in submission_results if isinstance(result, BaseException)
        ]
        pending = dict(submitted)
        if submission_errors:
            # Some requests may have been accepted even if another submission failed.
            # Cancel every accepted request before surfacing the original error.
            await asyncio.gather(
                *(
                    client.post(
                        f"{BASE_URL}/v2/generate/soft_cancel/{request_id}",
                        headers=headers,
                    )
                    for request_id in pending.values()
                ),
                return_exceptions=True,
            )
            raise submission_errors[0]
        image_urls: dict[int, str] = {}
        try:
            while pending:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"AI Horde generation exceeded {timeout_seconds} seconds; "
                        f"{len(pending)} scene(s) were still pending"
                    )

                async def check(index: int, request_id: str) -> tuple[int, str, dict]:
                    response = await client.get(
                        f"{BASE_URL}/v2/generate/check/{request_id}", headers=headers
                    )
                    response.raise_for_status()
                    return index, request_id, response.json()

                checks = await asyncio.gather(
                    *(check(index, request_id) for index, request_id in list(pending.items()))
                )
                for index, request_id, state in checks:
                    if state.get("faulted"):
                        raise RuntimeError(f"AI Horde failed to generate scene {index}")
                    if state.get("finished", 0) >= 1:
                        status_response = await client.get(
                            f"{BASE_URL}/v2/generate/status/{request_id}", headers=headers
                        )
                        status_response.raise_for_status()
                        generations = status_response.json().get("generations") or []
                        if not generations or not generations[0].get("img"):
                            raise RuntimeError(f"AI Horde returned no image for scene {index}")
                        image_urls[index] = str(generations[0]["img"])
                        pending.pop(index, None)
                if pending:
                    await asyncio.sleep(poll_seconds)
        except Exception:
            # Best-effort cancellation avoids leaving volunteer jobs running after failure.
            await asyncio.gather(
                *(
                    client.post(
                        f"{BASE_URL}/v2/generate/soft_cancel/{request_id}",
                        headers=headers,
                    )
                    for request_id in pending.values()
                ),
                return_exceptions=True,
            )
            raise

        async def download(index: int, url: str) -> tuple[int, str]:
            response = await client.get(url)
            response.raise_for_status()
            if len(response.content) < 1024:
                raise RuntimeError(f"AI Horde scene {index} image was unexpectedly small")
            extension = _image_extension(response.headers.get("content-type", ""), response.content)
            path = directory / f"scene-{index}{extension}"
            path.write_bytes(response.content)
            return index, str(path)

        downloaded = await asyncio.gather(
            *(download(index, url) for index, url in image_urls.items())
        )
        return [path for _, path in sorted(downloaded)]
