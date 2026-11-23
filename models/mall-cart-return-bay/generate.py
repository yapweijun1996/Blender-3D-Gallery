"""Author/save and export the original two-place shopping-cart return bay, in metres."""
import argparse
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = "mall-cart-return-bay"
SOURCE = HERE / "sources" / (SLUG + ".blend")
LEVELS = ("LOD0", "LOD1", "LOD2")


def finish(name, hex_rgb, metallic, roughness):
    values = [int(hex_rgb[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    rgba = tuple(v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4 for v in values) + (1,)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    for key, value in [("Base Color", rgba), ("Metallic", metallic), ("Roughness", roughness)]:
        shader.inputs[key].default_value = value
    return mat


def link_mesh(name, vertices, faces, mat, smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(x, -z, y) for x, y, z in vertices], [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(MATS[mat])
    for poly in mesh.polygons:
        if smooth and len(poly.vertices) == 4:
            poly.use_smooth = True
    obj = bpy.data.objects.new(name + "_" + LEVEL, mesh)
    COL.objects.link(obj)
    obj.parent = ROOT
    obj["export_region"] = REGION
    return obj


def solid(name, loops, mat, smooth=False):
    n = len(loops[0])
    faces = [tuple(reversed(range(n)))]
    for i in range(1, len(loops)):
        for j in range(n):
            a = (i - 1) * n + j
            b = (i - 1) * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    faces.append(tuple(range(n * (len(loops) - 1), n * len(loops))))
    return link_mesh(name, [p for loop in loops for p in loop], faces, mat, smooth)


def pad(name, x, z, profiles, mat):
    loops = []
    for h, width, depth, cut in profiles:
        w, d = width / 2, depth / 2
        outline = [(-w+cut,-d),(w-cut,-d),(w,-d+cut),(w,d-cut),
                   (w-cut,d),(-w+cut,d),(-w,d-cut),(-w,-d+cut)]
        loops.append([(x+u,h,z+v) for u,v in outline])
    return solid(name, loops, mat)


def pipe(name, points, radius, mat, sides=None):
    path = [Vector(p) for p in points]
    rings = []
    num = sides or SIDES
    # The path is planar. Its binormal stays fixed through both elbows.
    choices = [Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1))]
    guide = min(choices, key=lambda n: max(abs((b-a).normalized().dot(n)) for a,b in zip(path,path[1:])))
    for i,p in enumerate(path):
        tangent = (path[min(i+1,len(path)-1)] - path[max(0,i-1)]).normalized()
        u = guide - tangent * tangent.dot(guide)
        u.normalize()
        v = tangent.cross(u).normalized()
        rings.append([tuple(p + radius*(u*math.cos(j*math.tau/num)+v*math.sin(j*math.tau/num)))
                     for j in range(num)])
    return solid(name, rings, mat, smooth=True)


def side_frame(x, centre):
    name = "Divider" if centre else ("Left" if x < 0 else "Right")
    h = .605 if centre else .800
    bend = .075 if centre else .095
    r = .017 if centre else .020
    for z in (-.50,.50):
        end = name + ("_back" if z < 0 else "_mouth")
        pad(end+"_foot",x,z,[(0,.100,.100,.014),(.008,.100,.100,.014),(.012,.092,.092,.012)],"dark")
        pipe(end+"_socket",[(x,.012,z),(x,.044,z)],r+.008,"metal")
        if LOD < 2:
            for dx,dz in [(-.030,-.030),(.030,.030)]:
                pipe(end+"_anchor",[(x+dx,.010,z+dz),(x+dx,.015,z+dz)],.006,"metal",6)
    path = [(x,.044,.50)]
    n = (8,4,2)[LOD]
    for i in range(n+1):
        a = i*math.pi/(2*n)
        path.append((x,h-bend+bend*math.sin(a),.50-bend+bend*math.cos(a)))
    for i in range(n+1):
        a = i*math.pi/(2*n)
        path.append((x,h-bend+bend*math.cos(a),-.50+bend-bend*math.sin(a)))
    path.append((x,.044,-.50))
    pipe(name+"_continuous_return_rail",path,r,"metal")
    low = .260 if centre else .345
    pipe(name+"_guide",[(x,low,-.50+r*.40),(x,low,.50-r*.40)],.013 if centre else .016,"teal")
    if LOD < 2:
        pipe(name+"_mouth_guard",[(x,.105,.50),(x,.208,.50)],r+.003,"dark")
    if LOD == 0:
        for z in (-.47,.47):
            pipe(name+"_guide_ferrule",[(x,low,z-.010),(x,low,z+.010)],.016 if centre else .019,"metal")


def rear_sign(x):
    name = "Left" if x<0 else "Right"
    # The raised signs stay above parked carts. Each post meets the rear rail and a forward saddle.
    for dx in (-.170,.170):
        pipe(name+"_sign_post",[(x+dx,.610,-.50),(x+dx,1.146,-.50)],.012,"metal")
        pipe(name+"_sign_saddle",[(x+dx,1.138,-.50),(x+dx,1.138,-.471)],.009,"metal")
    pad(name+"_rear_sign",x,-.471,[(1.074,.485,.018,.006),(1.079,.495,.023,.007),
                                     (1.196,.495,.023,.007),(1.201,.485,.018,.006)],"teal")
    if LOD == 2:
        pad(name+"_distant_marker",x,-.456,[(1.127,.130,.007,.002),(1.150,.130,.007,.002)],"ivory")
        return
    z=-.456
    profile=[(-.077,1.171),(-.059,1.171),(-.041,1.120),(.052,1.120),(.068,1.156),(-.052,1.156)]
    for i,((a,b),(c,d)) in enumerate(zip(profile,profile[1:])):
        pipe(name+"_cart_mark_"+str(i),[(x+a,b,z),(x+c,d,z)],.0045,"ivory",8)
    for dx in (-.030,.040):
        pipe(name+"_cart_mark_wheel",[(x+dx,1.107,z-.002),(x+dx,1.107,z+.004)],.008,"ivory",10)
    if LOD == 0:
        for dx in (-.208,.208):
            pipe(name+"_rivet",[(x+dx,1.138,z-.004),(x+dx,1.138,z+.002)],.0045,"metal",8)


def create():
    global MATS, LEVEL, LOD, SIDES, ROOT, COL, REGION
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system="METRIC"
    MATS={key:finish(*v) for key,v in {
        "metal":("Brushed rail steel","A9B9BB",.70,.30),"teal":("Deep lagoon enamel","326463",.16,.36),
        "dark":("Graphite sockets and bumpers","3D494A",.19,.49),"ivory":("Porcelain return marks","EEE7D1",.06,.40)}.items()}
    for LOD,LEVEL in enumerate(LEVELS):
        SIDES=(16,10,8)[LOD]
        COL=bpy.data.collections.new(LEVEL)
        bpy.context.scene.collection.children.link(COL)
        ROOT=bpy.data.objects.new("ASSET_CartReturnBay_"+LEVEL,None)
        COL.objects.link(ROOT)
        for x,REGION in [(-.75,"Left"),(0,"Divider"),(.75,"Right")]:
            side_frame(x,x==0)
        REGION="Rear"
        for h in (.185,.610):
            pipe("Back_stop", [(-.75,h,-.50),(.75,h,-.50)],.018,"metal")
        for x in (-.375,.375): rear_sign(x)
    studio()
    show("LOD0")
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), compress=True, relative_remap=False)


def studio():
    sc=bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=100, location=(0,0,-.0002))
    ground=bpy.context.object
    ground.name="Studio_ground"
    ground.data.materials.append(finish("Studio warm grey","C5C0B4",0,.86))
    bpy.ops.object.camera_add(location=(2.12,-2.72,1.93))
    cam=bpy.context.object
    cam.name="Studio_camera"
    focus=Vector((0,-.02,.56))
    cam.rotation_euler=(focus-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.type="ORTHO"
    cam.data.ortho_scale=2.36
    sc.camera=cam
    for name,pos,power,size in [("Key",(-2,-4,5),500,4),("Fill",(4,-1,3),360,3),("Rim",(0,3,4),520,3)]:
        bpy.ops.object.light_add(type="AREA", location=pos)
        o=bpy.context.object
        o.name="Studio_"+name
        o.rotation_euler=(focus-o.location).to_track_quat("-Z","Y").to_euler()
        o.data.energy=power
        o.data.shape="DISK"
        o.data.size=size
    sc.world=bpy.data.worlds.new("Studio daylight")
    sc.world.color=(.40,.40,.40)
    sc.render.engine="CYCLES"
    sc.cycles.samples=28
    sc.cycles.use_denoising=True
    sc.render.resolution_x=sc.render.resolution_y=700
    sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="JPEG"
    sc.render.image_settings.quality=90
    sc.view_settings.view_transform="AgX"


def show(level):
    for lvl in LEVELS:
        for o in bpy.data.collections[lvl].objects:
            o.hide_set(lvl!=level)
            o.hide_render=lvl!=level


def export_level(lvl):
    # Keep separate lateral and rear batches so collision bounds preserve the open mouths.
    show(lvl)
    sc=bpy.context.scene
    native=bpy.data.collections[lvl]
    root=next(o for o in native.objects if o.type=="EMPTY")
    root.name="Source_"+lvl
    export_root=bpy.data.objects.new("ASSET_CartReturnBay_"+lvl,None)
    sc.collection.objects.link(export_root)
    mats={}
    for o in sorted(native.objects,key=lambda x:x.name):
        if o.type!="MESH":continue
        copy=o.copy()
        copy.data=o.data.copy()
        sc.collection.objects.link(copy)
        copy.parent=export_root
        mats.setdefault((o["export_region"],o.data.materials[0].name),[]).append(copy)
    selected=[]
    for (region,mat),objects in sorted(mats.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects:o.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        if len(objects)>1:bpy.ops.object.join()
        active=objects[0]
        active.name=region+"_"+mat.replace(" ","_")+"_"+lvl
        active.data.name=active.name
        selected.append(active)
    bpy.ops.object.select_all(action="DESELECT")
    for o in selected+[export_root]:o.select_set(True)
    suffix="" if lvl=="LOD0" else "-"+lvl.lower()
    bpy.ops.export_scene.gltf(filepath=str(HERE/"exports"/(SLUG+suffix+".glb")),export_format="GLB",
        use_selection=True,export_yup=True,export_extras=False,export_animations=False,
        export_cameras=False,export_lights=False)
    for o in selected+[export_root]:bpy.data.objects.remove(o,do_unlink=True)
    root.name="ASSET_CartReturnBay_"+lvl


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    op=parser.add_mutually_exclusive_group(required=True)
    op.add_argument("--rebuild",action="store_true")
    op.add_argument("--export-source",action="store_true")
    parser.add_argument("--skip-render",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    for folder in ("exports","sources","previews","reports"):(HERE/folder).mkdir(exist_ok=True)
    if args.rebuild:create()
    else:bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    for level in LEVELS:export_level(level)
    show("LOD0")
    if not args.skip_render:
        bpy.context.scene.render.filepath=str(HERE/"previews"/(SLUG+".jpg"))
        bpy.ops.render.render(write_still=True)
