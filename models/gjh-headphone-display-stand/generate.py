"""Build the gjh-headphone-display-stand GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from library import derive


def retopology(f,source):
    for o in source.objects:
        n = o.name
        if n.startswith("HP"):
            f.group = "Six over-ear headsets"
            if "HeadbandShell" in n:
                points = [o.matrix_world @ v.co for v in o.data.vertices]
                indices = range(0,29,4 if f.level else 7)
                band = [[(v.x,-v.y,v.z) for v in points[4*i:4*i+4]] for i in indices]
                if not f.level:
                    # Carry the band down into each cup in the low-poly shell.
                    # The original separate telescopic yokes serve this joint.
                    left,right = [[(x,d,z-.046) for x,d,z in end] for end in (band[0],band[-1])]
                    band = [left,*band,right]
                f.rings(band,0,0,True)
            elif "OvalShell" in n or (f.level and "SoftEarCushion" in n):
                color = 2 if "OvalShell" in n and not n.startswith(("HP01","HP05")) else 1
                source.cylinder(o,color,10 if f.level else 5,axis=0)
            elif f.level and "Telescopic" in n:
                source.box(o,2)
        elif n.startswith("HOOK"):
            if "CurvedJ" in n:
                f.group = "Suspended hooks"
                verts = [o.matrix_world @ v.co for v in o.data.vertices]
                rings = [verts[i:i+8] for i in range(0,len(verts),8)]
                sampled = rings[::3 if f.level else 6]
                if sampled[-1]!=rings[-1]:
                    sampled.append(rings[-1])
                f.rings([[(v.x,-v.y,v.z) for v in ring[::2]] for ring in sampled],2)
        else:
            if not f.level and any(t in n for t in ("Socket","Reveal","Inset","BlankBack","Card","FrontLip")):
                continue
            f.group = "Acoustic rack"
            source.box(o,3 if "BlankFront" in n else 2 if "RAIL" in n else 0,0,.001)


def build(f):
    derive(f,retopology)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
