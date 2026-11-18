"""Build the specimen-drawers GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model


def build(f):
    f.group = "Plinth and open niche"
    f.box((0,0,.025),(1,.85,.05),0,1,.006)
    f.box((0,.025,.279),(.36,.78,.045),3,0,.004)
    f.box((0,-.345,.21),(.39,.12,.38),0,1)
    f.group = "Porcelain counting bowl"
    f.lathe((0,.065),[(.052,.097,.302),(.07,.12,.316),(.115,.19,.37),
                       (.112,.185,.384),(.098,.161,.379),(.056,.09,.33)],1,
                       (12,20,32)[f.level])
    for side,label in ((-1,"Left"),(1,"Right")):
        f.group = label+" stepped bank"
        for col,(cx,w,h) in enumerate(((.413,.17,1),(.252,.15,.785),(.145,.066,.56))):
            x = side*cx
            f.box((x,0,(.05+h)/2),(w,.72,h-.05),0,1,.003)
            f.box((x,.364,(.094+h-.051)/2),(w*.90,.02,h-.145),2,2)
            f.box((x,.004,h-.016),(w+.008,.78,.032),0,1,.002)
            if f.level:
                for j in range(4 if col!=2 else 3):
                    z = .14+(h-.23)*(j+.5)/(4 if col!=2 else 3)
                    f.box((x,.381,z),(w*.82,.035,(h-.22)*.15),0,3)
                    f.box((x,.406,z),(w*.28,.032,.013),3)
    f.group = "Three open drawers"
    for x,z in ((-.413,.66),(-.252,.35),(.413,.48)):
        f.box((x,.413,z),(.142,.167,.078),0,1,.003)
        f.box((x,.498,z),(.15,.026,.09),2,3,.003)
        f.box((x,.521,z+.002),(.043,.039,.014),3)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
