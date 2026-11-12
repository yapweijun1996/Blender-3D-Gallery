"""Original seeded terrazzo surface artwork, no downloaded pixels. Python + Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw
import random, math
HERE=Path(__file__).resolve().parent
rng=random.Random(421)
# Supersampled, restrained warm ivory aggregate for a generic SG/MY retail interior.
size=1024
im=Image.new('RGB',(size,size),(216,210,193)); draw=ImageDraw.Draw(im)
colors=[(244,239,220),(234,225,207),(168,163,149),(141,153,146),(188,177,150),(110,126,124)]
for i in range(1900):
    x,y=rng.randrange(size),rng.randrange(size); r=rng.uniform(1.0,4.3) if i<1700 else rng.uniform(4.5,10)
    points=[]
    sides=rng.choice([4,5,6]); angle=rng.random()*math.tau
    for n in range(sides):
        a=angle+n*math.tau/sides; radius=r*rng.uniform(.65,1.15)
        points.append((x+math.cos(a)*radius,y+math.sin(a)*radius))
    color=rng.choices(colors,[36,30,15,6,10,3])[0];draw.polygon(points,fill=color)
im.resize((512,512),Image.Resampling.LANCZOS).save(HERE/'textures/terrazzo-original.png',optimize=True)
print('Original texture seed 421: 512 x 512 PNG')
