"""Convert authored Blender renders to lightweight gallery thumbnails (Pillow)."""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
for name in ['mall-directory-kiosk', 'mall-advertising-lightbox', 'mall-trash-bin', 'mall-display-shelf']:
    with Image.open(HERE / 'previews' / f'{name}.png') as render:
        render.convert('RGB').save(HERE / 'previews' / f'{name}.webp', quality=88, method=6)
