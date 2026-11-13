from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent
for p in (root/'previews').glob('*.png'):
    Image.open(p).convert('RGB').save(p.with_suffix('.webp'),'WEBP',quality=90,method=6)
