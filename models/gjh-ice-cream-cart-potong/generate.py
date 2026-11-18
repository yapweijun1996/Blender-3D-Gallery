"""Build the gjh-ice-cream-cart-potong GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from library import derive

from math import atan2, pi


def canopy(f,obj):
    vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    def point(v,offset=0):
        return (v.x,-v.y,v.z+offset)
    step = 1 if f.level else 2
    rings = [[point(vertices[k+i]) for i in range(0,32,step)] for k in (1,33,65,97)]
    peak = vertices[0]
    crown = [(peak.x+.04*(x-peak.x),-peak.y+.04*(y+peak.y),peak.z) for x,y,z in rings[0]]
    underside = [(x,d,z-.009) for x,d,z in rings[0]]
    f.rings([crown,*rings,underside],lambda v: 0 if int((atan2(v.y-.025,v.x)+2*pi)/(pi/4))%2 else 2)


def retopology(f,source):
    for o in source.objects:
        n = o.name
        if n.startswith("UMBRELLA"):
            f.group = "Citrus parasol"
            if "Scalloped" in n:
                canopy(f,o)
            elif "Rib" not in n or f.level:
                source.copy(o,3,simplify=.32)
        elif n.startswith(("WHEEL","HANDLE","CASTER","CHASSIS","BELL")):
            f.group = "Running gear and handle"
            if n.startswith("WHEEL"):
                if "Cap" not in n and (f.level or not n.endswith(".001") and not n.endswith(".003")):
                    source.cylinder(o,2 if "Hub" in n else 3,16 if f.level else 8,axis=0)
            elif f.level or any(t in n for t in ("PushBar","Support","Fork")):
                source.copy(o,3,simplify=.65 if not f.level else .35)
        else:
            f.group = "Enamel chest and counter"
            if any(t in n for t in ("Score","Grid")) or (not f.level and any(t in n for t in
                    ("Hinge","Wafer","WAFER","Grip","Gasket","Insert","Recess","Shadow","CreamRim"))):
                continue
            color = (1 if any(t in n for t in ("Mint","InsulatedTop")) else
                     0 if any(t in n for t in ("Coral","Shelf","BAR_")) else 2)
            source.copy(o,color,bevel=.002 if n.startswith("BOX") else 0)


def build(f):
    derive(f,retopology)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
