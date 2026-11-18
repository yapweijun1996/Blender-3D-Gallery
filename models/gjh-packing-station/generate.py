"""Build the gjh-packing-station GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from library import derive


def retopology(f,source):
    for o in source.objects:
        family = o.name.split("_")[0].split(".")[0]
        f.group = ("Roll and cutter" if family in ("CUTTER","PAPER","ROLL") else
                   "Open carton" if family=="CARTON" else "Wrapping bench")
        color = {"CUTTER":2,"PAPER":3,"ROLL":1,"CARTON":0,"LEG":1,"LOWER":2,"WORKTOP":0}[family]
        if family=="PAPER":
            source.cylinder(o,color,24 if f.level else 10,axis=0)
        else:
            source.copy(o,color,1 if family=="WORKTOP" else 0,.004 if family!="ROLL" else 0)


def build(f):
    derive(f,retopology)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
