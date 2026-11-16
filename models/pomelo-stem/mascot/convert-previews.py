#!/usr/bin/env python3
"""Convert Blender inspection renders into gallery WebP previews."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
PREVIEWS = ROOT / "previews"


def save_front(source: Path, target: Path) -> None:
    image = Image.open(source).convert("RGB")
    for longest in (1024, 896, 768, 640, 512):
        resized = image.copy()
        if max(resized.size) > longest:
            resized.thumbnail((longest, longest), Image.Resampling.LANCZOS)
        for quality in (88, 84, 80, 76, 72, 68, 64):
            resized.save(target, "WEBP", quality=quality, method=6)
            if target.stat().st_size < 150 * 1024:
                return
    raise ValueError(f"Could not fit the front preview below 150 KiB: {source}")


def main() -> None:
    save_front(PREVIEWS / "front.png", PREVIEWS / "front.webp")
    for view in ("side", "back", "3q", "expressions"):
        Image.open(PREVIEWS / f"{view}.png").convert("RGB").save(
            PREVIEWS / f"{view}.webp", "WEBP", quality=86, method=6
        )


if __name__ == "__main__":
    main()
