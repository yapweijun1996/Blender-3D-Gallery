"""Build the round, spring-retained architectural downlight in metres."""
from pathlib import Path
import math
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/"scripts"))
from mall_ceiling_profiles import bar, box, disc, group, material, revolve, screw
from mall_lighting_delivery import deliver

ROOT = "ASSET_MallRecessedDownlight"
VIEW = (.65, -1.9, .95)


def build(lod):
    root = group(ROOT)
    trim = material("Porcelain white trim", "EDE8DB", .23, .33)
    graphite = material("Deep graphite baffle", "252D31", .32, .37)
    metal = material("Die-cast aluminium", "89969B", .73, .36)
    warm = material("Champagne optical liner", "C9A16C", .80, .25)
    light = material("Opal COB lens", "FFE8AF", .02, .27, .70)
    sec = 20 if lod else 64
    body = group("Recessed housing",root)
    # The plaster contact is the upper flange at zero. A clear cavity is required above it.
    revolve("Rolled plaster trim",body,trim,[
        (.054,-.0055),(.061,-.0055),(.073,-.0045),(.075,-.0030),(.075,-.0012),
        (.0735,0),(.0608,0),(.0608,.003),(.054,.003)], sec)
    revolve("Tapered casting",body,metal,[
        (.054,.001),(.0595,.001),(.0595,.009),(.0555,.015),(.0475,.065),
        (.041,.079),(.038,.080),(.034,.080),(.040,.061),(.0495,.010)],sec)
    for i in range(3 if lod else 5):
        height = .024 + i*(.035/(2 if lod else 4))
        r = .0567 - (height-.018)*.162
        revolve(f"Cooling fin {i+1}",body,metal,[(r-.002,height),(r+.0038,height+.0005),
            (r+.0038,height+.0023),(r-.002,height+.0025)],sec)
    disc("Driver cover",body,graphite,.039,.078,.089,sec,.0016)
    disc("Rear service button",body,metal,.026,.088,.091,sec,.0008)
    optics = group("Deep-set optical assembly",root)
    profile = [(.051,-.005),(.0545,-.005),(.0545,.004),(.044,.033),(.035,.037),(.030,.034)]
    # Serrations are formed into the inner wall, backed by a continuous closed shell.
    for i in range(4 if lod else 7):
        t=i/(3 if lod else 6)
        z=.031-.033*t
        r=.032+.0175*t
        profile.extend([(r+.0015,z), (r+.0002,z-.0014)])
    revolve("Concentric glare baffle",optics,graphite,profile,sec)
    revolve("Faceted optical cone",optics,warm,[(.030,.0335),(.034,.0345),(.021,.0555),
        (.013,.058),(.012,.0555),(.018,.053),(.0245,.044)],20 if lod else 40,smooth=False,phase=.5)
    disc("Recessed LED lens",optics,light,.0136,.054,.057,20 if lod else 40,.001)
    # Opposed steel retaining springs expand above the cutout and fold toward the can for insertion.
    for side,tag in [(-1,"Left"),(1,"Right")]:
        clip=group(tag+" ceiling clip",body)
        x=side
        box(tag+" spring shoe",clip,graphite,(x*.054,0,.030),(.010,.017,.019),.001,lod)
        bar(tag+" spring shank",clip,metal,(x*.057,0,.030),(x*.072,0,.062),.011,.002,lod)
        bar(tag+" sprung outer leaf",clip,metal,(x*.072,0,.062),(x*.085,0,.019),.011,.002,lod)
        box(tag+" contact foot",clip,graphite,(x*.085,0,.019),(.005,.014,.005),.001,lod)
        if not lod:
            screw(tag+" clip pin",clip,warm,(x*.0595,0,.032),(0,side*math.pi/2,0),.0037)
    return root


if __name__ == "__main__":
    deliver(HERE, ROOT, build, VIEW)
