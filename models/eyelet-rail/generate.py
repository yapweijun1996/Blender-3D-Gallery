"""Build the eyelet-rail GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from math import cos, sin, tau


def eyelet(f,x,z,r):
    n = (12,24,36)[f.level]
    # Uncapped annular topology leaves the central bore genuinely open.
    rings = []
    for rad,d in ((r,-.028),(r,.055),(.62*r,.06),(.62*r,-.031)):
        rings.append([(x+rad*cos(tau*i/n),d,z+.65*rad*sin(tau*i/n)) for i in range(n)])
    f.rings(rings,1,0,True,True)


def build(f):
    f.group = "Workshop bench"
    for x in (-.41,.41):
        f.box((x,0,.02),(.115,.86,.04),3,0,.004)
        f.box((x,-.055,.19),(.075,.64,.31),0,0,.006)
    f.box((0,-.015,.363),(1,.96,.056),0,0,.008)
    f.box((0,.467,.353),(.92,.022,.027),1)
    f.group = "Perforated back and uprights"
    f.box((0,-.24,.537),(.87,.055,.264),0,2,.007)
    for x in (-.426,.426):
        f.box((x,-.21,.69),(.052,.10,.62),3,0,.004)
    f.box((0,-.22,.979),(.902,.09,.042),1,0,.004)
    f.group = "Three open architectural eyelets"
    for i,(x,z,r) in enumerate(((-.278,.777,.116),(0,.826,.143),(.278,.797,.10))):
        f.tube((x,-.20,.968),(x,0,z+.62*r),.019,3,6)
        eyelet(f,x,z,r)
    f.group = "Pocket sample and lime lanyard"
    f.box((-.075,.17,.408),(.121,.138,.033),3,3,.016)
    f.group = "Lime lanyard"
    path = [(-.02,.20,.399),(.10,.28,.398),(.19,.225,.398),(.115,.164,.398),(-.02,.185,.399)]
    for a,b in zip(path,path[1:]):
        f.tube(a,b,.008,0,5)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
