from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent/'previews'
for p in sorted(root.glob('*.png')):
    image=Image.open(p);assert image.size==(768,768);image.convert('RGB').save(p.with_suffix('.webp'),quality=87,method=6)
    print(p.name,p.stat().st_size,p.with_suffix('.webp').stat().st_size)
