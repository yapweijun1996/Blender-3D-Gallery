from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parent
with Image.open(root / 'previews/mall-event-booth.png') as image: image.convert('RGB').save(root / 'previews/mall-event-booth.webp', quality=88, method=6)
