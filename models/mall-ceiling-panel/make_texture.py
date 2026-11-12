"""Original deterministic mineral-fibre surface; no third-party pixels."""
from pathlib import Path
import random
from PIL import Image, ImageDraw
p=Path(__file__).resolve().parent/'textures/mineral-fibre-original.png'
r=random.Random(422);im=Image.new('RGB',(256,256),(225,222,210));d=ImageDraw.Draw(im)
for _ in range(5800):
    x,y=r.randrange(256),r.randrange(256);v=r.randrange(-16,10)
    d.point((x,y),fill=(225+v,222+v,210+v))
for _ in range(340):
    x,y=r.randrange(256),r.randrange(256);d.line((x,y,x+1,y),fill=(193,192,182))
im.save(p)
