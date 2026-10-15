"""Deterministic, offline scene-art fallback for when volunteer image APIs are throttled.

This is intentionally an illustrated fallback, not a claim of photorealistic AI output.
It preserves the channel's black lion / black suit / white shirt / gold tie palette and
keeps a single recognizable character across all four vertical scenes.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZE = (720, 1280)
GOLD = (218, 170, 62)
DARK = (9, 12, 18)


def _background(scene: int) -> Image.Image:
    image = Image.new("RGB", SIZE)
    pixels = image.load()
    for y in range(SIZE[1]):
        t = y / (SIZE[1] - 1)
        for x in range(SIZE[0]):
            glow = max(0.0, 1 - (((x - 470) / 520) ** 2 + ((y - 300) / 700) ** 2))
            accent = (scene * 9) % 22
            pixels[x, y] = (
                int(7 + 12 * (1 - t) + glow * (24 + accent)),
                int(10 + 10 * (1 - t) + glow * 15),
                int(17 + 15 * (1 - t) + glow * 8),
            )
    draw = ImageDraw.Draw(image, "RGBA")
    # Minimal office architecture / horizon; no on-screen words or captions.
    draw.polygon([(0, 930), (720, 790), (720, 1280), (0, 1280)], fill=(5, 7, 12, 230))
    for x in (70, 185, 555, 655):
        draw.line((x, 170, x, 930), fill=(218, 170, 62, 32), width=2)
    draw.line((0, 920 + scene * 5, 720, 790 + scene * 5), fill=(218, 170, 62, 90), width=3)
    return image


def _draw_lion(draw: ImageDraw.ImageDraw, scene: int) -> None:
    # Stylized, consistent lion portrait in a formal suit.
    cx, cy = 360 + (scene - 2) * 8, 465
    # Mane silhouette and ears
    draw.ellipse((cx - 172, cy - 185, cx + 172, cy + 190), fill=(20, 20, 23), outline=(218, 170, 62), width=5)
    draw.ellipse((cx - 145, cy - 220, cx - 65, cy - 135), fill=(24, 24, 27), outline=(115, 88, 39), width=3)
    draw.ellipse((cx + 65, cy - 220, cx + 145, cy - 135), fill=(24, 24, 27), outline=(115, 88, 39), width=3)
    # Face
    draw.ellipse((cx - 112, cy - 145, cx + 112, cy + 115), fill=(39, 35, 31), outline=(164, 128, 62), width=3)
    # Brow and eyes, serious expression
    draw.line((cx - 84, cy - 50, cx - 20, cy - 38), fill=(13, 12, 12), width=13)
    draw.line((cx + 20, cy - 38, cx + 84, cy - 50), fill=(13, 12, 12), width=13)
    draw.ellipse((cx - 69, cy - 30, cx - 29, cy - 9), fill=(242, 193, 71))
    draw.ellipse((cx + 29, cy - 30, cx + 69, cy - 9), fill=(242, 193, 71))
    draw.ellipse((cx - 55, cy - 28, cx - 43, cy - 10), fill=(4, 5, 7))
    draw.ellipse((cx + 43, cy - 28, cx + 55, cy - 10), fill=(4, 5, 7))
    # Muzzle and nose
    draw.ellipse((cx - 65, cy + 5, cx + 65, cy + 83), fill=(86, 73, 60))
    draw.polygon([(cx - 24, cy + 24), (cx + 24, cy + 24), (cx, cy + 47)], fill=(12, 11, 12))
    draw.line((cx, cy + 47, cx, cy + 66), fill=(15, 13, 13), width=4)
    draw.arc((cx - 32, cy + 50, cx, cy + 82), 10, 145, fill=(14, 12, 12), width=3)
    draw.arc((cx, cy + 50, cx + 32, cy + 82), 35, 170, fill=(14, 12, 12), width=3)
    # Suit shoulders and torso
    draw.polygon([(cx - 150, cy + 155), (cx + 150, cy + 155), (cx + 230, 1040), (cx - 230, 1040)], fill=(7, 8, 12), outline=(90, 75, 49))
    draw.polygon([(cx - 74, cy + 138), (cx + 74, cy + 138), (cx + 115, 880), (cx - 115, 880)], fill=(232, 229, 218))
    draw.polygon([(cx - 45, cy + 150), (cx + 45, cy + 150), (cx + 24, 810), (cx - 24, 810)], fill=(218, 170, 62))
    draw.line((cx - 150, cy + 160, cx - 95, 870), fill=(218, 170, 62, 160), width=4)
    draw.line((cx + 150, cy + 160, cx + 95, 870), fill=(218, 170, 62, 160), width=4)


def generate_fallback_scene_images(output_dir: str) -> list[str]:
    """Write four valid PNG scene assets locally, without network/API dependencies."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for scene in range(1, 5):
        image = _background(scene)
        draw = ImageDraw.Draw(image, "RGBA")
        _draw_lion(draw, scene)
        # Cinematic vignette and gold edge glow.
        overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle((18, 18, SIZE[0] - 19, SIZE[1] - 19), outline=(218, 170, 62, 100), width=2)
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        image = image.filter(ImageFilter.GaussianBlur(0.25))
        path = directory / f"scene-{scene}.png"
        image.save(path, format="PNG", optimize=True)
        if not path.is_file() or path.stat().st_size < 1024:
            raise RuntimeError(f"Local fallback failed to create scene {scene}")
        paths.append(str(path))
    return paths
