"""Create the original stepped 400 mm fascia for the 2 m mall shop opening."""
import argparse
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
SLUG="mall-shop-door-header-2m"
ROOT="ASSET_MallShopDoorHeader2m"
SOURCE=HERE/"sources"/(SLUG+".blend")
LEVELS=("LOD0","LOD1","LOD2")
COLORS={"back":(166,158,142),"stone":(213,203,178),"bronze":(72,64,54),"accent":(169,137,87)}


def rgba(c):
    def linear(n):
        v=n/255
        return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    return tuple(linear(n) for n in c)+(1,)


def material(name,color,roughness,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=rgba(color)
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=m.diffuse_color
    bsdf.inputs["Roughness"].default_value=roughness;bsdf.inputs["Metallic"].default_value=metal
    return m


def collection(name):
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
    return c


def empty(name,col,parent=None):
    o=bpy.data.objects.new(name,None);col.objects.link(o);o.parent=parent;o.empty_display_size=.07
    return o


class Geometry:
    def __init__(self):
        self.verts=[];self.faces=[];self.finishes=[]

    def rings(self,rings,faces_between,base,top):
        first=len(self.verts);count=len(rings[0])
        for ring in rings:self.verts.extend(ring)
        self.faces.append(tuple(first+i for i in reversed(range(count))));self.finishes.append(base)
        for row,finishes in enumerate(faces_between):
            start=first+row*count
            for i,finish in enumerate(finishes):
                j=(i+1)%count
                self.faces.append((start+i,start+j,start+j+count,start+i+count))
                self.finishes.append(finish)
        end=first+count*(len(rings)-1)
        self.faces.append(tuple(end+i for i in range(count)));self.finishes.append(top)

    def backing(self,level):
        # The eight-corner footprint forms a single physical stepped solid. No
        # hidden rectangular cap cuts through the two faces of the step.
        rows=[(0,.195,"bronze"),(.010,.195,"bronze"),(.012,.190,"bronze"),(.015,.190,"accent"),
              (.017,.190,"bronze"),(.019,.187,"back"),(.324,.187,"back"),(.334,.187,"bronze"),
              (.340,.195,"bronze"),(.400,.195,None)]
        if level=="LOD2":
            # The distant silhouette needs the stepped plan and major finish
            # bands. Fine recesses and individual joints disappear at distance.
            rows=[(0,.195,"bronze"),(.023,.195,"accent"),(.025,.194,"stone"),
                  (.324,.194,"back"),(.334,.195,"bronze"),(.400,.195,None)]
        rings=[];sides=[]
        for y,d,finish in rows:
            plan=[(-1,-.075),(1,-.075),(1,.075),(1.05,.075),(1.05,d),(-1.05,d),(-1.05,.075),(-1,.075)]
            rings.append([(x,y,z) for x,z in plan])
            if finish:
                side=finish if finish in ("bronze","accent") else "back"
                sides.append(["back","back",side,side,finish,side,side,"back"])
        self.rings(rings,sides,"bronze","back")

    def panel(self,left,right,detailed):
        rings=[]
        edge=[(0,.187),(0,.1925),(.00035,.1936),(.00125,.194)] if detailed else [(0,.187),(0,.194)]
        for inset,d in edge:
            l,r=left+inset,right-inset;b,t=.025+inset,.324-inset
            pts=[(l,b),(r,b),(r,t),(l,t)]
            if detailed:
                c=.0008
                pts=[(l+c,b),(r-c,b),(r,b+c),(r,t-c),(r-c,t),(l+c,t),(l,t-c),(l,b+c)]
            rings.append([(x,y,d) for x,y in pts])
        self.rings(rings,[["stone"]*len(rings[0]) for _ in rings[1:]],"stone","stone")

    def create(self,name,col,parent,mats,vertex=False,uv=False):
        data=bpy.data.meshes.new(name);data.from_pydata([(x,-z,y) for x,y,z in self.verts],[],self.faces)
        if vertex:
            data.materials.append(mats["vertex"])
            attr=data.color_attributes.new(name="Fascia finishes",type="FLOAT_COLOR",domain="CORNER")
            for p,k in zip(data.polygons,self.finishes):
                for i in p.loop_indices:attr.data[i].color=rgba(COLORS[k])
        else:
            names=list(dict.fromkeys(self.finishes))
            for key in names:data.materials.append(mats[key])
            for p,k in zip(data.polygons,self.finishes):p.material_index=names.index(k)
        if uv:
            layer=data.uv_layers.new(name="Limestone grain")
            for f in data.polygons:
                for i in f.loop_indices:
                    x,n,y=data.vertices[data.loops[i].vertex_index].co
                    if abs(f.normal.x)>.7:coord=(-n/.85,y/.85)
                    elif abs(f.normal.z)>.7:coord=(x/.85,-n/.85)
                    else:coord=(x/.85+.27,(y+2.4)/.85+.13)
                    layer.data[i].uv=coord
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(data);bm.free()
        obj=bpy.data.objects.new(name,data);col.objects.link(obj);obj.parent=parent


def build_level(level,mats):
    col=collection(level)
    root=empty(ROOT if level=="LOD0" else ROOT+"_"+level,col)
    root["opening_m"]=2.;root["height_m"]=.4;root["front"]="glTF +Z"
    for label,position in [("West",(-1,0,0)),("East",(1,0,0)),("DoorTop",(0,-.135,0))]:
        empty("CONNECTOR_"+label+"_"+level,col,root).location=position
    shell=Geometry();shell.backing(level)
    shell.create("Stepped lintel and bronze returns "+level,col,root,mats,vertex=level=="LOD2")
    if level=="LOD2":return
    panels=Geometry()
    ends=[-1.05,-.50,0,.50,1.05]
    for i,(left,right) in enumerate(zip(ends,ends[1:]),1):
        panels.panel(left+.002,right-.002,level=="LOD0")
        if level=="LOD0":
            panels.create("Limestone fascia panel "+str(i),col,root,mats,uv=True)
            panels=Geometry()
    if level=="LOD1":
        panels.create("Four fascia faces "+level,col,root,{**mats,"stone":mats["midstone"]})


def aim(o,p):
    o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()


def studio():
    col=collection("STUDIO");sc=bpy.context.scene
    g=bpy.data.meshes.new("Studio surface");g.from_pydata([(-40,-40,-.0003),(40,-40,-.0003),(40,40,-.0003),(-40,40,-.0003)],[],[(0,1,2,3)])
    g.materials.append(material("Studio backdrop",(166,161,149),.9))
    col.objects.link(bpy.data.objects.new("Studio floor",g))
    for name,pos,power,size in [("Key",(-1.5,-3.5,3.7),320,2.8),("Fill",(2.8,-3,1.5),120,2.2),("Rear",(-1,3,4),440,3)]:
        light=bpy.data.lights.new(name,"AREA");light.energy=power;light.shape="DISK";light.size=size
        o=bpy.data.objects.new(name,light);col.objects.link(o);o.location=pos;aim(o,(0,0,.2))
    cam=bpy.data.objects.new("Studio camera",bpy.data.cameras.new("Studio camera"));col.objects.link(cam)
    cam.location=(2,-4.9,1.75);aim(cam,(0,-.05,.19));cam.data.type="ORTHO";cam.data.ortho_scale=2.45;sc.camera=cam
    sc.world=bpy.data.worlds.new("Studio world");sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes["Background"];bg.inputs["Color"].default_value=(.45,.47,.49,1);bg.inputs["Strength"].default_value=.5
    sc.render.engine="CYCLES";sc.cycles.samples=24;sc.cycles.use_denoising=True
    sc.render.resolution_x=760;sc.render.resolution_y=480;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="JPEG";sc.render.image_settings.quality=92;sc.view_settings.view_transform="AgX"


def show(level):
    for label in LEVELS:
        for o in bpy.data.collections[label].objects:
            o.hide_set(label!=level);o.hide_render=label!=level


def build(texture):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system="METRIC"
    mats={"back":material("Warm mortar substrate",COLORS["back"],.82),"stone":material("Honed honey limestone",COLORS["stone"],.74),
          "midstone":material("Limestone average",COLORS["stone"],.74),"bronze":material("Dark satin bronze",COLORS["bronze"],.42,.52),
          "accent":material("Brushed champagne lip",COLORS["accent"],.33,.68),"vertex":material("Grouped fascia finishes",(255,255,255),.64)}
    image=bpy.data.images.load(str(texture.resolve()));image.pack()
    image.filepath="//../../mall-wall-module-2m/sources/honed-limestone.png"
    for packed in image.packed_files:packed.filepath=image.filepath
    nt=mats["stone"].node_tree;tx=nt.nodes.new("ShaderNodeTexImage");tx.image=image
    nt.links.new(tx.outputs["Color"],nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt=mats["vertex"].node_tree;attr=nt.nodes.new("ShaderNodeVertexColor");attr.layer_name="Fascia finishes"
    nt.links.new(attr.outputs["Color"],nt.nodes["Principled BSDF"].inputs["Base Color"])
    for level in LEVELS:build_level(level,mats)
    studio();show("LOD0")
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True,relative_remap=False)


def main():
    p=argparse.ArgumentParser();p.add_argument("--texture",type=Path,default=HERE.parent/"mall-wall-module-2m"/"sources"/"honed-limestone.png")
    p.add_argument("--export-source",action="store_true");p.add_argument("--rebuild",action="store_true");p.add_argument("--skip-render",action="store_true")
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    for folder in ("sources","exports","previews"):(HERE/folder).mkdir(exist_ok=True)
    if a.export_source:bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    elif SOURCE.exists() and not a.rebuild:raise ValueError("Use --export-source for a saved edit or --rebuild to replace the source.")
    else:build(a.texture)
    for level in LEVELS:
        show(level);bpy.ops.object.select_all(action="DESELECT")
        for o in bpy.data.collections[level].objects:o.select_set(True)
        suffix="" if level=="LOD0" else "-"+level.lower()
        bpy.ops.export_scene.gltf(filepath=str(HERE/"exports"/(SLUG+suffix+".glb")),export_format="GLB",use_selection=True,
            export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_cameras=False,export_lights=False)
    show("LOD0")
    if not a.skip_render:
        bpy.context.scene.render.filepath=str(HERE/"previews"/(SLUG+".jpg"));bpy.ops.render.render(write_still=True)

if __name__=="__main__":main()
