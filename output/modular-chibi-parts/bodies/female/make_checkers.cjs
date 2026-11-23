const fs = require("node:fs");
const path = require("node:path");
const parts = path.resolve(__dirname, "..", "..");
const scratch = "/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular";
const parent = path.join(__dirname, "checkers");
fs.mkdirSync(parent, { recursive: true });

function write(directory, name, code) {
  const out = path.join(parent, directory);
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(path.join(out, name), code);
}
for (const name of ["motion_check_dense.py", "motion_check_tri.py"]) {
  let source = fs.readFileSync(path.join(scratch, name), "utf8");
  source = source.slice(0, source.indexOf("sc.render.engine="));
  source = source.replace("sc=bpy.context.scene;", "sc=bpy.context.scene;sc.render.fps=30;")
    .replace("before=set(sc.objects);bpy.ops.import_scene.gltf(filepath=garment)",
      "before=set(sc.objects);bpy.ops.import_scene.gltf(filepath=garment)")
    .replace("g=[o for o in new if o.type=='MESH'][0]", "g,=[o for o in new if o.type=='MESH' and len(o.vertex_groups)]")
    .replace(/    for fr in range\(int\(f0\),int\(f1\)\+1(?:,3)?\):\n        sc\.frame_set\(fr\)/,
      "    from pathlib import Path\n    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))\n    from common import samples, set_frame\n    for fr in samples(f0,f1):\n        set_frame(sc,fr)")
    .replace("(worst,round(mn,4))", "(worst,mn)");
  source += "\nfrom pathlib import Path\n"
    + "destination=Path(out)\ndestination.mkdir(parents=True,exist_ok=True)\n"
    + `(destination/'${name.replace(".py", ".json")}').write_text(json.dumps(res,indent=2)+'\\n')\n`;
  write("shared", name, source);
}
for (const [dir, tuple] of [["act", "('sit_down','sit_idle','stand_up','hold_item')"],
                           ["act2", "('hold_box','hold_bag','take_item')"]]) {
  const input = path.join(parts, "body-fix", dir);
  let source = fs.readFileSync(path.join(input, "motion_check.py"), "utf8");
  source = source.slice(0, source.indexOf("    # Retain the original"))
    .replace("from chibi import *",
      `sys.path.insert(0, ${JSON.stringify(input)})\nfrom chibi import *\nsys.path.insert(0, str(Path(__file__).resolve().parents[2]))\nfrom common import samples, set_frame`)
    .replace(/^LEGACY = .*$/m, "LEGACY = ()")
    .replace(/^ADDED = .*$/m, `ADDED = ${tuple}`)
    .replace("first,last=map(round,act.frame_range)", "first,last=act.frame_range")
    .replace("for f in range(first,last+1):\n                scene.frame_set(f)",
      "for f in samples(first,last):\n                set_frame(scene,f)");
  // Batch mode evaluates both original metrics against the same evaluated surface.
  source = source.replace("        if triangles:",
    "        if triangles == 'both':\n            gt=BVHTree.FromPolygons(gp.tolist(),garment_tri,all_triangles=True)\n            return (inside,len(tree.overlap(gt))),mn,float(gp[:,2].min())\n        if triangles:")
    .replace("max(r['count'] for r in results)",
      "tuple(max(r['count'][i] for r in results) for i in range(2)) if triangles=='both' else max(r['count'] for r in results)")
    .replace("    stem='motion_check_tri' if triangles else 'motion_check'",
      "    stem='motion_check_both' if triangles=='both' else 'motion_check_tri' if triangles else 'motion_check'");
  source += "\n\nif __name__=='__main__':\n    garment_check(triangles='both')\n";
  write(dir, "motion_check.py", source);
  const wrapper = fs.readFileSync(path.join(input, "motion_check_tri.py"), "utf8");
  write(dir, "motion_check_tri.py", wrapper);
}
