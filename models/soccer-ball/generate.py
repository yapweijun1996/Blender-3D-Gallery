"""Original unbranded spherical panel ball. Deterministic Blender 5.3 build, metres."""
from pathlib import Path
import json, math, sys, struct, os
import bpy, bmesh
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='soccer-ball'
ROOT='ASSET_SoccerBall'
CIRCUMFERENCE=0.69
RADIUS=CIRCUMFERENCE/(2*math.pi)
TARGET=Vector((0,0,RADIUS))
LAYOUT='ico'
COLORS=[(0.045, 0.045, 0.05), (0.91, 0.9, 0.86)]
MATERIAL_NAMES=('Panel accent','Panel main','Recessed seam bed')
SEAM_COLOR=(0.12,0.12,0.13)
GAP=0.0012
DEPTH=0.0014
GRAIN=0.0014
GRAIN_DEPTH=6e-05
ROUGHNESS=0.5
TEXTURE_SIZE=(1024,512)
def srgb(rgb):
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb) + (1,)


def pebble_bake(ball):
    """Bake 3D Voronoi pebbles to a tangent-space normal map on the ball UVs."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.cycles.samples = 4
    scene.cycles.seed = 0
    scene.cycles.device = "CPU"
    image = bpy.data.images.new("T_Grip_Normal", *TEXTURE_SIZE, alpha=False, float_buffer=False)
    image.colorspace_settings.name = "Non-Color"
    mat = bpy.data.materials.new("BAKE_Pebbles")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    coords = nodes.new("ShaderNodeTexCoord")
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.voronoi_dimensions = "3D"
    voronoi.feature = "SMOOTH_F1"
    voronoi.inputs["Scale"].default_value = 1 / GRAIN
    voronoi.inputs["Smoothness"].default_value = 0.35
    voronoi.inputs["Randomness"].default_value = 0.85
    ramp = nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.0
    ramp.inputs["From Max"].default_value = 0.55
    ramp.inputs["To Min"].default_value = 1.0
    ramp.inputs["To Max"].default_value = 0.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.55
    bump.inputs["Distance"].default_value = GRAIN_DEPTH
    links.new(coords.outputs["Object"], voronoi.inputs["Vector"])
    links.new(voronoi.outputs["Distance"], ramp.inputs["Value"])
    links.new(ramp.outputs["Result"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    target = nodes.new("ShaderNodeTexImage")
    target.image = image
    nodes.active = target
    ball.data.materials.clear()
    ball.data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    ball.select_set(True)
    bpy.context.view_layer.objects.active = ball
    scene.render.bake.margin = 8
    scene.render.bake.normal_space = "TANGENT"
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=8, use_clear=True)
    image.filepath_raw = str(HERE / "sources" / "textures" / "grip_normal.png")
    image.file_format = "PNG"
    image.save()
    image.filepath = "//textures/grip_normal.png"
    ball.data.materials.clear()
    bpy.data.materials.remove(mat)
    return image


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("Slate studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.12, 0.16, 0.2, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45
    for name, location, energy, size in (("Key", (-0.6, -0.9, 1.3), 42, 0.9), ("Fill", (0.9, -0.3, 0.8), 26, 0.9),
                                         ("Rim", (0, 0.9, 0.9), 45, 0.6)):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = "STUDIO_" + name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        aim(light, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = "STUDIO_Camera"
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = 0.33
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"


def render_views():
    scene = bpy.context.scene
    for name, delta in (("hero", (0.55, -0.9, 0.42)), ("front", (0, -1.1, 0.05)),
                        ("side", (1.1, 0, 0.08)), ("3q", (-0.62, -0.85, 0.6))):
        scene.camera.location = TARGET + Vector(delta)
        aim(scene.camera, TARGET)
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(HERE / "previews" / (name + ".png"))
        bpy.ops.render.render(write_still=True)
        if name == "hero":
            scene.render.image_settings.file_format = "WEBP"
            scene.render.image_settings.quality = 86
            bpy.data.images["Render Result"].save_render(str(HERE / "previews" / "hero.webp"), scene=scene)



def polygons():
    """Construct truncated-icosahedral polygons or six cube faces split into three strips."""
    if LAYOUT == 'ico':
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1)
        bm.verts.ensure_lookup_table()
        vs = [v.co.copy() for v in bm.verts]
        faces = [[v.index for v in f.verts] for f in bm.faces]
        bm.free()
        result=[]
        for i, v in enumerate(vs):
            neighbors=sorted({j for f in faces if i in f for j in f if j != i})
            pts=[(v*2+vs[j])/3 for j in neighbors]
            c=sum(pts,Vector())/len(pts)
            u=(pts[0]-c).normalized(); w=c.normalized().cross(u)
            pts.sort(key=lambda p: math.atan2((p-c).dot(w),(p-c).dot(u)))
            result.append((pts,0))
        for a,b,c in faces:
            result.append(([(vs[a]*2+vs[b])/3,(vs[b]*2+vs[a])/3,(vs[b]*2+vs[c])/3,
                            (vs[c]*2+vs[b])/3,(vs[c]*2+vs[a])/3,(vs[a]*2+vs[c])/3],1))
        return result
    result=[]
    for axis in range(3):
        for sign in (-1,1):
            n=Vector(tuple(sign if j==axis else 0 for j in range(3)))
            u=Vector(tuple(1 if j==(axis+1)%3 else 0 for j in range(3)))
            v=n.cross(u)
            for strip in range(3):
                a=-1+2*strip/3; b=-1+2*(strip+1)/3
                result.append(([n+u*a-v,n+u*b-v,n+u*b+v,n+u*a+v],0 if strip==1 else 1))
    return result


def build(root):
    verts=[]; faces=[]; mids=[]
    def vert(p):
        verts.append(tuple(p)); return len(verts)-1
    def face(ids,mat):
        faces.append(ids); mids.append(mat)
    # Each skin patch is a distinct connected component; its bevel descends into a real gap.
    for corners, material in polygons():
        center=sum(corners,Vector())/len(corners)
        normal=center.normalized()
        if (corners[1]-corners[0]).cross(corners[2]-corners[1]).dot(normal)<0:
            corners=list(reversed(corners))
        boundary=[]
        for j,a in enumerate(corners):
            b=corners[(j+1)%len(corners)]
            for k in range(8):
                p=a.lerp(b,k/8)
                # Uniform angular gap, independent of the base polygon size.
                direction=p.normalized()
                tangent=(center.normalized()-direction*center.normalized().dot(direction)).normalized()
                boundary.append((direction+tangent*(GAP/RADIUS/2)).normalized())
        count=len(boundary); prev=None
        centre_id=vert(normal*RADIUS)
        for ring in range(1,9):
            t=ring/8
            radius=RADIUS-0.00025*(t**8)
            ids=[vert(normal.lerp(p,t).normalized()*radius) for p in boundary]
            if prev is None:
                for j in range(count): face([centre_id,ids[j],ids[(j+1)%count]],material)
            else:
                for j in range(count):
                    k=(j+1)%count
                    face([prev[j],ids[j],ids[k]],material)
                    face([prev[j],ids[k],prev[k]],material)
            prev=ids
        lower=[vert(p*(RADIUS-DEPTH)) for p in boundary]
        for j in range(count):
            k=(j+1)%count
            face([prev[j],lower[j],lower[k]],material)
            face([prev[j],lower[k],prev[k]],material)
    mesh=bpy.data.meshes.new('Editable spherical panels')
    mesh.from_pydata(verts,[],faces); mesh.update()
    ball=bpy.data.objects.new('BALL_Panels',mesh); bpy.context.scene.collection.objects.link(ball)
    ball.parent=root
    # A spherical UV unwrap retains the baked 3D grain across panel boundaries.
    uv=mesh.uv_layers.new(name='UVMap')
    for p in mesh.polygons:
        coords=[]
        for vi in p.vertices:
            d=mesh.vertices[vi].co.normalized()
            coords.append([0.5+math.atan2(d.y,d.x)/(2*math.pi),0.5+math.asin(max(-1,min(1,d.z)))/math.pi])
        if max(c[0] for c in coords)-min(c[0] for c in coords)>0.5:
            for c in coords:
                if c[0]<0.5: c[0]+=1
        for li,c in zip(p.loop_indices,coords): uv.data[li].uv=c
    bpy.context.view_layer.objects.active=ball; ball.select_set(True)
    image=pebble_bake(ball)
    for name,color in zip(MATERIAL_NAMES[:2],COLORS):
        m=bpy.data.materials.new(name); m.use_nodes=True
        nodes,links=m.node_tree.nodes,m.node_tree.links
        bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
        bs.inputs['Base Color'].default_value=srgb(color); bs.inputs['Roughness'].default_value=ROUGHNESS
        bs.inputs['Metallic'].default_value=0
        m.diffuse_color=srgb(color)
        tex=nodes.new('ShaderNodeTexImage'); tex.image=image
        norm=nodes.new('ShaderNodeNormalMap'); norm.uv_map='UVMap'
        links.new(tex.outputs['Color'],norm.inputs['Color']); links.new(norm.outputs['Normal'],bs.inputs['Normal'])
        mesh.materials.append(m)
    for p,mi in zip(mesh.polygons,mids): p.material_index=mi; p.use_smooth=True
    # Backing makes channels visibly recessed rather than open holes.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=RADIUS-DEPTH)
    backing=bpy.context.object; backing.name='BALL_RecessedBacking'; backing.parent=root
    m=bpy.data.materials.new(MATERIAL_NAMES[2]); m.use_nodes=True
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=srgb(SEAM_COLOR); bs.inputs['Roughness'].default_value=0.75
    backing.data.materials.append(m)
    for p in backing.data.polygons: p.use_smooth=True
    stitch_verts=[]; stitch_faces=[]; edge_keys=set()
    for corners,_ in polygons():
        for a,b in zip(corners,corners[1:]+corners[:1]):
            key=tuple(sorted(tuple(round(x,6) for x in v) for v in (a,b)))
            if key in edge_keys: continue
            edge_keys.add(key)
            for k in range(5):
                d=a.lerp(b,(k+0.5)/5).normalized()
                along=(b-a).normalized(); cross=d.cross(along).normalized()
                # Short dark thread runs across the gap, below the panel crown.
                start=d*(RADIUS-0.0006)-cross*GAP*0.65
                end=d*(RADIUS-0.0006)+cross*GAP*0.65
                offset=len(stitch_verts)
                for point in (start,end):
                    for q in range(6):
                        angle=q*math.pi/3
                        stitch_verts.append(tuple(point+(d*math.cos(angle)+along*math.sin(angle))*0.00012))
                for q in range(6):
                    j=(q+1)%6
                    stitch_faces.extend([(offset+q,offset+j,offset+6+j),(offset+q,offset+6+j,offset+6+q)])
    sm=bpy.data.meshes.new('Editable recessed stitch bridges'); sm.from_pydata(stitch_verts,[],stitch_faces)
    st=bpy.data.objects.new('BALL_Stitches',sm); bpy.context.scene.collection.objects.link(st); st.parent=root
    tm=bpy.data.materials.new('Recessed stitching'); tm.use_nodes=True
    bs=next(n for n in tm.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=srgb((0.28,0.27,0.25)); bs.inputs['Roughness'].default_value=0.85
    sm.materials.append(tm)
    for p in sm.polygons: p.use_smooth=True
    root['stitch_count']=len(edge_keys)*5
    # A single translation puts the lowest actual vertex precisely on the floor.
    low=min(v.co.z for v in mesh.vertices)
    low=min(low,min(v.co.z for v in backing.data.vertices))
    for obj in (ball,backing,st): obj.location.z=-low
    root['panel_count']=len(polygons()); root['layout']=LAYOUT
    return {'radius_m':RADIUS,'diameter_m':RADIUS*2,'circumference_m':CIRCUMFERENCE,
            'panels':len(polygons()),'channel_width_m':GAP,'channel_depth_m':DEPTH,
            'centre_height_m':-low,'blender_version':bpy.app.version_string,
            'panel_material_counts': [sum(m==i for _,m in polygons()) for i in range(2)]}


def export(path):
    root=bpy.data.objects[ROOT]
    bpy.ops.object.select_all(action='DESELECT')
    copies=[]
    for obj in root.children:
        if obj.type=='MESH':
            cp=obj.copy(); cp.data=obj.data.copy(); bpy.context.scene.collection.objects.link(cp)
            cp.parent=root; cp.select_set(True); copies.append(cp)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.join(); cp=bpy.context.object; cp.name='MESH_'+ROOT[6:]
    bm=bmesh.new(); bm.from_mesh(cp.data)
    bmesh.ops.triangulate(bm,faces=bm.faces); bm.to_mesh(cp.data); bm.free()
    root.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
        export_yup=True,export_animations=False,export_extras=True,export_cameras=False,
        export_lights=False,export_tangents=True,export_image_format='JPEG',export_jpeg_quality=86)
    bpy.data.objects.remove(cp,do_unlink=True)
    # Blender can emit duplicate texture bindings for the shared image. Canonicalize them.
    raw=path.read_bytes(); length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length]); binary=raw[28+length:]
    unique=[]; indices={}
    for i,t in enumerate(doc.get('textures',[])):
        if t not in unique: unique.append(t)
        indices[i]=unique.index(t)
    for mat in doc['materials']:
        if 'normalTexture' in mat: mat['normalTexture']['index']=indices[mat['normalTexture']['index']]
    doc['textures']=unique
    encoded=json.dumps(doc,separators=(',',':')).encode(); encoded+=b' '*((-len(encoded))%4)
    path.write_bytes(struct.pack('<5I',0x46546c67,2,28+len(encoded)+len(binary),len(encoded),0x4e4f534a)+encoded+struct.pack('<2I',len(binary),0x004e4942)+binary)


def main():
    for directory in ('sources','sources/textures','exports','previews','metadata','reports'):
        (HERE/directory).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version=0
        bpy.context.scene.unit_settings.system='METRIC'
        root=bpy.data.objects.new(ROOT,None); bpy.context.scene.collection.objects.link(root)
        root['units']='metres'; root['front_axis']='Blender -Y / glTF +Z'; root['up_axis']='Blender +Z / glTF +Y'
        measured=build(root)
        studio(); bpy.context.scene.camera.data.ortho_scale=RADIUS*2.8
        bpy.context.scene.camera.location=TARGET+Vector((0.55,-0.9,0.42))
        aim(bpy.context.scene.camera,TARGET)
        (HERE/'reports/source-geometry.json').write_text(json.dumps(measured,indent=2)+'\n')
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    if '--previews-only' not in sys.argv: export(HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv: render_views()

if __name__=='__main__':
    main()
    # This workstation's PulseAudio shutdown can hang after successful background jobs.
    # All outputs are closed above; retain normal exception handling on failed builds.
    if bpy.app.background:
        sys.stdout.flush(); sys.stderr.flush(); os._exit(0)
