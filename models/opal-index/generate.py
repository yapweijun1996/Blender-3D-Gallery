"""Build the opal-index GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model


def build(f):
    f.group = "Recessed island base"
    f.box((0,0,.03),(.81,.78,.06),2,0,.009)
    f.box((0,0,.18),(.91,.87,.24),3,0,.008)
    f.box((0,.45,.17),(.67,.022,.14),2,3,.004)
    f.box((0,0,.314),(.97,.94,.035),0,0,.006)
    shelf = (1.15-f.spec["anchor"]["position_m"][1])/f.spec["anchor"]["envelope_whd_m"][1]
    for i in range(4):
        f.group = ("Tall rear index","Second index","Third index","Front index and shelf")[i]
        x = -.135+.09*i
        top = 1-.128*i
        d = -.355+i*.191
        w = .34-.022*i
        outline = [(x-w,.315),(x+w,.315),(x+w,top-.13),(x+w-.09,top-.13),
                   (x+w-.09,top-.028),(x+w-.12,top),(x-w+.055,top),
                   (x-w,top-.054)]
        f.profile(outline,d,.075,0 if i%2==0 else 1,2,.006)
        f.box((x-w+.025,d+.042,(.33+top-.07)/2),(.016,.016,top-.40),1,0,.002)
        if f.level:
            f.box((x-w+.109,d+.044,top-.046),(.094,.012,.012),3)
        if i==3:
            f.group = "Level sample shelf"
            f.box((0,.315,shelf-.018),(.69,.37,.036),3,0,.003)
            f.box((0,.488,shelf-.019),(.64,.022,.019),1)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
