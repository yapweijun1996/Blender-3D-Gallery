"""Blender 5.1 entry point. Install with -- --gallery <library> --output <interiors>."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from mesh import CRAFT, PULSE, SCROLL
from rooms import DESIGNS, LIBRARY, build


def material(name, atlas):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = .63 if name == CRAFT else .48
    bsdf.inputs["Metallic"].default_value = .14 if name == CRAFT else .04
    if name == CRAFT:
        colour = mat.node_tree.nodes.new("ShaderNodeVertexColor")
        colour.layer_name = "Pigment"
    else:
        colour = mat.node_tree.nodes.new("ShaderNodeTexImage")
        colour.image = atlas
        mat.node_tree.links.new(colour.outputs["Color"],bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = .68 if name == SCROLL else .43
    mat.node_tree.links.new(colour.outputs["Color"],bsdf.inputs["Base Color"])
    return mat


def file_glb(path, target):
    # Keep the shared PNG external. glTF permits a BIN chunk plus URI-backed images.
    doc = json.loads(path.read_text())
    binary = bytearray((path.parent/doc["buffers"][0].pop("uri")).read_bytes())
    for node in doc["nodes"]:
        ext = node.get("extensions",{}).get("EXT_mesh_gpu_instancing")
        if not ext:
            continue
        # glTF instance attributes carry three package finishes in the same draw.
        count = doc["accessors"][ext["attributes"]["TRANSLATION"]]["count"]
        colors = ((1,.93,.80),(.62,.87,1),(.97,.65,.61))
        start = len(binary)
        for i in range(count):
            binary.extend(struct.pack("<3f",*colors[i%3]))
        view = len(doc["bufferViews"])
        doc["bufferViews"].append(dict(buffer=0,byteOffset=start,byteLength=count*12,byteStride=12,target=34962))
        ext["attributes"]["_COLOR_0"] = len(doc["accessors"])
        doc["accessors"].append(dict(bufferView=view,componentType=5126,count=count,type="VEC3"))
    for img in doc["images"]:
        generated = path.parent/img["uri"]
        if sha256(generated.read_bytes()).digest() != sha256((target.parent/"showroom-atlas.png").read_bytes()).digest():
            raise ValueError("Exporter changed the shared image")
        img["uri"] = "showroom-atlas.png"
    doc["buffers"][0]["byteLength"] = len(binary)
    data = json.dumps(doc,separators=(",",":")).encode()
    data += b" "*(-len(data)%4)
    binary.extend(b"\0"*(-len(binary)%4))
    header = struct.pack("<4sIIII",b"glTF",2,28+len(data)+len(binary),len(data),0x4e4f534a)
    target.write_bytes(header+data+struct.pack("<II",len(binary),0x004e4942)+binary)


def export(slot, gallery, output):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    room = build(slot,gallery/"models")
    atlas = bpy.data.images.load(str(output/"showroom-atlas.png"))
    finishes = {name:material(name,atlas) for name in room.batches}
    for name,batch in room.batches.items():
        batch.object(f"S{slot:02} {name}",finishes[name],name == CRAFT)
    for prototype, locations in room.instances:
        holder = bpy.data.objects.new("Shelf stock",None)
        bpy.context.collection.objects.link(holder)
        first = prototype.object("Package",finishes[CRAFT],True)
        for i,(x,y,z,s) in enumerate(locations):
            obj = first if i==0 else bpy.data.objects.new("Package",first.data)
            if i:
                bpy.context.collection.objects.link(obj)
            obj.parent = holder
            obj.location = (x,-z,y)
            obj.rotation_euler.z = (i%3-1)*.09
            obj.scale=(s,s,s*(.94+.07*(i%3)))
    name = f"s{slot:02}-{DESIGNS[slot-1].__name__.replace('_','-')}-details"
    with TemporaryDirectory() as temp:
        path = Path(temp)/(name+".gltf")
        bpy.ops.export_scene.gltf(filepath=str(path),export_format="GLTF_SEPARATE",export_yup=True,
            export_animations=False,export_cameras=False,export_lights=False,export_gpu_instances=True,
            export_image_format="AUTO",export_vertex_color="ACTIVE")
        file_glb(path,output/(name+".glb"))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    for slot in range(1,len(DESIGNS)+1):
        export(slot,args.gallery.resolve(),args.output.resolve())
