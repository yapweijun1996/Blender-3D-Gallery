"""Build the noodle-loom GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from math import cos, pi, sin


def build(f):
    f.group = "Beech trestles"
    for x in (-.44,.44):
        f.box((x,0,.025),(.12,1,.05),2,0,.005)
        for d in (-.33,.33):
            f.tube((x,d,.045),(x,d*.70,.945),.031,0,4,1)
        f.tube((x,-.39,.16),(x,.29,.72),.022,0,4,1)
        f.box((x,0,.944),(.097,.80,.055),0,1,.007)
    f.tube((-.45,-.29,.1),(.45,-.29,.55),.017,2,4)
    f.tube((-.45,-.29,.55),(.45,-.29,.1),.017,2,4)
    f.group = "Drying combs"
    for k,d in enumerate((-.32,0,.32)):
        top = .983-.056*k
        f.tube((-.485,d,top),(.485,d,top),.017,0,8,1)
        for x in (-.47,.47):
            f.box((x,d,top),(.041,.08,.035),2,0,.002)
    for k,d in enumerate((-.32,0,.32)):
        f.group = ("Rear ribbon bank","Middle ribbon bank","Front ribbon bank")[k]
        count = (4,7,10)[f.level]
        for i in range(count):
            x = -.36+.72*(i+.5)/count + .018*(k-1)
            w = .255/count
            top = .99-.056*k
            bottom = .29+.065*k+.058*cos((i+.7*k)*1.8)
            rings = []
            for t in range((3,5,8)[f.level]):
                a = t/((3,5,8)[f.level]-1)
                cx = x+.022*sin(pi*a+i)*a
                depth = d+.074*sin(pi*a)+.052*a
                rw = w*(1+.19*a)
                z = top+(bottom-top)*a
                rings.append([(cx-rw,depth-.016,z),(cx+rw,depth-.016,z),
                              (cx+rw,depth+.016,z),(cx-rw,depth+.016,z)])
            f.rings(rings,3 if (i+k)%4==0 else 1,2)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
