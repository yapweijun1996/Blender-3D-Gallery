"""Convert the original Blender PNG renders to lightweight gallery previews."""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
for name in ('hero', 'front', 'side', '3q'):
    with Image.open(HERE / 'previews' / (name + '.png')) as im:
        im.convert('RGB').save(HERE / 'previews' / (name + '.webp'), quality=88, method=6)
