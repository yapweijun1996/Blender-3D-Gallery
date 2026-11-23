"""Run an unchanged supplied checker with its render block on Cycles CPU."""

from pathlib import Path
from contextlib import redirect_stdout
import sys

args = sys.argv[sys.argv.index("--") + 1:]
checker, master, motion, shoes, out = map(lambda val: Path(val).resolve(), args)
out.mkdir(parents=True, exist_ok=True)
source = checker.read_text()
workbench = (
    "sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';"
    "sc.display.shading.color_type='MATERIAL'"
)
assert source.count(workbench) == 1
cycles = """
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 12
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.world = bpy.data.worlds.new('Checker studio')
sc.world.use_nodes = True
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.86, .89, .96, 1)
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
"""
sys.argv = [sys.argv[0], "--", *(str(p) for p in (master, motion, shoes, out))]
with (out / "RESULT.txt").open("w", buffering=1) as log, redirect_stdout(log):
    exec(compile(source.replace(workbench, cycles), str(checker), "exec"), {"__name__": "__main__"})
if checker.stem == "motion_check_tri":
    (out / "motion_check.json").replace(out / "motion_check_tri.json")
