"""Download images only, never executable code. Retain source hashes and attribution."""
from pathlib import Path
import hashlib, json, urllib.request
ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
 'earth': ('https://space.jpl.nasa.gov/tmaps/pix/ear0xuu2.jpg', 'Caltech/JPL/USGS topographic land/ocean visualization', 'https://space.jpl.nasa.gov/tmaps/earth.html'),
 'mars': ('https://space.jpl.nasa.gov/tmaps/pix/mar0kuu2.jpg', 'NASA/JPL/USGS Viking mosaic', 'https://space.jpl.nasa.gov/tmaps/mars.html'),
 'moon': ('https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_2k.jpg', 'NASA/GSFC/Arizona State University, CGI Moon Kit, Ernie Wright', 'https://svs.gsfc.nasa.gov/4720/'),
 'pluto': ('https://assets.science.nasa.gov/content/dam/science/psd/solar/2023/09/p/l/pluto_color_mapmosaic.jpg', 'NASA/JHUAPL/SwRI, New Horizons MVIC color mosaic', 'https://science.nasa.gov/resource/pluto-global-color-map/'),
}
records = []
for name, (url, credit, page) in SOURCES.items():
 p = ROOT / 'reference' / (name + '.jpg')
 if not p.exists():
  with urllib.request.urlopen(url, timeout=45) as response:
   body = response.read()
  if not body.startswith(b'\xff\xd8'): raise ValueError('Expected JPEG: ' + name)
  p.write_bytes(body)
 records.append(dict(id=name,url=url,page=page,credit=credit,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,retrieved='2026-11-04',usage='Educational visualization; acknowledge original source; no endorsement. See NASA media guidelines and source credits.'))
 print(name, p.stat().st_size)
(ROOT / 'reference' / 'provenance.json').write_text(json.dumps(records, indent=2)+'\n')
