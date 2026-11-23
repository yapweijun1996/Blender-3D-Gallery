"""Fold the saved 2 m straight-wall finish sections into a new editable corner."""
import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector

BASE = Path(__file__).resolve().parent
SLUG = "mall-wall-corner-2m"
STRAIGHT = "mall-wall-module-2m"
ROOT = "ASSET_MallWallCorner2m"
SOURCE = BASE / "sources" / f"{SLUG}.blend"
LEVELS = ("LOD0", "LOD1", "LOD2")


def new_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def empty(name, collection, parent=None):
    obj = bpy.data.objects.new(name, None)
    collection.objects.link(obj)
    obj.parent = parent
    obj.empty_display_size = .09
    return obj


def arm_mesh(source, arm, collection, root, name):
    original = source.data
    xyz = [source.matrix_local @ v.co for v in original.vertices]
    on_cut = [abs(v.x-1) < 1e-6 for v in xyz]
    verts, faces, mapped = [], [], []
    for v in xyz:
        depth = -v.y
        x = v.x-1
        if v.x > .98:
            x -= depth
        pos = (x, -depth, v.z) if arm == 0 else (-depth, x, v.z)
        verts.append(pos)
    for p in original.polygons:
        # Both arms share the miter's perimeter. A cap here would add coincident
        # interior faces. Separate arm objects keep native collision bounds tight.
        if all(on_cut[i] for i in p.vertices):
            continue
        loops=list(p.loop_indices)
        if arm==1:
            loops.reverse()
        faces.append(tuple(original.loops[i].vertex_index for i in loops))
        mapped.append((p, loops))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for mat in original.materials:
        mesh.materials.append(mat)
    old_uv = original.uv_layers.active
    uv = mesh.uv_layers.new(name=old_uv.name) if old_uv else None
    old_color = original.color_attributes.active_color
    color = mesh.color_attributes.new(name=old_color.name, type=old_color.data_type, domain=old_color.domain) if old_color else None
    for face,(src,loops) in zip(mesh.polygons,mapped):
        face.material_index = src.material_index
        for new_i,old_i in zip(face.loop_indices,loops):
            if uv:
                u,v = old_uv.data[old_i].uv
                uv.data[new_i].uv = (u if arm==0 else .31-u, v)
            if color:
                color.data[new_i].color = old_color.data[old_i].color
    mesh.update()
    obj = bpy.data.objects.new(name,mesh)
    collection.objects.link(obj)
    obj.parent = root


def fold_level(level, original):
    dest = new_collection(level)
    name = ROOT if level=="LOD0" else f"{ROOT}_{level}"
    root = empty(name, dest)
    root["backlog_id"] = "MALL-STR-011"
    root["arm_m"] = 2.
    root["front"] = "Interior glTF +Z on the X arm and -X on the Z arm."
    for label,point in [("Left",(-2,0,0)),("Return",(0,-2,0))]:
        empty(f"CONNECTOR_{label}_{level}",dest,root).location=point
    for src in sorted(original.objects,key=lambda obj:obj.name):
        if src.type!="MESH":
            continue
        arm_mesh(src,0,dest,root,"West "+src.name)
        arm_mesh(src,1,dest,root,"Return "+src.name)


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def studio():
    scene=bpy.context.scene
    col=new_collection("STUDIO")
    floor=bpy.data.meshes.new("Studio plane")
    floor.from_pydata([(-110,-110,-.0005),(110,-110,-.0005),(110,110,-.0005),(-110,110,-.0005)],[],[(0,1,2,3)])
    mat=bpy.data.materials.new("Studio sandstone");mat.diffuse_color=(.45,.41,.34,1)
    floor.materials.append(mat);col.objects.link(bpy.data.objects.new("Studio floor",floor))
    for name,pos,power,size in [("Soft key",(-3.5,-4.5,6),530,3),("Fill",(3,-5,3.6),320,4),("Return",(-5,1.7,4.4),470,3)]:
        data=bpy.data.lights.new(name,"AREA");data.energy=power;data.shape="DISK";data.size=size
        light=bpy.data.objects.new(name,data);col.objects.link(light);light.location=pos;aim(light,(-.7,-.7,1.35))
    cam=bpy.data.objects.new("Studio camera",bpy.data.cameras.new("Studio camera"))
    col.objects.link(cam);cam.location=(-5.65,-6.4,4.75);aim(cam,(-.74,-.74,1.38))
    cam.data.type="ORTHO";cam.data.ortho_scale=4.5;scene.camera=cam
    scene.world=bpy.data.worlds.new("Studio world");scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.42,.45,.47,1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.47
    scene.render.engine="CYCLES";scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="JPEG";scene.render.image_settings.quality=91
    scene.view_settings.view_transform="AgX"


def visible(level):
    for value in LEVELS:
        for obj in bpy.data.collections[value].objects:
            obj.hide_render=value!=level
            obj.hide_set(value!=level)


def build(straight):
    source=straight/"sources"/f"{STRAIGHT}.blend"
    texture=straight/"sources"/"honed-limestone.png"
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    originals=[bpy.data.collections[level] for level in LEVELS]
    original_studio=bpy.data.collections["STUDIO"]
    for obj in list(original_studio.objects):
        bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(original_studio)
    bpy.context.scene.world=None
    for level,coll in zip(LEVELS,originals):
        coll.name="Template "+level
        for obj in coll.objects:
            if obj.type=="EMPTY":
                obj.name="Template "+obj.name
    for level,coll in zip(LEVELS,originals):
        fold_level(level,coll)
    for collection in originals:
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(collection)
    bpy.data.orphans_purge(do_recursive=True)
    image=bpy.data.images.get("honed-limestone.png")
    assert image and image.packed_file and bytes(image.packed_file.data)==texture.read_bytes()
    # The saved source carries the shared image and identifies its original file
    # by the relative repository location, regardless of the build checkout.
    image.filepath=f"//../../{STRAIGHT}/sources/honed-limestone.png"
    for packed in image.packed_files:
        packed.filepath=image.filepath
    studio()
    visible("LOD0")
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True,relative_remap=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--straight-dir",type=Path,default=BASE.parent/STRAIGHT)
    parser.add_argument("--rebuild",action="store_true")
    parser.add_argument("--export-source",action="store_true")
    parser.add_argument("--skip-render",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    for name in ("sources","exports","previews"):
        (BASE/name).mkdir(exist_ok=True)
    if args.export_source:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    elif SOURCE.exists() and not args.rebuild:
        raise ValueError("Use --export-source to preserve the saved source or --rebuild to replace it.")
    else:
        build(args.straight_dir)
    for level in LEVELS:
        visible(level)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in bpy.data.collections[level].objects:
            obj.select_set(True)
        suffix="" if level=="LOD0" else "-"+level.lower()
        bpy.ops.export_scene.gltf(filepath=str(BASE/"exports"/f"{SLUG}{suffix}.glb"),export_format="GLB",
            use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,
            export_cameras=False,export_lights=False)
    visible("LOD0")
    if not args.skip_render:
        bpy.context.scene.render.filepath=str(BASE/"previews"/f"{SLUG}.jpg")
        bpy.ops.render.render(write_still=True)

if __name__=="__main__":
    main()
