from pathlib import Path

from PIL import Image

from app.fallback_art import generate_fallback_scene_images


def test_fallback_art_creates_four_vertical_png_scenes(tmp_path):
    paths = generate_fallback_scene_images(str(tmp_path))

    assert len(paths) == 4
    assert [Path(path).name for path in paths] == [
        "scene-1.png", "scene-2.png", "scene-3.png", "scene-4.png"
    ]
    for path in paths:
        image_path = Path(path)
        assert image_path.is_file()
        assert image_path.stat().st_size > 1024
        with Image.open(image_path) as image:
            assert image.format == "PNG"
            assert image.size == (720, 1280)
