"""Author and export the original two-surface retail tether exhibit in glTF metre coordinates."""
import argparse
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = "mall-product-security-tether"
SOURCE = HERE / "sources" / (SLUG + ".blend")
LEVELS = ("LOD0", "LOD1", "LOD2")


def color(hex_rgb):
    c=[int(hex_rgb[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)+(1,)


def material(name, hex_rgb, metallic, roughness):
    m=bpy.data.materials.new(name)
    m.diffuse_color=color(hex_rgb)
    m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=m.diffuse_color
    p.inputs["Metallic"].default_value=metallic
    p.inputs["Roughness"].default_value=roughness
    return m


def rounded(w,d,r):
    pts=[]
    for x,z,start in [(w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),
                      (-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)]:
        for i in range(ARC+1):
            a=math.radians(start+90*i/ARC)
            pts.append((x+r*math.cos(a),z+r*math.sin(a)))
    return pts


def shell(name,loops,materials,smooth=False):
    n=len(loops[0])
    verts=[(x,-z,y) for loop in loops for x,y,z in loop]
    faces=[tuple(reversed(range(n)))]
    indices=[materials[0]]
    for k in range(len(loops)-1):
        for j in range(n):
            a,b=k*n+j,k*n+(j+1)%n
            faces.append((a,b,b+n,a+n))
            indices.append(materials[k])
    faces.append(tuple(range(len(verts)-n,len(verts))))
    indices.append(materials[-1])
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    unique=list(dict.fromkeys(indices))
    for key in unique:
        mesh.materials.append(MATS[key])
    for f,key in zip(mesh.polygons,indices):
        f.material_index=unique.index(key)
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        mesh.set_sharp_from_angle(angle=math.radians(32))
    obj=bpy.data.objects.new(name+"_"+LEVEL,mesh)
    COLLECTION.objects.link(obj)
    obj.parent=ROOT
    return obj


def body(name,x,z,stages,materials):
    loops=[[(x+u,h,z+v) for u,v in rounded(w,d,r)] for h,w,d,r in stages]
    return shell(name,loops,materials)


def boot(name,z,h,profile,mats):
    loops=[[(x,h+r*math.sin(i*math.tau/SIDES),z+r*math.cos(i*math.tau/SIDES)) for i in range(SIDES)]
           for x,r in profile]
    return shell(name,loops,mats,True)


def cable():
    # The endpoints leave both molded boots along X. The eye-shaped bend lies
    # toward the customer (+Z) and rises above the palm-rest edge before crossing it.
    points=[(-.038,.013,.006),(-.043,.013,.006),(-.055,.018,.015),(-.070,.024,.033),
            (-.085,.0265,.039),(-.099,.0269,.034),(-.111,.0261,.020),
            (-.117,.0257,.007),(-.122,.0257,.003),(-.1255,.0257,.003)]
    knots=[Vector(p) for p in points]
    centers=[]
    subdivisions=(4,3,1)[LOD]
    for i in range(len(knots)-1):
        p0,p1,p2,p3=knots[max(0,i-1)],knots[i],knots[i+1],knots[min(len(knots)-1,i+2)]
        for s in range(subdivisions):
            t=s/subdivisions
            centers.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    centers.append(knots[-1])
    loops=[]
    for i,c in enumerate(centers):
        tangent=(centers[min(len(centers)-1,i+1)]-centers[max(i-1,0)]).normalized()
        if i in (0,len(centers)-1):
            tangent=Vector((-1,0,0))
        a=tangent.cross(Vector((0,1,0))).normalized()
        b=tangent.cross(a).normalized()
        loops.append([tuple(c+.0020*(a*math.cos(j*math.tau/SIDES)+b*math.sin(j*math.tau/SIDES)))
                      for j in range(SIDES)])
    shell("Looped_polymer_lead",loops,["lead"]*len(loops),True)


def build_level():
    body("Table_adhesive_sole",0,0,[(0,.050,.050,.0095),(.0016,.050,.050,.0095)],["rubber"]*2)
    table=[(.0016,.050,.050,.0095),(.0032,.053,.053,.011),(.006,.053,.053,.011),
           (.0066,.0518,.0518,.0105),(.008,.0518,.0518,.0105),(.0086,.053,.053,.011),
           (.016,.053,.053,.011),(.0206,.048,.048,.0102),(.0215,.046,.046,.0095)]
    skins=["graphite","graphite","graphite","rubber","graphite","pearl","pearl","pearl","pearl"]
    if LOD==2:
        table=[table[i] for i in (0,1,2,6,8)]
        skins=["graphite","graphite","pearl","pearl","pearl"]
    body("Table_display_base",0,0,table,skins)
    if LOD<2:
        body("Base_indicator_reveal",0,.012,
             [(.0215,.021,.0046,.0018),(.0218,.021,.0046,.0018),(.0220,.020,.004,.0015)],["graphite"]*3)
        body("Base_indicator_inset",0,.012,[(.022,.013,.002,.0009),(.0223,.0126,.0018,.0008)],["lens"]*2)
    # The stock laptop is 20 mm above this tabletop at the agreed sensor site.
    # A 30 x 20 mm flat contact patch is wholly inside the measured palm rest.
    body("Device_sensor_adhesive_sole",-.150,0,
         [(.020,.030,.020,.0050),(.0209,.030,.020,.0050)],["rubber"]*2)
    body("Device_sensor_housing",-.150,0,
         [(.0209,.030,.020,.005),(.022,.033,.022,.006),(.026,.033,.022,.006),
          (.028,.030,.020,.005),(.0284,.028,.018,.0045)],["graphite","graphite","pearl","pearl","pearl"])
    if LOD==0:
        body("Sensor_witness_inlay",-.155,0,[(.0284,.0018,.007,.0008),(.02855,.0018,.007,.0008)],["lens"]*2)
    source=[(-.0265,.0044),(-.0273,.0045),(-.0282,.0045),(-.0285,.0036),
            (-.0302,.0037),(-.0304,.0031),(-.0310,.0031),(-.0312,.00355),
            (-.0328,.00345),(-.0331,.0029),(-.0337,.0029),(-.0340,.0032),
            (-.0358,.0029),(-.0370,.0024),(-.038,.0022)]
    tip=[(-.1335,.0039),(-.1328,.0040),(-.1319,.0039),(-.1316,.0031),
         (-.1303,.0032),(-.1301,.0027),(-.1295,.0027),(-.1292,.00295),
         (-.1274,.00265),(-.1255,.0022)]
    if LOD:
        source=[source[i] for i in ((0,2,3,8,12,14) if LOD==1 else (0,3,14))]
        tip=[tip[i] for i in ((0,2,3,8,9) if LOD==1 else (0,3,9))]
    boot("Base_strain_relief",.006,.013,source,["trim"]+["rubber"]*(len(source)-1))
    boot("Device_strain_relief",.003,.0257,tip,["trim"]+["rubber"]*(len(tip)-1))
    cable()


def group_lod():
    # The small cable ends and fittings share draw calls at room-scale distances.
    meshes=[o for o in COLLECTION.objects if o.type=="MESH"]
    if LOD==2:
        for obj in meshes:
            for i,mat in enumerate(obj.data.materials):
                if mat in (MATS["lead"],MATS["rubber"],MATS["trim"]):
                    obj.data.materials[i]=MATS["graphite"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    active=meshes[0]
    bpy.context.view_layer.objects.active=active
    bpy.ops.object.join()
    active.name="Tether_assembly_"+LEVEL
    active.data.name=active.name


def collection(name):
    col=bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def aim(obj,point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat("-Z","Y").to_euler()


def studio():
    sc=bpy.context.scene
    col=collection("Studio")
    # This support represents the palm rest only in the source studio and thumbnail.
    # Its matte surface raises the secondary foot to exactly its installed elevation.
    def block(name,corners,height,mat):
        vertices=[(x,-z,h) for h in (-.002,height) for x,z in corners]
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(vertices,[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        mesh.materials.append(mat)
        col.objects.link(bpy.data.objects.new(name,mesh))
    block("Studio table",[(-4,-4),(4,-4),(4,4),(-4,4)],-.00001,material("Studio warm surface","C9BEB1",0,.74))
    shape=[(-1,-1),(-.099,-1),(-.099,.037),(-1,.037)]
    block("Studio elevated palm rest",shape,.01999,material("Studio anodized surface","777C81",.35,.48))
    for name,pos,power,size in [("Large softbox",(-.25,-.3,.38),4,.26),("Strip",(.13,.22,.16),3,.13),("Fill",(.2,-.2,.12),.9,.16)]:
        light=bpy.data.lights.new(name,"AREA");light.energy=power;light.shape="DISK";light.size=size
        obj=bpy.data.objects.new(name,light);col.objects.link(obj);obj.location=pos;aim(obj,(-.07,0,.015))
    cam=bpy.data.objects.new("Studio camera",bpy.data.cameras.new("Studio camera"));col.objects.link(cam)
    cam.location=(.03,-.24,.195);aim(cam,(-.07,-.006,.016));cam.data.type="ORTHO";cam.data.ortho_scale=.235
    cam.data.clip_start=.001;sc.camera=cam
    sc.world=bpy.data.worlds.new("Studio ambient");sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes["Background"];bg.inputs["Color"].default_value=(.57,.59,.61,1);bg.inputs["Strength"].default_value=.55
    sc.render.engine="CYCLES";sc.cycles.samples=35;sc.cycles.use_denoising=True
    sc.render.resolution_x=780;sc.render.resolution_y=540;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="JPEG";sc.render.image_settings.quality=92;sc.view_settings.view_transform="AgX"


def show(level):
    for label in LEVELS:
        for obj in bpy.data.collections[label].objects:
            obj.hide_set(label!=level);obj.hide_render=label!=level


def build():
    global LOD,LEVEL,ARC,SIDES,MATS,COLLECTION,ROOT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system="METRIC"
    MATS={k:material(*params) for k,params in {
        "pearl":("Pearl satin shell","DCDEDA",.19,.32),"graphite":("Basalt enclosure","4B504E",.22,.38),
        "rubber":("Graphite elastomer","414544",.02,.55),"lead":("Jacketed security lead","454B4B",.04,.48),
        "trim":("Anodized port collar","9A968B",.68,.30),"lens":("Pale jade indicator inset","7EA797",.09,.23)}.items()}
    for LOD,LEVEL in enumerate(LEVELS):
        ARC=(5,3,2)[LOD];SIDES=(12,9,6)[LOD]
        COLLECTION=collection(LEVEL)
        ROOT=bpy.data.objects.new("ASSET_ProductSecurityTether_"+LEVEL,None);ROOT.empty_display_size=.01
        COLLECTION.objects.link(ROOT)
        build_level()
        if LOD:
            group_lod()
    studio();show("LOD0");bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True,relative_remap=False)


def main():
    p=argparse.ArgumentParser();p.add_argument("--export-source",action="store_true");p.add_argument("--skip-render",action="store_true")
    p.add_argument("--rebuild",action="store_true");args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    for d in ("sources","exports","reports","previews"):(HERE/d).mkdir(exist_ok=True)
    if args.export_source:bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    elif not SOURCE.exists() or args.rebuild:build()
    else:raise ValueError("Use --export-source to retain edits or --rebuild to replace the source.")
    for level in LEVELS:
        show(level);bpy.ops.object.select_all(action="DESELECT")
        for obj in bpy.data.collections[level].objects:obj.select_set(True)
        suffix="" if level=="LOD0" else "-"+level.lower()
        bpy.ops.export_scene.gltf(filepath=str(HERE/"exports"/(SLUG+suffix+".glb")),export_format="GLB",use_selection=True,
             export_apply=True,export_yup=True,export_animations=False,export_extras=False,export_lights=False,export_cameras=False)
    show("LOD0")
    if not args.skip_render:
        bpy.context.scene.render.filepath=str(HERE/"previews"/(SLUG+".jpg"));bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    main()
