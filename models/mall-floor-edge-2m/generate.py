"""Build and export the straight and mitred 100 mm mall edge from a common section."""
import argparse
from math import cos, pi, sin
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

BASE=Path(__file__).resolve().parent
SLUG="mall-floor-edge-2m"
SOURCE=BASE/"sources"/(SLUG+".blend")
ROOT="ASSET_MallFloorEdge2m"
# Each point is radial distance from the tile, height below the floor, and
# finish of the surface extending to the next point (0 champagne, 1 bronze).
LEVELS=("LOD0","LOD1","LOD2")
# All detail levels retain the same complete perimeter at each join.
SECTION=[(0,0,0),(.044,0,1),(.0455,0,0),(.060,0,0),(.060,-.005,0),
         (.0585,-.0065,0),(.0585,-.010,1),(.0595,-.011,1),(.0595,-.023,1),
         (.0575,-.025,1),(.0575,-.077,1),(.0545,-.080,1),(.0545,-.089,1),
         (.057,-.0915,1),(.057,-.098,1),(.055,-.100,1),(0,-.100,1)]
PALETTE=((173,152,114),(76,72,63))


def linear(v):
    v/=255
    return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4


def rgba(color):
    return tuple(linear(v) for v in color)+(1,)


def mat(name,color,roughness,metal):
    result=bpy.data.materials.new(name)
    result.use_nodes=True
    result.diffuse_color=rgba(color)
    bsdf=result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=result.diffuse_color
    bsdf.inputs["Roughness"].default_value=roughness
    bsdf.inputs["Metallic"].default_value=metal
    return result


def new_collection(name):
    col=bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def empty(name,col,parent=None):
    obj=bpy.data.objects.new(name,None)
    col.objects.link(obj);obj.parent=parent;obj.empty_display_size=.04
    return obj


def profile_mesh(name,level,arm,col,parent,materials):
    section=SECTION;n=len(section)
    verts=[]
    for end in (False,True):
        for r,h,_ in section:
            if arm=="Straight":
                x,z=(1 if end else -1), r-.03
            else:
                # Both pieces end on the exact x=z diagonal. Omitting their
                # internal end caps gives a filled manifold section in assembly.
                x,z=(1+r if end else -1), 1+r
                if arm=="Right":
                    x,z=z,x
            verts.append((x,-z,h))
    faces=[tuple(range(n))];finishes=[1]
    for i,(_,_,finish) in enumerate(section):
        j=(i+1)%n
        faces.append((i,j,j+n,i+n))
        finishes.append(finish)
    if arm=="Straight":
        faces.append(tuple(range(n,2*n)));finishes.append(1)
    # Establish the orientation from the actual Blender axis conversion. The
    # straight and front strip run toward +X; swapping X/Z reverses winding.
    if arm!="Right":
        faces[0]=tuple(reversed(faces[0]))
    else:
        faces[1:]=[tuple(reversed(f)) for f in faces[1:]]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces)
    if level=="LOD2":
        mesh.materials.append(materials["distant"])
        color=mesh.color_attributes.new(name="Metal finishes",type="FLOAT_COLOR",domain="CORNER")
        for poly,finish in zip(mesh.polygons,finishes):
            for i in poly.loop_indices: color.data[i].color=rgba(PALETTE[finish])
    else:
        for key in ("cap","fascia"):mesh.materials.append(materials[key])
        for poly,finish in zip(mesh.polygons,finishes):poly.material_index=finish
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    # Open arms have no signed-volume guarantee from Blender's orientation
    # heuristic. The top faces provide an exact local outward reference.
    top=[f for f in bm.faces if all(abs(v.co.z)<1e-8 for v in f.verts)]
    if top[0].normal.z<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh)
    col.objects.link(obj);obj.parent=parent
    return obj


def fasteners(arm,level,col,parent,material):
    if level=="LOD2":
        return
    sides=12 if level=="LOD0" else 6
    # Radius, distance from the tile edge, hexagonal socket boundary.
    rings=[(.004,.0575,False),(.004,.05785,False),(.00345,.0585,False)]
    if level=="LOD0":
        rings.extend([(.00155,.0585,True),(.00155,.05782,True)])
    vertices=[]; faces=[]
    for station in (-.58,.58):
        first=len(vertices)
        for radius,depth,hexagon in rings:
            for i in range(sides):
                angle=2*pi*i/sides
                rad=radius*(cos(pi/6) if hexagon and i%2 else 1)
                x=station+rad*cos(angle)
                z=depth+(-.03 if arm=="Straight" else 1)
                if arm=="Right":x,z=z,x
                vertices.append((x,-z,-.052+rad*sin(angle)))
        faces.append(tuple(first+i for i in reversed(range(sides))))
        for ring in range(len(rings)-1):
            start=first+ring*sides
            for i in range(sides):
                j=(i+1)%sides
                faces.append((start+i,start+j,start+j+sides,start+i+sides))
        faces.append(tuple(first+(len(rings)-1)*sides+i for i in range(sides)))
    name=arm+" fascia buttons "+level
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.materials.append(material)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);col.objects.link(obj);obj.parent=parent


def collection_name(form,level):
    return form+" "+level


def build_form(form,level,materials):
    col=new_collection(collection_name(form,level))
    rootname=ROOT+("Mitre" if form=="Mitre" else "")+("" if level=="LOD0" else "_"+level)
    parent=empty(rootname,col)
    parent["kit"]="Full-depth 2 m mall floor edge"
    parent["form"]=form
    parent["width_m"]=.06
    parent["depth_m"]=.1
    if form=="Straight":
        profile_mesh("Straight full-depth section "+level,level,"Straight",col,parent,materials)
        fasteners("Straight",level,col,parent,materials["buttons"])
        sockets=[("West",(-1,0,0)),("East",(1,0,0))]
    else:
        for arm in ("Front","Right"):
            profile_mesh(arm+" mitred section "+level,level,arm,col,parent,materials)
            fasteners(arm,level,col,parent,materials["buttons"])
        sockets=[("West",(-1,-1.03,0)),("South",(1.03,1,0))]
    for label,position in sockets:
        empty(f"CONNECTOR_{form}_{label}_{level}",col,parent).location=position


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def studio():
    scene=bpy.context.scene;col=new_collection("STUDIO")
    floor=bpy.data.meshes.new("Studio floor")
    floor.from_pydata([(-40,-40,-.1003),(40,-40,-.1003),(40,40,-.1003),(-40,40,-.1003)],[],[(0,1,2,3)])
    floor.materials.append(mat("Studio stone backdrop",(145,138,124),.85,0))
    col.objects.link(bpy.data.objects.new("Studio ground",floor))
    for name,pos,power,size in [("Key",(-2.8,-3.5,4.0),380,3.0),("Fascia fill",(2.7,-3,1.45),210,2.2),("Rim",(-1,3.3,3.5),520,2.5)]:
        ld=bpy.data.lights.new(name,"AREA");ld.energy=power;ld.shape="DISK";ld.size=size
        light=bpy.data.objects.new(name,ld);col.objects.link(light);light.location=pos;aim(light,(0,0,0))
    cam=bpy.data.objects.new("Studio camera",bpy.data.cameras.new("Studio camera"))
    col.objects.link(cam);cam.data.type="ORTHO";scene.camera=cam
    scene.world=bpy.data.worlds.new("Studio world");scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes["Background"];bg.inputs["Color"].default_value=(.52,.55,.59,1);bg.inputs["Strength"].default_value=.5
    scene.render.engine="CYCLES";scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=760;scene.render.resolution_y=480;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="JPEG";scene.render.image_settings.quality=93;scene.view_settings.view_transform="AgX"


def show(form,level):
    for item in ("Straight","Mitre"):
        for quality in LEVELS:
            for o in bpy.data.collections[collection_name(item,quality)].objects:
                hide=(item,quality)!=(form,level)
                o.hide_set(hide);o.hide_render=hide


def camera(form):
    cam=bpy.context.scene.camera
    if form=="Straight":
        cam.location=(2.4,-3.8,2.15);aim(cam,(0,0,-.047));cam.data.ortho_scale=2.1
    else:
        cam.location=(3.2,-3.5,3.1);aim(cam,(.16,-.16,-.045));cam.data.ortho_scale=3.15


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system="METRIC"
    materials={"cap":mat("Satin champagne nosing",PALETTE[0],.32,.68),
               "fascia":mat("Anodized bronze fascia",PALETTE[1],.46,.47),
               "buttons":mat("Bronze button fasteners",(113,103,83),.36,.6),
               "distant":mat("Distant metal finishes",(255,255,255),.41,.52)}
    node=materials["distant"].node_tree.nodes.new("ShaderNodeVertexColor")
    node.layer_name="Metal finishes"
    bsdf=materials["distant"].node_tree.nodes["Principled BSDF"]
    materials["distant"].node_tree.links.new(node.outputs["Color"],bsdf.inputs["Base Color"])
    for form in ("Straight","Mitre"):
        for level in LEVELS:build_form(form,level,materials)
    studio();show("Straight","LOD0");camera("Straight")
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True,relative_remap=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--export-source",action="store_true")
    parser.add_argument("--rebuild",action="store_true")
    parser.add_argument("--skip-render",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    for folder in ("sources","exports","previews"):(BASE/folder).mkdir(exist_ok=True)
    if args.export_source:bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    elif SOURCE.exists() and not args.rebuild:raise ValueError("Use --export-source to preserve edits or --rebuild to replace the source.")
    else:build()
    for form in ("Straight","Mitre"):
        suffix="" if form=="Straight" else "-mitre"
        for level in LEVELS:
            show(form,level)
            bpy.ops.object.select_all(action="DESELECT")
            for obj in bpy.data.collections[collection_name(form,level)].objects:obj.select_set(True)
            name=SLUG+suffix+("" if level=="LOD0" else "-"+level.lower())
            bpy.ops.export_scene.gltf(filepath=str(BASE/"exports"/(name+".glb")),export_format="GLB",use_selection=True,
                export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_cameras=False,export_lights=False)
        if not args.skip_render:
            show(form,"LOD0");camera(form)
            bpy.context.scene.render.filepath=str(BASE/"previews"/(SLUG+suffix+".jpg"))
            bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    main()
