from pathlib import Path
from PIL import Image
here = Path(__file__).resolve().parent
Image.open(here/'previews/mall-floor-direction-sign.png').convert('RGB').save(
    here/'previews/mall-floor-direction-sign.webp', 'WEBP', quality=90, method=6)
