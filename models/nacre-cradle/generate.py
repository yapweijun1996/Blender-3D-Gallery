"""Build the nacre-cradle GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from math import atan2, cos, sin, tau


def valve(f, upright):
    # Polar bowl with separate inner and outer skins, a rolled scalloped lip
    # and small closed heel faces. Both valves hinge at the rear of the stand.
    n = (24,48,72)[f.level]
    sections = (3,5,8)[f.level]
    rings = []
    for inside in (False,True):
        for k in range(sections):
            r = .036+.964*(k if not inside else sections-1-k)/(sections-1)
            ring = []
            for i in range(n):
                a = tau*i/n
                wave = 1+.037*cos(11*a)*r
                x = .49*r*cos(a)*wave*(1+.12*sin(a))
                if upright:
                    z = .655+.335*r*sin(a)*wave
                    angle = atan2(x,.07+z-.32)
                    flute = .032*(.5+.5*cos(34*angle))**2
                    d = -.43+.31*r*r+.11*r*sin(a)+flute+(.045 if inside else 0)
                else:
                    d = .055+.425*r*sin(a)*wave
                    flute = .013*r*cos(12*a)
                    z = .32+.115*r*r+.028*r*sin(a)+flute+(.027 if inside else 0)
                ring.append((x,d,z))
            rings.append(ring)
    if upright:
        peak = max(z for ring in rings for x,d,z in ring)
        rings = [[(x,d,z/peak) for x,d,z in ring] for ring in rings]
    f.rings(rings,0,2,True,projection=(0,2) if upright else (0,1))


def build(f):
    f.group = "Teak foot and mineral pedestal"
    f.lathe((0,0),[(.27,.32,0),(.30,.36,.034),(.23,.27,.071),
                    (.165,.22,.244),(.235,.31,.315)],3,pattern=1)
    f.group = "Lower valve"
    valve(f,False)
    f.group = "Upper valve"
    valve(f,True)
    f.group = "Hinge and level gift shelf"
    f.tube((-.26,-.27,.374),(.26,-.27,.374),.032,1)
    shelf = (1.15-f.spec["anchor"]["position_m"][1])/f.spec["anchor"]["envelope_whd_m"][1]
    f.box((0,.05,shelf-.016),(.58,.43,.032),1,0,.007)
    f.box((0,.257,shelf-.017),(.50,.016,.012),2,0,.003)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
