"""Build the original cosmetics fixture, or export the editable saved Blender scene."""
import argparse
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = "mall-cosmetics-tester-bar"
SOURCE = HERE / "sources" / (SLUG + ".blend")
LEVELS = ("LOD0", "LOD1", "LOD2")
LIP = ("833D50", "AD5164", "C57275", "CE877C")
FOUNDATION = ("98634E", "BA8767", "D4A784", "E2C2A4")


def linear(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels) + (1,)


def material(name, color, metal, roughness, vertex=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = linear(color)
    mat.use_nodes = True
    tree = mat.node_tree
    pbr = tree.nodes.get("Principled BSDF")
    pbr.inputs["Base Color"].default_value = mat.diffuse_color
    pbr.inputs["Metallic"].default_value = metal
    pbr.inputs["Roughness"].default_value = roughness
    if vertex:
        tint = tree.nodes.new("ShaderNodeVertexColor")
        tint.layer_name = "Finish"
        tree.links.new(tint.outputs["Color"], pbr.inputs["Base Color"])
    return mat


def rounded(w, d, r, segments):
    points = []
    for cx, cy, a in [(w/2-r, d/2-r, 0), (-w/2+r, d/2-r, 90),
                      (-w/2+r, -d/2+r, 180), (w/2-r, -d/2+r, 270)]:
        for i in range(segments + 1):
            angle = math.radians(a + 90 * i / segments)
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


def circle(radius, count):
    return [(radius*math.cos(i*math.tau/count), radius*math.sin(i*math.tau/count)) for i in range(count)]


class Part:
    """Build named closed solids in glTF metres. Each ring is a physical cross section."""
    def __init__(self, name):
        self.name = name
        self.verts, self.faces, self.finishes = [], [], []

    def face(self, indices, finish, shade=None, smooth=False):
        self.faces.append(indices)
        self.finishes.append((finish, shade, smooth))

    def rings(self, loops, materials, colors=None, smooth=False):
        start = len(self.verts)
        n = len(loops[0])
        for loop in loops:
            assert len(loop) == n
            self.verts.extend(loop)
        self.face(tuple(reversed(range(start, start+n))), materials[0], colors[0] if colors else None)
        for k in range(len(loops)-1):
            lo = start + k*n
            for j in range(n):
                a, b = lo + j, lo + (j+1)%n
                self.face((a,b,b+n,a+n), materials[k], colors[k] if colors else None, smooth)
        last = start + (len(loops)-1)*n
        self.face(tuple(range(last,last+n)), materials[-1], colors[-1] if colors else None)

    def slab(self, x, z, stages, mats):
        loops = [[(x+u,h,z+v) for u,v in rounded(w,d,r,ARC)] for h,w,d,r in stages]
        self.rings(loops, mats)

    def lathe(self, x, z, profile, mats, shades=None, slope=0):
        loops = []
        for i,(h,r) in enumerate(profile):
            ring = circle(r, ROUND)
            loops.append([(x+u,h+(slope*u if i >= len(profile)-2 else 0),z+v) for u,v in ring])
        self.rings(loops,mats,shades,smooth=True)

    def emit(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata([(x,-z,y) for x,y,z in self.verts], [], self.faces)
        unique = list(dict.fromkeys(m for m,c,s in self.finishes))
        for m in unique:
            mesh.materials.append(MATS[m])
        use_color = any(color is not None for _,color,_ in self.finishes)
        if use_color:
            layer = mesh.color_attributes.new(name="Finish",type="FLOAT_COLOR",domain="CORNER")
        for poly,(m,color,smooth) in zip(mesh.polygons,self.finishes):
            poly.material_index = unique.index(m)
            poly.use_smooth = smooth
            if use_color:
                for loop_id in poly.loop_indices:
                    layer.data[loop_id].color = linear(color or "FFFFFF")
        bm=bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        if any(s for _,_,s in self.finishes):
            mesh.set_sharp_from_angle(angle=math.radians(35))
        obj = bpy.data.objects.new(self.name + "_" + LEVEL,mesh)
        COLLECTION.objects.link(obj)
        obj.parent = ROOT
        return obj


def slab(name,x,z,stages,mats):
    part = Part(name)
    part.slab(x,z,stages,mats)
    return part.emit()


def cabinet(lod):
    slab("Grounded_plinth",0,-.065,[(0,.78,.47,.085),(.055,.78,.47,.085),(.075,.82,.51,.095)],
         ["charcoal","metal","metal"])
    slab("Reeded_cabinet_carcass",0,-.065,[(.075,.86,.54,.092),(.09,.88,.56,.10),(.795,.88,.56,.10),(.811,.86,.54,.092)],
         ["enamel","enamel","enamel","enamel"])
    slab("Champagne_apron",0,0,[(.811,.951,.751,.11),(.823,.966,.766,.115),(.828,.966,.766,.115)],
         ["metal","metal","metal"])
    slab("Ivory_solid_surface",0,0,[(.828,.978,.778,.115),(.838,1,.80,.12),(.862,1,.80,.12),(.867,.990,.790,.116)],
         ["ivory"]*4)
    # The applied tambour doors meet the flat part of the carcass at z=.215.
    for sign, label in [(-1,"Left"),(1,"Right")]:
        cx=sign*.165
        w=.322
        front=[]
        count=14 if lod==0 else 7 if lod==1 else 1
        steps=count*(6 if lod==0 else 3 if lod==1 else 1)
        for i in range(steps+1):
            x=-w/2+w*i/steps
            flute=(1-math.cos(i*math.tau*count/steps))/2
            front.append((cx+x,.221+(.007*flute if lod!=2 else 0)))
        shape=[(cx-w/2,.215),(cx+w/2,.215)]+list(reversed(front))
        panel=Part(label+"_tambour_front")
        panel.rings([[(x,h,z) for x,z in shape] for h in (.108,.769)], ["enamel","enamel"])
        panel.emit()
        if lod<2:
            slab(label+"_finger_pull",cx-sign*.048,.226,
                 [(.735,.092,.022,.007),(.741,.105,.028,.01),(.751,.105,.028,.01)],["metal"]*3)


def mirror(lod):
    # Two rear posts touch the flat back of the medallion. The exposed base is fixed to the deck.
    posts=Part("Mirror_pedestal_feet_and_stems")
    for x in (-.171,.171):
        posts.slab(x,-.328,[(.867,.072,.067,.019),(.879,.072,.067,.019),(.886,.060,.055,.015)],["metal"]*3)
        posts.slab(x,-.329,[(.886,.031,.032,.007),(1.075,.031,.032,.007)],["metal"]*2)
    posts.emit()
    # Section runs forward from the rear shell, around the bezel, then back into the glass seat.
    frame=Part("Mirror_champagne_bezel")
    sections=[(-.313,.628,.515,.246),(-.308,.646,.53,.253),(-.282,.646,.53,.253),
              (-.276,.637,.521,.251),(-.276,.608,.492,.237),(-.281,.599,.483,.232),(-.283,.599,.483,.232)]
    if lod==2:
        sections=[sections[i] for i in (0,2,3,5,6)]
    loops=[[(u,1.235+v,z) for u,v in rounded(w,h,r,(13,6,5)[lod])] for z,w,h,r in sections]
    frame.rings(loops,["metal"]*(len(loops)-2)+["gasket","gasket"],smooth=True)
    frame.emit()
    glass=Part("Mirror_inset_silver_face")
    loops=[[(u,1.235+v,z) for u,v in rounded(w,h,r,(13,6,5)[lod])] for z,w,h,r in
           [(-.283,.5986,.4826,.2318),(-.2817,.5986,.4826,.2318),(-.2805,.596,.480,.2305)]]
    glass.rings(loops,["silver"]*3,smooth=True)
    glass.emit()


def subtract_wells(tray, wells):
    # One boolean operand per pocket. Its flat bottom leaves a real 4 mm tray floor.
    for x,z,r in wells:
        cutter=Part("Temporary_socket_tool")
        cutter.lathe(x,z,[(.876,r),(.914,r)],["tray"]*2)
        tool=cutter.emit()
        mod=tray.modifiers.new("Machine blind pocket","BOOLEAN")
        mod.operation="DIFFERENCE"
        mod.solver="EXACT"
        mod.object=tool
        bpy.context.view_layer.objects.active=tray
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(tool,do_unlink=True)
    for poly in tray.data.polygons:
        poly.use_smooth=False


def tester_station(lod, sign, label, shades):
    cx=sign*.224
    tray_z=.083
    slab(label+"_champagne_tray_edge",cx,tray_z,
         [(.867,.393,.288,.033),(.871,.404,.299,.036),(.873,.404,.299,.036)],["metal"]*3)
    tray=slab(label+"_socket_tray",cx,tray_z,
              [(.873,.400,.295,.035),(.890,.400,.295,.035),(.893,.394,.289,.032)],["tray"]*3)
    pan_x=[cx+d for d in (-.144,-.048,.048,.144)]
    test_x=[cx+d for d in (-.119,0,.119)]
    product_radius=.022 if sign<0 else .0325
    if lod<2:
        subtract_wells(tray,[(x,.154,.036) for x in pan_x]+[(x,.018,product_radius+.0018) for x in test_x])
    # Each cup has a true inner seat. The separate powder or cream solid touches the cup bottom.
    collars=Part(label+"_four_swatch_cups")
    pigments=Part(label+"_four_pressed_swatches")
    for x,shade in zip(pan_x,shades):
        if lod<2:
            collars.lathe(x,.154,[(.876,.0353),(.889,.0353),(.891,.0345),(.891,.0309),(.886,.0301)],["metal"]*5)
            pigments.lathe(x,.154,[(.886,.0300),(.8888,.0300),(.8896,.0288)],["pigment"]*3,[shade]*3)
        else:
            pigments.lathe(x,.154,[(.893,.032),(.895,.032)],["pigment"]*2,[shade]*2)
    if lod<2:
        collars.emit()
    pigments.emit()
    for i,x in enumerate(test_x):
        bottom=.876 if lod<2 else .893
        part=Part(label+("_lipstick_" if sign<0 else "_pump_")+str(i+1))
        if sign<0:
            profile=[(bottom,.021),(.948,.021),(.951,.0215),(.956,.0215),(.956,.016),
                     (.978,.016),(.981,.0151),(.981,.0126)]
            if lod:
                profile=[(bottom,.021),(.952,.021),(.952,.016),(.981,.016),(.981,.0126)]
            sleeve=["case","case","metal","metal","metal","metal","metal","metal"] if not lod else ["case","metal","metal","metal","metal"]
            part.lathe(x,.018,profile,sleeve)
            h=(1.022,1.015,1.025)[i]
            part.lathe(x,.018,[(.981,.0121),(h-.015,.0121),(h-.002,.0117),(h,.0105)],
                       ["pigment"]*4,[shades[i]]*4,slope=.52)
        else:
            shoulder=.963+(0,.008,.003)[i]
            part.lathe(x,.018,[(bottom,.032),(.885 if not lod==2 else .897,.032),(.949,.032),
                     (shoulder,.028),(shoulder+.003,.019),(shoulder+.014,.019)],
                     ["bottle","bottle","bottle","bottle","metal","metal"],[shades[i+1]]*4+[None,None])
            if lod<2:
                part.lathe(x,.018,[(shoulder+.014,.008),(shoulder+.023,.008)],["case"]*2)
                top=shoulder+.023
                part.slab(x,.025,[(top,.026,.040,.006),(top+.009,.026,.040,.006)],["case"]*2)
            else:
                part.lathe(x,.018,[(shoulder+.014,.012),(shoulder+.030,.012)],["case"]*2)
        part.emit()


def join_objects(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    active=objects[0]
    bpy.context.view_layer.objects.active=active
    bpy.ops.object.join()
    active.name=name+"_"+LEVEL
    active.data.name=name+"_"+LEVEL
    return active


def group_lower_level(lod):
    meshes=[o for o in COLLECTION.objects if o.type=="MESH"]
    # Blender fills a missing colour layer with black during join. The GLB uses
    # COLOR_0, so unpainted vertices need the neutral multiplier before joining.
    for obj in meshes:
        if obj.data.color_attributes.get("Finish") is None:
            layer=obj.data.color_attributes.new(name="Finish",type="FLOAT_COLOR",domain="CORNER")
            for entry in layer.data:
                entry.color=(1,1,1,1)
    if lod==1:
        mirror=[o for o in meshes if o.name.startswith("Mirror_")]
        testers=[o for o in meshes if o.name.startswith(("Lip_","Complexion_"))]
        cabinet=[o for o in meshes if o not in mirror+testers]
        for name,group in [("Cabinet_and_counter",cabinet),("Rear_mirror",mirror),("Mixed_tester_trays",testers)]:
            join_objects(group,name)
    elif lod==2:
        # Write fixture colours per face into one shared paint shader. Keep metallic trim and
        # silver on physically distinct PBR surfaces. The distant product dots retain their tints.
        for obj in meshes:
            mesh=obj.data
            color=mesh.color_attributes.get("Finish")
            if color is None:
                color=mesh.color_attributes.new(name="Finish",type="FLOAT_COLOR",domain="CORNER")
            for poly in mesh.polygons:
                assigned=mesh.materials[poly.material_index]
                if assigned not in (MATS["pigment"],MATS["bottle"]):
                    for loop_id in poly.loop_indices:
                        color.data[loop_id].color=(1,1,1,1) if assigned in (MATS["metal"], MATS["silver"]) else assigned.diffuse_color
            for index,mat in enumerate(mesh.materials):
                if mat not in (MATS["metal"],MATS["silver"]):
                    mesh.materials[index]=MATS["distance"]
        join_objects(meshes,"Distant_tester_bar")


def collection(name):
    col=bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def aim(obj, point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat("-Z","Y").to_euler()


def studio():
    col=collection("Studio")
    sc=bpy.context.scene
    plane=bpy.data.meshes.new("Studio plane")
    plane.from_pydata([(-40,-40,-.0003),(40,-40,-.0003),(40,40,-.0003),(-40,40,-.0003)],[],[(0,1,2,3)])
    plane.materials.append(material("Studio warm stone","D2C6BD",0,.84))
    col.objects.link(bpy.data.objects.new("Studio ground",plane))
    for name,pos,power,size_y,size_x in [
        ("Key softbox",(-2.8,-3.3,4),335,2.5,2.2),("Fill card",(2.2,-2.9,2.5),120,2.1,1.1),
        ("Rear softbox",(-.5,2.4,3.3),370,2,2),("Mirror strip",(1.4,-3.4,2.3),75,2.2,.37)]:
        light=bpy.data.lights.new(name,"AREA")
        light.energy=power
        light.shape="RECTANGLE"
        light.size=size_x
        light.size_y=size_y
        obj=bpy.data.objects.new(name,light)
        col.objects.link(obj)
        obj.location=pos
        aim(obj,(0,0,.8))
    cam=bpy.data.objects.new("Studio camera",bpy.data.cameras.new("Studio camera"))
    col.objects.link(cam)
    cam.location=(1.45,-3.8,2.04)
    aim(cam,(0,0,.76))
    cam.data.type="ORTHO"
    cam.data.ortho_scale=1.91
    sc.camera=cam
    sc.world=bpy.data.worlds.new("Studio ambient")
    sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value=(.44,.46,.49,1)
    bg.inputs["Strength"].default_value=.6
    sc.render.engine="CYCLES"
    sc.cycles.samples=40
    sc.cycles.use_denoising=True
    sc.render.resolution_x=780
    sc.render.resolution_y=780
    sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="JPEG"
    sc.render.image_settings.quality=92
    sc.view_settings.view_transform="AgX"


def show(level):
    for lvl in LEVELS:
        for obj in bpy.data.collections[lvl].objects:
            obj.hide_set(lvl!=level)
            obj.hide_render=lvl!=level


def build():
    global LEVEL, ROUND, ARC, ROOT, COLLECTION, MATS
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system="METRIC"
    MATS={k:material(*values) for k,values in {
        "enamel":("Celadon deep lacquer","486764",.14,.37),
        "charcoal":("Recessed bronze plinth","403E39",.38,.44),
        "metal":("Satin champagne metal","C5A16D",.72,.30),
        "ivory":("Warm ivory solid surface","E8E1D2",.01,.34),
        "gasket":("Mirror edge seal","494745",.12,.42),
        "silver":("Inset silvered mirror","BACCD2",.77,.125),
        "tray":("Warm slate pocket tray","575450",.18,.42),
        "pigment":("Tested lip and powder shades","FFFFFF",.025,.52,True),
        "distance":("Distant powder coated finishes","FFFFFF",.08,.43,True),
        "case":("Gloss oxblood tester casing","513A3F",.26,.28),
        "bottle":("Tinted foundation sample vessel","FFFFFF",.08,.26,True),
    }.items()}
    for lod,LEVEL in enumerate(LEVELS):
        ARC=(7,4,3)[lod]
        ROUND=(20,12,8)[lod]
        COLLECTION=collection(LEVEL)
        ROOT=bpy.data.objects.new("ASSET_CosmeticsTesterBar_"+LEVEL,None)
        COLLECTION.objects.link(ROOT)
        ROOT.empty_display_size=.10
        cabinet(lod)
        mirror(lod)
        tester_station(lod,-1,"Lip",LIP)
        tester_station(lod,1,"Complexion",FOUNDATION)
        if lod:
            group_lower_level(lod)
    studio()
    show("LOD0")
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True,relative_remap=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--export-source", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    for folder in ("exports","sources","previews","reports"):
        (HERE/folder).mkdir(exist_ok=True)
    if args.export_source:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    elif not SOURCE.exists() or args.rebuild:
        build()
    else:
        raise ValueError("Use --export-source to preserve saved edits or --rebuild to regenerate.")
    for level in LEVELS:
        show(level)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in bpy.data.collections[level].objects:
            obj.select_set(True)
        name=SLUG+("" if level=="LOD0" else "-"+level.lower())+".glb"
        bpy.ops.export_scene.gltf(filepath=str(HERE/"exports"/name),export_format="GLB",use_selection=True,
            export_apply=True,export_yup=True,export_animations=False,export_extras=False,
            export_cameras=False,export_lights=False,export_vertex_color="NAME",export_vertex_color_name="Finish")
    show("LOD0")
    if not args.skip_render:
        bpy.context.scene.render.filepath=str(HERE/"previews"/(SLUG+".jpg"))
        bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    main()
