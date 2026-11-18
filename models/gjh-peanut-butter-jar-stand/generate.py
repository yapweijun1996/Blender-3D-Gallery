"""Build the gjh-peanut-butter-jar-stand GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from library import derive


def retopology(f,source):
    lids = {o.name.split("_")[-1]:o for o in source.objects if o.name.startswith("PlainLid")}
    for o in source.objects:
        n = o.name
        if n.startswith("PlainLid"):
            continue
        if n.startswith("JarBody"):
            f.group = "Three rows of capped jars"
            lo,hi = source.bounds(o)
            _,cap = source.bounds(lids[n.split("_")[-1]])
            x,d = [(lo[i]+hi[i])/2 for i in (0,1)]
            r = (hi[0]-lo[0])/2
            z,top = lo[2],cap[2]
            rings = [(r*.94,r*.94,z),(r,r,hi[2]-.006),(r,r,top)]
            if f.level:
                rings = [(r*.88,r*.88,z),(r,r,z+.014),(r,r,hi[2]-.021),
                         (.86*r,.86*r,hi[2]-.004),(r,r,hi[2]),(r,r,top)]
            f.lathe((x,d),rings,lambda v: 0 if v.z>hi[2]-.004 else 2,
                    8 if f.level else 5)
        else:
            f.group = "Tiered breakfast stand" if "Sign" not in n else "Blank header"
            if not f.level and any(t in n for t in ("Reveal","FrontInset","BlankSign_Back")):
                continue
            color = (3 if "Deck" in n or "BlankSign_Front" in n else
                     0 if "Cabinet" in n or "Core" in n else 1)
            source.copy(o,color,3 if "FrontPanel" in n else 0)


def build(f):
    derive(f,retopology)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
