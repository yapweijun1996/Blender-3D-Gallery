from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent/'previews'
for p in sorted(root.glob('*.png')):
    with Image.open(p) as img:
        assert img.size==(768,768)
        img.convert('RGB').save(p.with_suffix('.webp'),quality=88,method=6)
    assert p.with_suffix('.webp').stat().st_size<150*1024
    print(p.name,p.stat().st_size,p.with_suffix('.webp').stat().st_size)
