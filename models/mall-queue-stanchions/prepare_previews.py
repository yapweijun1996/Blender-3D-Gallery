from pathlib import Path
from PIL import Image
p=Path(__file__).resolve().parent/'previews'
for src in sorted(p.glob('*.png')):
    Image.open(src).convert('RGB').save(src.with_suffix('.webp'),quality=88,method=6)
