"""Build the patch-folio GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model


def build(f):
    f.group = "Ash counter"
    f.box((0,0,.027),(.82,.80,.054),1,0,.008)
    f.profile([(-.43,.052),(.43,.052),(.45,.395),(-.45,.395)],0,.83,3,1,.008)
    f.box((0,0,.402),(.95,.96,.039),1,0,.006)
    f.box((0,.421,.232),(.73,.026,.245),2,3,.005)
    f.group = "Sample ledge"
    shelf = (1.15-f.spec["anchor"]["position_m"][1])/f.spec["anchor"]["envelope_whd_m"][1]
    f.box((0,.24,shelf-.014),(.93,.52,.028),0,0,.006)
    for i,(x,top,slope) in enumerate(((-.31,.83,-.64),(0,1,.7),(.31,.908,-.64))):
        f.group = ("Sage outer leaf","Porcelain centre leaf","Plum outer leaf")[i]
        f.pose = lambda u,d,z: (u+x,d-.17+u*slope,z)
        outline = [(-.17,.418),(.165,.418),(.165,top-.085),(.095,top),(-.17,top-.027)]
        f.profile(outline,0,.06,(1,0,2)[i],2,.003)
        f.profile([(.095,top),(.165,top-.085),(.095,top-.082)],.039,.018,3,0)
        f.box((-.146,.043,(.44+top-.06)/2),(.014,.024,top-.50),3)
        for j in range((1,3,5)[f.level]):
            z = .50+j*.065
            f.box((-.012,.045,z),(.169,.022,.035),0 if i!=1 else 1,3,.002)
        f.pose = None


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
