"""Build or export the original 2 m mall wall family with Blender 5.1.2."""
import argparse
from math import cos, pi, sin
from pathlib import Path
import random
import struct
import sys
import zlib

import bmesh
import bpy
from mathutils import Vector

BASE = Path(__file__).resolve().parent
SLUG = "mall-wall-module-2m"
SOURCE = BASE / "sources" / f"{SLUG}.blend"
LEVELS = ("LOD0", "LOD1", "LOD2")
ROOT = "ASSET_MallWall2m"
BACK, SUBSTRATE, FRONT = -.075, .062, .075
PLINTH, PANEL_LOW, PANEL_HIGH, CROWN = .12, .13, 2.724, 2.734
MID = 1.43


def linear(value):
    value /= 255
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def rgb(values):
    return tuple(linear(value) for value in values) + (1,)


def material(name, color, roughness, metal=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = rgb(color)
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    return mat


def packed_stone(mat):
    # A period of one is shared along both UV axes. All artwork is generated here.
    size = 512
    rng = random.Random(4528)
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)
        v = 2 * pi * y / size
        for x in range(size):
            u = 2 * pi * x / size
            bend = .37 * sin(u) + .15 * sin(2*u + v)
            grain = (1.5 * sin(3*v + bend) + 1.1 * cos(7*v + 2*bend)
                     + .8 * cos(25*v + 4*bend) + rng.uniform(-2.1, 2.1))
            if rng.random() < .016:
                grain -= rng.uniform(4, 13)
            pixels.extend(round(k + grain) for k in (213, 203, 178))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels, 9)) + chunk(b"IEND", b"")
    path = BASE / "sources" / "honed-limestone.png"
    path.write_bytes(png)
    image = bpy.data.images.load(str(path))
    image.pack()
    image.filepath = "//honed-limestone.png"
    for item in image.packed_files:
        item.filepath = image.filepath
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    mat.node_tree.links.new(node.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])


class Mesh:
    """Accumulate independent closed solids in glTF X/height/front coordinates."""
    def __init__(self):
        self.verts, self.faces, self.materials = [], [], []

    def rings(self, rings, sides, caps=(0, 0)):
        offset, count = len(self.verts), len(rings[0])
        for ring in rings:
            self.verts.extend(ring)
        self.faces.append(tuple(offset+i for i in reversed(range(count))))
        self.materials.append(caps[0])
        for row in range(len(rings)-1):
            start = offset + row*count
            for i in range(count):
                j = (i+1) % count
                self.faces.append((start+i, start+j, start+j+count, start+i+count))
                self.materials.append(sides[i])
        end = offset + (len(rings)-1)*count
        self.faces.append(tuple(end+i for i in range(count)))
        self.materials.append(caps[1])

    def profile(self, points, sides=None):
        self.rings([[(x, h, depth) for h, depth in points] for x in (-1, 1)], sides or [0]*len(points))

    def panel(self, x0, x1, h0, h1, detailed):
        if detailed:
            rings = []
            for inset, depth in [(0, SUBSTRATE), (0, .0705), (.0003, .0715), (.0014, .072)]:
                left, right, bottom, top = x0+inset, x1-inset, h0+inset, h1-inset
                cut = .001
                xy = [(left+cut,bottom),(right-cut,bottom),(right,bottom+cut),(right,top-cut),
                      (right-cut,top),(left+cut,top),(left,top-cut),(left,bottom+cut)]
                rings.append([(x,h,depth) for x,h in xy])
        else:
            rings = [[(x0,h0,d),(x1,h0,d),(x1,h1,d),(x0,h1,d)] for d in (SUBSTRATE,.072)]
        self.rings(rings,[0]*len(rings[0]))

    def create(self, name, coll, parent, materials, uv=False, colors=None):
        data = bpy.data.meshes.new(name)
        data.from_pydata([(x,-d,h) for x,h,d in self.verts], [], self.faces)
        for mat in materials:
            data.materials.append(mat)
        if not colors:
            for face, idx in zip(data.polygons,self.materials):
                face.material_index=idx
        if colors:
            col = data.color_attributes.new(name="Finish", type="FLOAT_COLOR", domain="CORNER")
            for face, idx in zip(data.polygons,self.materials):
                for loop in face.loop_indices:
                    col.data[loop].color = rgb(colors[idx])
        if uv:
            coord = data.uv_layers.new(name="Stone UV")
            for face in data.polygons:
                for index in face.loop_indices:
                    x, y, z = data.vertices[data.loops[index].vertex_index].co
                    # Scale normal to front panel faces. Edge UVs retain a finite area.
                    if abs(face.normal.x) > .7:
                        coord.data[index].uv = (-y/.85, z/.85)
                    elif abs(face.normal.z) > .7:
                        coord.data[index].uv = (x/.85, -y/.85)
                    else:
                        coord.data[index].uv = (x/.85+.27, z/.85+.13)
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(data)
        bm.free()
        obj = bpy.data.objects.new(name, data)
        coll.objects.link(obj)
        obj.parent = parent
        return obj


def collection(name):
    coll=bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


def empty(coll, name, parent=None):
    obj = bpy.data.objects.new(name,None)
    coll.objects.link(obj)
    obj.parent = parent
    obj.empty_display_size=.065
    return obj


def build_level(level, mats):
    coll = collection(level)
    root = empty(coll,ROOT if level == "LOD0" else f"{ROOT}_{level}")
    root["backlog_id"] = "MALL-STR-010"
    root["pitch_m"] = 2.
    root["front"] = "glTF +Z. Ground-centre pivot in metres."
    for side, x in [("Left",-1),("Right",1)]:
        node=empty(coll,f"CONNECTOR_{side}_{level}",root)
        node.location.x=x
    if level == "LOD2":
        # A single closed silhouette with front finish colours retained in one primitive.
        shape=[(0,BACK),(2.8,BACK),(2.8,FRONT),(CROWN,FRONT),
               (CROWN-.006,SUBSTRATE),(PANEL_HIGH,.072),(PANEL_LOW,.072),
               (PLINTH,SUBSTRATE),(.114,FRONT),(.108,FRONT),(.012,FRONT),(0,.069)]
        body=Mesh()
        body.profile(shape,[0,0,2,0,0,1,0,0,3,2,2,0])
        body.create("Distant finish bands",coll,root,[mats["vertex"]],
                    colors=[(166,158,142),(213,203,178),(72,64,54),(169,137,87)])
        return
    core=Mesh()
    core.profile([(0,BACK),(2.8,BACK),(2.8,SUBSTRATE),(0,SUBSTRATE)])
    core.create(f"Continuous backing {level}",coll,root,[mats["backing"]])
    trim=Mesh()
    plinth=[(0,SUBSTRATE),(PLINTH,SUBSTRATE),(PLINTH,.070),(.115,FRONT),(.109,FRONT),
            (.108,.074),(.106,.074),(.105,FRONT),(.012,FRONT),(.009,.069),(0,.069)]
    crown=[(CROWN,SUBSTRATE),(2.8,SUBSTRATE),(2.8,FRONT),(CROWN+.009,FRONT),(CROWN,.069)]
    if level == "LOD1":
        plinth=[(0,SUBSTRATE),(PLINTH,SUBSTRATE),(PLINTH,FRONT),(.108,FRONT),(0,FRONT)]
    trim.profile(plinth, [0,0,0,1,0,0,0,0,0,0,0] if level == "LOD0" else [0,0,1,0,0])
    if level == "LOD0":
        trim.create("Folded bronze plinth and brass lip",coll,root,[mats["bronze"],mats["brass"]])
        trim=Mesh()
    trim.profile(crown)
    trim.create(f"Bronze trims {level}",coll,root,[mats["bronze"],mats["brass"]])
    panels=Mesh()
    for row,(h0,h1) in enumerate([(PANEL_LOW,MID-.002),(MID+.002,PANEL_HIGH)],1):
        for column in range(4):
            left=-1+.5*column
            panels.panel(left+.002,left+.498,h0,h1,level=="LOD0")
            if level == "LOD0":
                panels.create(f"Honed limestone {row}-{column+1}",coll,root,[mats["stone"]],uv=True)
                panels=Mesh()
    if level == "LOD1":
        panels.create("Eight limestone panels LOD1",coll,root,[mats["midstone"]])


def point_at(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def studio():
    coll=collection("STUDIO")
    scene=bpy.context.scene
    floor=Mesh()
    floor.verts=[(-200,-.0005,-200),(200,-.0005,-200),(200,-.0005,200),(-200,-.0005,200)]
    floor.faces=[(3,2,1,0)]; floor.materials=[0]
    floor.create("Studio floor",coll,None,[material("Studio floor",(184,179,170),.85)])
    for name,position,power,size in [("Warm key",(-3.5,-4.2,5.5),380,3.0),
                                     ("Fill",(3.8,-3.3,2.7),165,3.0),("Shoulder",(2,3,4.8),540,2.8)]:
        data=bpy.data.lights.new(name,"AREA"); data.energy=power; data.shape="DISK"; data.size=size
        obj=bpy.data.objects.new(name,data);coll.objects.link(obj);obj.location=position
        point_at(obj,(0,0,1.4))
    camera=bpy.data.objects.new("Studio camera",bpy.data.cameras.new("Studio camera"))
    coll.objects.link(camera);scene.camera=camera;camera.location=(3.1,-7.2,3.65)
    point_at(camera,(0,0,1.38));camera.data.type="ORTHO";camera.data.ortho_scale=3.6
    scene.world=bpy.data.worlds.new("Studio world");scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.41,.44,.46,1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.42
    scene.render.engine="CYCLES";scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="JPEG";scene.render.image_settings.quality=91
    scene.view_settings.view_transform="AgX"


def visibility(active):
    for level in LEVELS:
        for obj in bpy.data.collections[level].objects:
            obj.hide_set(level != active)
            obj.hide_render=level != active


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system="METRIC"
    mats={
        "backing":material("Warm mortar substrate",(166,158,142),.82),
        "stone":material("Honed honey limestone",(213,203,178),.74),
        "midstone":material("Limestone average",(213,203,178),.74),
        "bronze":material("Dark satin bronze",(72,64,54),.42,.52),
        "brass":material("Brushed champagne lip",(169,137,87),.33,.68),
        "vertex":material("Distant grouped finishes",(255,255,255),.65)
    }
    packed_stone(mats["stone"])
    color=mats["vertex"].node_tree.nodes.new("ShaderNodeVertexColor");color.layer_name="Finish"
    mats["vertex"].node_tree.links.new(color.outputs["Color"],mats["vertex"].node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    for level in LEVELS:
        build_level(level,mats)
    studio()
    visibility("LOD0")
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True,relative_remap=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--rebuild",action="store_true")
    parser.add_argument("--export-source",action="store_true")
    parser.add_argument("--skip-render",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    for path in ("sources","exports","previews"):
        (BASE/path).mkdir(exist_ok=True)
    if args.export_source:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    elif SOURCE.exists() and not args.rebuild:
        raise ValueError("Existing editable source. Use --export-source to preserve it or --rebuild to replace it.")
    else:
        build()
    for level in LEVELS:
        visibility(level)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in bpy.data.collections[level].objects:
            obj.select_set(True)
        suffix="" if level=="LOD0" else "-"+level.lower()
        bpy.ops.export_scene.gltf(filepath=str(BASE/"exports"/f"{SLUG}{suffix}.glb"),export_format="GLB",
                                  use_selection=True, export_apply=True, export_yup=True, export_animations=False,
                                  export_extras=True, export_cameras=False, export_lights=False)
    visibility("LOD0")
    if not args.skip_render:
        bpy.context.scene.render.filepath=str(BASE/"previews"/f"{SLUG}.jpg")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
