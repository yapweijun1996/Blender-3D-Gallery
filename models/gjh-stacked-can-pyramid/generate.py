"""Build the gjh-stacked-can-pyramid GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from library import derive

from collections import defaultdict
from math import cos, pi, sin, tau


def retopology(f,source):
    tiers = defaultdict(list)
    for o in source.objects:
        if o.name.startswith("CAN_"):
            tiers[o["tier"]].append(source.bounds(o))
        else:
            f.group = "Banquet plinth"
            source.copy(o,0,3)
    f.group = "Six stepped tin courses"
    for tier,cans in sorted(tiers.items()):
        centers = [((a[0]+b[0])/2,(a[1]+b[1])/2) for a,b in cans]
        a,b = cans[0]
        r = (b[0]-a[0])/2
        z,top = a[2],b[2]
        if f.level:
            for x,d in centers:
                f.lathe((x,d),[(.98*r,.98*r,z),(r,r,top-.025),(r,r,top)],
                        lambda v: 3 if v.z>top-.022 or v.z<z+.001 else 1,5)
            continue
        # Trace the scalloped exterior of each complete course. Internal cans
        # disappear behind the closed top and bottom of this distance mesh.
        perimeter = []
        for edge in range(4):
            angle = edge*pi/2
            nx,ny = cos(angle),sin(angle)
            max_dist = max(x*nx+d*ny for x,d in centers)
            row = [(x,d) for x,d in centers if abs(x*nx+d*ny-max_dist)<.001]
            for x,d in sorted(row,key=lambda p:-p[0]*ny+p[1]*nx):
                for turn in (-.70,.70):
                    perimeter.append((x+r*cos(angle+turn),d+r*sin(angle+turn)))
        f.rings([[(x,d,h) for x,d in perimeter] for h in (z,top)],
                lambda v: 3 if abs(v.z-top)<.001 else 1,2)


def build(f):
    derive(f,retopology)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
