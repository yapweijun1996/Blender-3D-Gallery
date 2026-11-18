"""Build the gjh-tv-wall-mounted GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from library import derive


def retopology(f,source):
    for o in source.objects:
        lo,hi = source.bounds(o)
        mid = [(h+l)/2 for l,h in zip(lo,hi)]
        w,d,h = [b-a for a,b in zip(lo,hi)]
        if o.name.startswith("SCREEN"):
            f.group = "Floating picture plane"
            source.box(o,2,2,.005)
        elif o.name.startswith("PANEL"):
            f.group = "Aluminium gallery reveal"
            source.box(o,1,0,.008)
            f.box((mid[0],lo[1]+d*.10,mid[2]),(.87*w,.22*d,.84*h),0,3,.007)
            for i in range(8 if f.level else 3):
                x = mid[0]+(i-(7 if f.level else 2)/2)*w*.065
                f.box((x,lo[1]-.0006,mid[2]+.22*h),(.011,d*.09,.13*h),2)
        else:
            f.group = "Wall bracket"
            f.box((mid[0],lo[1]+.07*d,mid[2]),(w,.14*d,h),1,0,.004)
            for side in (-1,1):
                f.box((mid[0]+side*.35*w,mid[1],mid[2]),(.13*w,d,.89*h),2,0,.002)


def build(f):
    derive(f,retopology)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
