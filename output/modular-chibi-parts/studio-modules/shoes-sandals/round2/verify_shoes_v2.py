"""Run the supplied geometry checks and an independent dense export check."""
import ast
from contextlib import redirect_stdout
import math
from pathlib import Path
import sys
from types import ModuleType

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

from fit_shoes_v2 import (EXPORT, GATE, MASTER, MOTION, OUT, PARTS, SOURCE, attach,
                          bind, digest, faces, load_bank, report, signed_nearest, world_coords)

SHARED_TOOLS = Path("/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/"
                    "26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular")
ACTIONS = PARTS / "actions-fix/actions_fixed.glb"
CARRY = PARTS / "actions-hold2/hold_actions.glb"
BANKS = (
    (MOTION, ("walk", "run", "wave", "jump", "idle", "nod", "dance")),
    (ACTIONS, ("sit_down", "sit_idle", "stand_up", "hold_item")),
    (CARRY, ("hold_box", "hold_bag", "take_item")),
)


class CpuPreviews(ast.NodeTransformer):
    """Only substitute the headless renderer configuration."""
    def visit_Assign(self, node):
        if not isinstance(node.value, ast.Constant) or node.value.value != "BLENDER_WORKBENCH":
            return node
        target = node.targets[0]
        scene = target.value.value.id
        node.value = ast.Constant("CYCLES")
        settings = ast.parse(f"""
{scene}.cycles.device = 'CPU'
{scene}.cycles.samples = 8
{scene}.cycles.use_denoising = True
{scene}.render.resolution_percentage = 100
{scene}.render.image_settings.file_format = 'PNG'
{scene}.world = bpy.data.worlds.new('Checker studio')
{scene}.world.use_nodes = True
{scene}.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.86, 0.89, 0.96, 1)
{scene}.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.65
""").body
        return [node, *[ast.copy_location(setting, node) for setting in settings]]


def execute(script, module):
    syntax = ast.parse(script.read_text(), str(script))
    syntax = ast.fix_missing_locations(CpuPreviews().visit(syntax))
    exec(compile(syntax, str(script), "exec"), module)


def check_supplied(bank, variant):
    triangle = variant == "tri"
    if bank == "shared":
        folder = SHARED_TOOLS
        script = folder / ("motion_check_tri.py" if triangle else "motion_check_dense.py")
        extra = []
    else:
        if bank not in ("actions", "carry"):
            raise ValueError(bank)
        folder = PARTS / ("body-fix/act" if bank == "actions" else "body-fix/act2")
        script = folder / ("motion_check_tri.py" if triangle else "motion_check.py")
        extra = [str(ACTIONS if bank == "actions" else CARRY)]
    out = OUT / "checks" / bank / variant
    out.mkdir(parents=True, exist_ok=True)
    sys.argv = [str(script), "--", str(MASTER), str(MOTION), str(EXPORT), str(out), *extra]
    sys.path.insert(0, str(folder))
    module = {"__file__": str(script), "__name__": "__main__"}
    with (out / "checker.txt").open("w", buffering=1) as log, redirect_stdout(log):
        print(f"Checker SHA-256 {digest(script)}")
        print(f"Export SHA-256 {digest(EXPORT)}")
        if bank != "shared" and triangle:
            helper = folder / "motion_check.py"
            print(f"Checker helper SHA-256 {digest(helper)}")
            original = ModuleType("motion_check")
            original.__file__ = str(helper)
            sys.modules[original.__name__] = original
            execute(helper, original.__dict__)
        execute(script, module)


def evaluated_check(path):
    scene, arm, body, shoe = attach(path)
    body_tri, shoe_tri = (faces(obj.data).tolist() for obj in (body, shoe))

    def measure(frame):
        base = math.floor(frame)
        scene.frame_set(base, subframe=frame - base)
        b, s = world_coords(body), world_coords(shoe)
        body_tree = BVHTree.FromPolygons(b.tolist(), body_tri, all_triangles=True)
        shoe_tree = BVHTree.FromPolygons(s.tolist(), shoe_tri, all_triangles=True)
        distance = np.array([signed_nearest(body_tree, point)[0] for point in s])
        return dict(frame=frame, inside=int((distance < 0).sum()),
                    overlap_pairs=len(body_tree.overlap(shoe_tree)), min_signed_m=float(distance.min()))

    result = {"rest": [measure(1)]}
    for i, (bank, names) in enumerate(BANKS):
        if i > 0:
            scene.render.fps = 30
            scene.render.fps_base = 1
        actions = load_bank(bank)
        for name in names:
            action = actions[name]
            bind(arm, action)
            begin, end = map(round, action.frame_range)
            ticks = 2 if name == "run" else 1
            result[name] = [measure(f / ticks) for f in range(begin * ticks, end * ticks + 1)]

    summary = {}
    for name, rows in result.items():
        closest = min(rows, key=lambda row: row["min_signed_m"])
        summary[name] = dict(samples=len(rows), max_inside=max(r["inside"] for r in rows),
                             max_overlap_pairs=max(r["overlap_pairs"] for r in rows),
                             min_signed_m=closest["min_signed_m"],
                             minimum_frame=closest["frame"])
        print("DENSE", name, summary[name], flush=True)

    stem = "export_dense" if path == EXPORT else "v1_dense"
    report(stem + ".json", dict(glb_sha256=digest(path), summary=summary, frames=result))
    if path == EXPORT:
        failures = [name for name, value in summary.items()
                    if value["max_inside"] or value["max_overlap_pairs"] or value["min_signed_m"] < GATE]
        if failures:
            raise RuntimeError(f"Failed export gate for {failures}")


def rest_surface():
    result = {}
    for path in (SOURCE, EXPORT):
        _, _, _, shoe = attach(path)
        mesh = bmesh.new()
        mesh.from_mesh(shoe.data)
        bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-6)
        mesh.verts.index_update()
        positions = [vertex.co.copy() for vertex in mesh.verts]
        triangles = [tuple(vertex.index for vertex in face.verts) for face in mesh.faces]
        tree = BVHTree.FromPolygons(positions, triangles, all_triangles=True)
        count = sum(i < j and set(triangles[i]).isdisjoint(triangles[j]) for i, j in tree.overlap(tree))
        result[path.name] = dict(sha256=digest(path), open_edges=sum(edge.is_boundary for edge in mesh.edges),
                                 nonmanifold_edges=sum(not edge.is_manifold for edge in mesh.edges),
                                 nonadjacent_self_overlap_pairs=count,
                                 lowest_sole_world_m=float(world_coords(shoe)[:, 2].min()))
        mesh.free()
    report("rest_surface.json", result)
    print("REST_SURFACE", result, flush=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    if args[0] == "dense":
        evaluated_check(SOURCE if "--v1" in args else EXPORT)
    elif args[0] == "surface":
        rest_surface()
    else:
        check_supplied(*args)
