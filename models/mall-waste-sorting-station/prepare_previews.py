from pathlib import Path
from PIL import Image
here = Path(__file__).resolve().parent
Image.open(here/'previews/mall-waste-sorting-station.png').convert('RGB').save(
    here/'previews/mall-waste-sorting-station.webp', 'WEBP', quality=90, method=6)
