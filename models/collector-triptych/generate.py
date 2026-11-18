"""Build the collector-triptych GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model


def build(f):
    f.group = "Case and cornice"
    f.box((0,-.30,.48),(.49,.35,.91),0,1,.008)
    for z,w in ((.035,.53),(.945,.52),(.981,.55)):
        f.box((0,-.27,z),(w,.44,.038),0,1,.005)
    f.box((0,-.255,.963),(.535,.46,.012),1)
    f.group = "Picture recess"
    f.profile([(-.207,.12),(.207,.12),(.207,.78),(.176,.853),(-.176,.853),(-.207,.78)],
              -.094,.035,1,0,.003)
    f.box((0,-.067,.465),(.376,.018,.61),2,3)
    for x in (-.197,.197):
        f.box((x,-.034,.465),(.013,.052,.65),1,0,.002)
    for z in (.146,.785):
        f.box((0,-.034,z),(.402,.052,.012),1,0,.002)
    for direction,label in ((-1,"Left"),(1,"Right")):
        f.group = label + " hinged leaf"
        f.pose = lambda x,d,z: (direction*(.248+x),d-.12+2.52*x,z)
        f.profile([(0,.064),(.233,.103),(.233,.865),(.201,.917),(.045,.942),(0,.92)],
                  0,.072,0,1,.004)
        f.profile([(.023,.139),(.209,.161),(.209,.813),(.177,.855),(.023,.882)],
                  .045,.018,1,0,.002)
        f.profile([(.032,.158),(.199,.177),(.199,.799),(.170,.837),(.032,.861)],
                  .062,.019,3,2,.002)
        for z in (.21,.49,.775):
            f.tube((.006,.056,z-.044),(.006,.056,z+.044),.014,1)
        for i in range((0,3,6)[f.level]):
            z = .24 + .52*i/max(1,(2,5)[f.level-1])
            f.profile([(.05,z),(.11,z+.019),(.174,z),(.11,z-.012)],.079,.009,1)
        f.pose = None


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
