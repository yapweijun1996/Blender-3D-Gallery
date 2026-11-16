#!/usr/bin/env python3
"""Convert Blender's rendered PNG views into the gallery's WebP previews."""

from pathlib import Path
import json

from PIL import Image


ROOT = Path(__file__).resolve().parent


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
    previews = ROOT / "previews"
    save_front(previews / "front.png", previews / "front.webp")
    for view in ("side", "back", "3q"):
        Image.open(previews / f"{view}.png").convert("RGB").save(
            previews / f"{view}.webp", "WEBP", quality=86, method=6
        )
    samples = json.loads((ROOT/'reports/animation-preview-samples.json').read_text())
    for clip, details in samples.items():
        frames = details['playback_frames']
        images = [Image.open(previews/f'animation-frames/{clip.lower()}-{frame:02d}.png').convert('RGB') for frame in frames]
        times = [round(frame*1000/details.get("fps",24)) for frame in frames+[details['duration_frames']]]
        durations = [b-a for a,b in zip(times,times[1:])]
        images[0].save(previews/f'anim-{clip.lower()}.webp',save_all=True,append_images=images[1:],
                       duration=durations,loop=0,quality=88,method=6)


if __name__ == "__main__":
    main()
