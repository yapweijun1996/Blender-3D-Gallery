"""Build a surface-mounted architectural linear luminaire with a continuous opal diffuser."""
from pathlib import Path
import math
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/"scripts"))
from mall_ceiling_profiles import box, extrusion_x, group, material, screw
from mall_lighting_delivery import deliver

ROOT = "ASSET_MallLinearCeilingLight"
VIEW = (1.4, -.90, 1.3)


def build(lod):
    root=group(ROOT)
    ink=material("Night blue anodised extrusion","36485A",.52,.32)
    dark=material("Graphite clips and seals","232C36",.30,.39)
    silver=material("Brushed pewter end cheeks","A8B4B9",.72,.35)
    opal=material("Warm linear opal","FFEBBC",.03,.30,.48)
    # Two fixing saddles carry the extrusion, which is spaced below the ceiling.
    for x,tag in [(-.37,"Left"),(.37,"Right")]:
        box(tag+" fixing saddle",root,silver,(x,0,-.005),(.092,.076,.010),.002,lod)
        for sign,label in [(-1,"front"),(1,"back")]:
            box(tag+" "+label+" saddle return",root,dark,(x,sign*.029,-.0125),(.075,.008,.016),.0012,lod)
    housing=group("Extruded chassis",root)
    # Cross section includes a hollow optic cavity with open underside.
    extrusion_x("Continuous aluminium channel",housing,ink,[
        (-.041,-.062),(-.034,-.062),(-.030,-.051),(-.030,-.031),(.030,-.031),
        (.030,-.051),(.034,-.062),(.041,-.062),(.045,-.057),(.045,-.021),
        (.041,-.016),(-.041,-.016),(-.045,-.021),(-.045,-.057)],-.592,.592)
    for sign,tag in [(-1,"Front"),(1,"Back")]:
        box(tag+" shadow reveal",housing,dark,(0,sign*.045,-.032),(1.165,.0018,.004),.0006,lod)
        if not lod:
            box(tag+" bright extrusion edge",housing,silver,(0,sign*.045,-.038),(1.166,.0014,.0018),.00035,lod)
    lens=group("Continuous diffuser",root)
    # Curved underside has a smooth radiused shoulder and a shallow central convexity.
    profile=[(-.034,-.053),(-.034,-.061),(-.032,-.0645),(-.027,-.0665)]
    for j in range(1,12 if not lod else 4):
        n=12 if not lod else 4
        y=-.027+.054*j/n
        profile.append((y,-.0665-.0025*(1-(y/.027)**2)))
    profile.extend([(.027,-.0665),(.032,-.0645),(.034,-.061),(.034,-.053)])
    extrusion_x("Snap-in opal cover",lens,opal,profile,-.591,.591,True)
    for sign,tag in [(-1,"Left"),(1,"Right")]:
        cap=group(tag+" end assembly",root)
        box(tag+" black gasket",cap,dark,(sign*.5938,0,-.040),(.0038,.090,.049),.0014,lod)
        box(tag+" metal end cheek",cap,silver,(sign*.5972,0,-.040),(.0056,.091,.050),.0027,lod)
        for y in [-.025,.025]:
            screw(tag+" captive fastener",cap,dark,(sign*.5996,y,-.039),
                (0,sign*math.pi/2,0),.0036)
    if not lod:
        for i in range(4):
            box(f"Driver service rib {i+1}",housing,ink,(0,(i-1.5)*.012,-.016),
                (.36,.003,.004),.0008,lod)
    return root


if __name__ == "__main__":
    deliver(HERE,ROOT,build,VIEW)
