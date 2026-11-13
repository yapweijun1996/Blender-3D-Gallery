from pathlib import Path
from PIL import Image
p=Path(__file__).resolve().parent/'previews'
for src in p.glob('*.png'):
    im=Image.open(src).convert('RGB');im.thumbnail((768,768));im.save(src.with_suffix('.webp'),'WEBP',quality=86,method=6)
