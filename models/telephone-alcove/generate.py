"""Build the telephone-alcove GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model


def build(f):
    f.group = "Cork base and side cheeks"
    f.box((0,0,.026),(.98,.96,.052),3,1,.005)
    for x,h in ((-.46,.74),(.46,.66)):
        f.box((x,-.06,(.05+h)/2),(.07,.78,h-.05),0,2,.005)
        f.box((x,.335,(.05+h)/2),(.073,.045,h-.05),3,1,.002)
    f.group = "Graphite felt lining"
    f.profile([(-.452,.05),(.452,.05),(.452,.65),(-.128,.974),(-.452,.734)],
              -.425,.085,0,2,.004)
    for x in (-.305,0,.305):
        height = .621 if x>.25 else .70
        f.box((x,-.369,height/2+.06),(.009,.023,height),1)
    f.group = "Asymmetric nickel gable"
    for section in ([(-.50,.737),(-.128,.964),(-.128,1),(-.50,.773)],
                    [(-.128,.964),(.50,.639),(.50,.675),(-.128,1)]):
        f.profile(section,-.033,.926,1,0,.002)
        f.profile(section,.439,.038,3,1,.002)
    shelf = (1.09-f.spec["anchor"]["position_m"][1])/f.spec["anchor"]["envelope_whd_m"][1]
    f.group = "Floating handset shelf"
    f.box((-.032,.006,shelf-.016),(.69,.78,.032),3,1,.005)
    f.box((-.032,.394,shelf-.016),(.66,.019,.018),1)
    for x in (-.252,.19):
        f.profile([(x-.022,shelf-.015),(x+.022,shelf-.015),(x+.022,shelf-.085)],
                  -.135,.31,1)
    f.group = "Graphite felt lining"
    if f.level:
        for j in range(3*f.level):
            f.box((-.317+j*.108,-.369,.58),(.068,.017,.176),0,2,.005)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
