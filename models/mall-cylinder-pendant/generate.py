"""Build a bottle-green tubular pendant with a turned brass optical lip."""
from pathlib import Path
import math
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/"scripts"))
from mall_ceiling_profiles import disc, group, material, revolve, screw
from mall_lighting_delivery import deliver

ROOT="ASSET_MallCylinderPendant"
VIEW=(.90,-.78,1.4)


def build(lod):
    root=group(ROOT)
    green=material("Bottle green satin enamel","285C53",.33,.32)
    brass=material("Champagne brass fittings","C69C61",.72,.29)
    black=material("Blackened flex and baffle","282C2B",.18,.42)
    bright=material("Satin reflector","CEB281",.68,.30)
    opal=material("Opal LED disc","FFE3AD",.03,.28,.58)
    sec=20 if lod else 56
    rose=group("Ceiling canopy",root)
    disc("Green canopy",rose,green,.046,-.020,0,sec,.0025)
    disc("Canopy brass face",rose,brass,.039,-.0225,-.019,sec,.0007)
    disc("Ceiling gland",rose,black,.0075,-.0345,-.022,16 if lod else 24,.0008)
    disc("Suspension cable",root,black,.003,-.231,-.033,12 if lod else 20,.0003)
    pendant=group("Spun metal shade",root)
    disc("Shade entry bush",pendant,black,.0075,-.240,-.227,16 if lod else 24,.0007)
    disc("Turned collar",pendant,brass,.012,-.250,-.2375,20 if lod else 32,.001)
    # The cylindrical barrel remains hollow down to the recessed cone.
    revolve("Enamelled shade",pendant,green,[(.040,-.445),(.043,-.445),(.045,-.442),
        (.045,-.422),(.044,-.419),(.044,-.268),(.043,-.259),(.040,-.254),
        (.033,-.251),(.017,-.247),(.012,-.247),(.012,-.250),(.038,-.261),(.040,-.268)],sec)
    # Fine ribs around the shoulder are spun into one separate removable collar.
    shoulder=[(.040,-.282),(.044,-.282)]
    for i in range(2 if lod else 4):
        z=-.281+i*(.009/(1 if lod else 3))
        shoulder.extend([(.0447,z),(.0452,z+.0005),(.0447,z+.0016)])
    shoulder.extend([(.044,-.2695),(.040,-.2695)])
    revolve("Shoulder grip beads",pendant,green,shoulder,sec)
    revolve("Outlet brass ferrule",pendant,brass,[(.038,-.447),(.043,-.447),(.0452,-.445),
        (.0452,-.439),(.0444,-.438),(.0395,-.439)],sec)
    optic=group("Anti-glare optic",pendant)
    revolve("Dark aperture ring",optic,black,[(.032,-.446),(.0389,-.446),(.041,-.444),
        (.041,-.440),(.0378,-.438),(.032,-.441)],sec)
    revolve("Gold reflector",optic,bright,[(.032,-.444),(.037,-.442),(.025,-.422),
        (.016,-.416),(.012,-.415),(.012,-.418),(.020,-.426),(.027,-.435)],
        20 if lod else 40,smooth=False,phase=.5)
    disc("LED opal diffuser",optic,opal,.014,-.4185,-.416,20 if lod else 36,.0007)
    if not lod:
        for side in [-1,1]:
            screw("Canopy screw",rose,black,(side*.026,0,-.022),(math.pi,0,0),.0023)
        for i in range(3):
            a=math.tau*i/3
            pin=disc("Crown inset rivet",pendant,brass,.0022,-.2525,-.2502,12,.00035)
            pin.location=(.029*math.cos(a),.029*math.sin(a),0)
    return root


if __name__ == "__main__":
    deliver(HERE,ROOT,build,VIEW)
