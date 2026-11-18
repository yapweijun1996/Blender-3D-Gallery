"""Build the gjh-grand-piano GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from library import derive

from library import physical


def curved_case(f,o,swatch):
    coords = [physical(o.matrix_world @ v.co) for v in o.data.vertices]
    rim = o.name=="CASE_CurvedRim"
    n = len(coords)//(4 if rim else 2)
    step = 2 if f.level else 4
    indices = sorted({0,1,2,n-1,*range(2,n,step)})
    rings = [[coords[n*k+i] for i in indices] for k in ((0,2,3,1) if rim else (0,1))]
    f.rings(rings,swatch,loop=rim)


def retopology(f,source):
    whites = []
    for o in source.objects:
        n = o.name
        family = n.split("_")[0]
        f.group = ("Raised lid" if family=="LID" else "Bench" if family=="BENCH" else
                   "Keyboard and music rest" if family in ("MUSIC","KEY") else "Case and action")
        if n in ("CASE_CurvedRim","CASE_Underbody","HARP_RecessedSoundboard","LID_RaisedPanel"):
            curved_case(f,o,1 if family=="HARP" else 0)
        elif family=="KEY":
            if f.level:
                source.box(o,2 if "White" in n else 0)
            elif "White" in n:
                whites.append(source.bounds(o))
        elif family=="HARP":
            if "CastBrace" in n or "PinBlock" in n or (f.level and "StringCourse" in n and int(n[-2:])%5==0):
                source.copy(o,1,simplify=.57)
        elif family in ("PEDAL","LYRE","CASTER"):
            if f.level or "Crossbar" in n or "Wheel" in n or "Column" in n:
                if "Axle" not in n and "Fork" not in n:
                    source.copy(o,1,simplify=.7)
        elif f.level or not any(k in n for k in ("Hinge","Socket","Shoulder","OpenStrut","Lip")):
            source.copy(o,3 if "Cushion" in n else 0,simplify=.5)
    if whites:
        f.group = "Keyboard and music rest"
        # A row of octave-sized solids keeps the 64-pixel key tile sharp on Low.
        for i in range(0,len(whites),7):
            group = whites[i:i+7]
            lo = list(map(min,zip(*(a for a,b in group))))
            hi = list(map(max,zip(*(b for a,b in group))))
            f.box([(a+b)/2 for a,b in zip(lo,hi)],[b-a for a,b in zip(lo,hi)],2,2)


def build(f):
    derive(f,retopology)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
