"""Reopen the saved master, exercise its embedded guide editor, and re-export in isolation."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import bpy

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from export_source import export_portrait


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh_position(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    obj = obj.evaluated_get(dg)
    return [tuple(v.co) for v in obj.data.vertices]


source = Path(bpy.data.filepath)
expected_glb = BASE / "exports/indigo-ninja-head.glb"
source_before = sha(source)
group = bpy.data.collections["Indigo | editable hair spines"]
sail = bpy.data.objects["Guide 05 | Crown sail"]
lock = "Lock 05 | Crown sail"
neighbour = bpy.data.objects["Lock 04 | Windswept forecrest"]
prior_vertices = mesh_position(bpy.data.objects[lock])
neighbour_before = mesh_position(neighbour)
with tempfile.TemporaryDirectory() as folder:
    dest = Path(folder) / "edit-test.glb"
    export_portrait(dest)
    replay = sha(dest)
    assert replay == sha(expected_glb), "Export from the saved master differs from the delivered export"
    bpy.ops.object.select_all(action="DESELECT")
    group.hide_viewport = False
    bpy.context.view_layer.update()
    sail.select_set(True)
    bpy.context.view_layer.objects.active = sail
    tip = sail.data.splines[0].bezier_points[-1]
    tip.co.x += .04
    bpy.context.view_layer.update()
    block = bpy.data.texts["INSTRUCTIONS - Refresh hair guides.py"]
    exec(compile(block.as_string(), block.name, "exec"), {"__name__":"__main__"})
    bpy.context.view_layer.update()
    after_vertices = mesh_position(bpy.data.objects[lock])
    assert len(after_vertices) == len(prior_vertices)
    max_dx = max(abs(b[0]-a[0]) for a,b in zip(prior_vertices, after_vertices))
    assert max_dx > .025 and mesh_position(neighbour) == neighbour_before
    group.hide_viewport = True
    export_portrait(dest)
    edited = sha(dest)
    assert edited != replay
    assert sha(source) == source_before
    report = dict(blender=bpy.app.version_string, sourceSha256=source_before,
                  deliveredSha256=replay, editableGuides=len(group.objects),
                  guideTipEditMetres=.04, maxCageEvaluatedDeltaXMetres=max_dx,
                  adjacentLockUnchanged=True, savedSourceUnchanged=True, editedCopyGlbSha256=edited)
    (BASE / "qa/editability.json").write_text(json.dumps(report, indent=2)+"\n")
    print(report)
