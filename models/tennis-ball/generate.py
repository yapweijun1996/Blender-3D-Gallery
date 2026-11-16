"""Original deterministic sports ball; metres; no external assets or markings."""
from pathlib import Path
import json, math, sys
import bpy, bmesh
from mathutils import Vector
HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
SLUG, ROOT = CFG["slug"], CFG["root"]
RADIUS = CFG["diameter"] / 2
TARGET = Vector((0, 0, RADIUS))
TEXTURE_SIZE = (1024, 512)
def srgb(rgb):
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb) + (1,)


def pebble_bake(ball):
    """Bake 3D Voronoi pebbles to a tangent-space normal map on the ball UVs."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 4
    scene.cycles.seed = 0
    scene.cycles.device = "CPU"
    image = bpy.data.images.new("T_Surface_Normal", *TEXTURE_SIZE, alpha=False, float_buffer=False)
    image.colorspace_settings.name = "Non-Color"
    mat = bpy.data.materials.new("BAKE_Pebbles")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    coords = nodes.new("ShaderNodeTexCoord")
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.voronoi_dimensions = "3D"
    voronoi.feature = "SMOOTH_F1"
    voronoi.inputs["Scale"].default_value = 1 / 0.00065
    voronoi.inputs["Smoothness"].default_value = 0.35
    voronoi.inputs["Randomness"].default_value = 0.85
    ramp = nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.0
    ramp.inputs["From Max"].default_value = 0.30
    ramp.inputs["To Min"].default_value = 1.0
    ramp.inputs["To Max"].default_value = 0.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.75
    bump.inputs["Distance"].default_value = 0.00018
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
    image.filepath_raw = str(HERE / "sources" / "textures" / "tennis-ball_grain_normal.png")
    image.file_format = "PNG"
    image.save()
    image.filepath = "//textures/tennis-ball_grain_normal.png"
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
    scene.camera.location = TARGET + Vector((.55, -.9, .42))
    aim(scene.camera, TARGET)
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = RADIUS * 2.85
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



def material(name, color, roughness, image=None):
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=srgb(color)
    bs.inputs['Roughness'].default_value=roughness
    bs.inputs['Metallic'].default_value=0
    if SLUG=='tennis-ball' and name=='Felt':
        bs.inputs['Sheen Weight'].default_value=.28
        bs.inputs['Sheen Roughness'].default_value=.8
    mat.diffuse_color=srgb(color)
    if image:
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
        normal=mat.node_tree.nodes.new('ShaderNodeNormalMap')
        normal.inputs['Strength'].default_value=1.2 if SLUG=='tennis-ball' else .3
        mat.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color'])
        mat.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
    return mat

# A closed, two-lobed spherical curve bounds the two figure-eight covers.
def direction(t, lat):
    p=Vector((math.cos(lat)*math.cos(t),math.cos(lat)*math.sin(t),math.sin(lat)))
    from mathutils import Matrix
    return Matrix.Rotation(.72,3,'X') @ p

def seamlat(t): return .68*math.cos(2*t)
def seam(t): return direction(t,seamlat(t))
def width_factor(t): return math.sqrt(1+(-1.36*math.sin(2*t)/math.cos(seamlat(t)))**2)

def make_mesh(name,verts,faces,mat,root):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    obj.parent=root;obj.data.materials.append(mat)
    uv=mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        poly.use_smooth=True
        us=[]
        for li in poly.loop_indices:
            v=Vector(verts[mesh.loops[li].vertex_index])-TARGET
            us.append((math.atan2(v.y,v.x)/(2*math.pi))%1)
        wrap=max(us)-min(us)>.5
        for li,u in zip(poly.loop_indices,us):
            v=(Vector(verts[mesh.loops[li].vertex_index])-TARGET).normalized()
            uv.data[li].uv=(u+1 if wrap and u<.5 else u, .5+math.asin(max(-1,min(1,v.z)))/math.pi)
    return obj

def covers(root,skin,band):
    n,m=192,24
    width=.0045 if SLUG=='tennis-ball' else .0007
    half=width/RADIUS/2
    objects=[]
    for sign in [-1,1]:
        verts=[];faces=[]
        for j in range(m):
            f=j/m
            for i in range(n):
                t=2*math.pi*i/n;edge=seamlat(t)+sign*half*width_factor(t)
                lat=edge*(1-f)+sign*math.pi/2*f
                verts.append(tuple(TARGET+direction(t,lat)*RADIUS))
        verts.append(tuple(TARGET+direction(0,sign*math.pi/2)*RADIUS));pole=len(verts)-1
        for j in range(m-1):
            for i in range(n):
                a=j*n+i;b=j*n+(i+1)%n;c=b+n;d=a+n
                faces.append((a,b,c,d) if sign==1 else (d,c,b,a))
        for i in range(n):
            a=(m-1)*n+i;b=(m-1)*n+(i+1)%n
            faces.append((a,b,pole) if sign==1 else (pole,b,a))
        objects.append(make_mesh('COVER_'+('A' if sign==1 else 'B'),verts,faces,skin,root))
    verts=[];faces=[]
    for j in range(5):
        f=j/4
        for i in range(n):
            t=2*math.pi*i/n
            depth=(.00025 if SLUG=='tennis-ball' else .00015)*math.sin(math.pi*f)
            verts.append(tuple(TARGET+direction(t,seamlat(t)+(2*f-1)*half*width_factor(t))*(RADIUS-depth)))
    for j in range(4):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
    objects.append(make_mesh('SEAM_Band',verts,faces,band,root))
    return objects

def tubes(name,paths,radius,mat,root):
    verts=[];faces=[]
    for points in paths:
        start=len(verts)
        for j,p in enumerate(points):
            tangent=(points[min(j+1,len(points)-1)]-points[max(j-1,0)]).normalized()
            normal=(p-TARGET).normalized();u=tangent.cross(normal).normalized();v=tangent.cross(u).normalized()
            for k in range(6):
                a=2*math.pi*k/6;verts.append(tuple(p+radius*(u*math.cos(a)+v*math.sin(a))))
        for j in range(len(points)-1):
            for k in range(6):
                a=start+j*6+k;b=start+j*6+(k+1)%6;faces.append((a,b,b+6,a+6))
        faces.append(tuple(start+k for k in reversed(range(6))))
        faces.append(tuple(start+(len(points)-1)*6+k for k in range(6)))
    return make_mesh(name,verts,faces,mat,root)

def build(root):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=48,radius=RADIUS)
    bakeball=bpy.context.object;image=pebble_bake(bakeball)
    bpy.data.objects.remove(bakeball,do_unlink=True)
    skin=material('Felt' if SLUG=='tennis-ball' else 'Cover',CFG['color'],CFG['roughness'],image)
    band=material('Rubber seam' if SLUG=='tennis-ball' else 'Seam',(.87,.87,.79) if SLUG=='tennis-ball' else (.25,.06,.045),.73)
    stitch=material('Stitches',(.72,.025,.035) if SLUG!='cricket-ball' else (.88,.80,.59),.62)
    if SLUG in ('tennis-ball','baseball','softball'):
        covers(root,skin,band)
        if CFG['stitch_pairs']:
            paths=[];count=CFG['stitch_pairs'];spread=.00155 if SLUG=='baseball' else .002
            for i in range(count):
                t=2*math.pi*i/count
                for side in [-1,1]:
                    points=[]
                    for j in range(4):
                        f=j/3;tt=t+(f-.5)*.025
                        lat=seamlat(tt)+side*spread/RADIUS*(1-f)
                        p=direction(tt,lat)*(RADIUS+.00012+math.sin(math.pi*f)*.00020)+TARGET
                        points.append(p)
                    paths.append(points)
            tubes('STITCHES_Double',paths,.00028 if SLUG=='baseball' else .00036,stitch,root)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=128,ring_count=64,radius=RADIUS,location=TARGET)
        ball=bpy.context.object;ball.name='BALL_Shell';ball.parent=root;ball.data.materials.append(skin)
        for p in ball.data.polygons:p.use_smooth=True
        # Subtle equatorial join recessed into the spherical shell.
        for v in ball.data.vertices:
            lat=abs(v.co.dot(direction(0,math.pi/2)))/RADIUS if SLUG=='cricket-ball' else abs(v.co.z)/RADIUS
            v.co*=1-.0015*math.exp(-(lat/.018)**2)
        if SLUG=='cricket-ball':
            paths=[]
            for row in range(6):
                lat=(row-2.5)*.017
                for i in range(72):
                    t=2*math.pi*i/72
                    paths.append([TARGET+direction(t+(.018*(f-.5)),lat+.006*(f-.5))*(RADIUS+.00015+.00012*math.sin(math.pi*f)) for f in [0,1/3,2/3,1]])
            tubes('STITCHES_SixRows',paths,.00022,stitch,root)
            # Raised primary welt and two shallow quarter-cover seams.
            paths=[[TARGET+direction(2*math.pi*i/256,0)*(RADIUS+.00005) for i in range(257)]]
            tubes('SEAM_Primary',paths,.00028,band,root)
            paths=[]
            for sign in [-1,1]:
                paths.append([TARGET+direction(math.pi/2+sign*math.pi/2,sign*math.pi*i/128)*(RADIUS-.00008) for i in range(129)])
            tubes('SEAM_QuarterPair',paths,.00013,band,root)
    # A deterministic triangle modifier keeps the source editable and export stable.
    for obj in root.children:
        if obj.type=='MESH':obj.modifiers.new('Export triangulation','TRIANGULATE')
    bpy.context.view_layer.update()
    # Floor datum uses the actual lowest point, including raised thread.
    coords=[obj.matrix_world@v.co for obj in root.children if obj.type=='MESH' for v in obj.data.vertices]
    low=min(v.z for v in coords)
    cx=(max(v.x for v in coords)+min(v.x for v in coords))/2
    cy=(max(v.y for v in coords)+min(v.y for v in coords))/2
    for obj in root.children:obj.location-=Vector((cx,cy,low))
    root['floor_adjustment_m']=-low
    root['horizontal_adjustment_m']=[-cx,-cy]


def export(path):
    # Join evaluated copies: one mesh, one primitive per material; source parts remain editable.
    root=bpy.data.objects[ROOT];copies=[]
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for obj in list(root.children):
        if obj.type!='MESH':continue
        mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),depsgraph=depsgraph)
        copy=bpy.data.objects.new('EXPORT_'+obj.name,mesh);bpy.context.scene.collection.objects.link(copy)
        copy.matrix_world=obj.matrix_world.copy();copy.parent=root;copies.append(copy)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in copies:obj.select_set(True)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join()
    joined=bpy.context.view_layer.objects.active;joined.name='MESH_'+SLUG
    try:
        root.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,
            export_animations=False,export_extras=True,export_texcoords=True,export_normals=True,
            export_cameras=False,export_lights=False,export_tangents=True,export_image_format='JPEG',export_jpeg_quality=86)
    finally:
        bpy.data.objects.remove(joined,do_unlink=True)


def main():
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version=0
        scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
        root=bpy.data.objects.new(ROOT,None);scene.collection.objects.link(root)
        root['units']='metres';root['front_axis']='Blender -Y / glTF +Z';root['up_axis']='Blender +Z / glTF +Y'
        root['panels']=CFG['panels'];root['stitch_pairs']=CFG['stitch_pairs']
        build(root);studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    if '--previews-only' not in sys.argv:
        export(HERE/'exports/optimized.glb')
        report=dict(blender_version=bpy.app.version_string,radius_m=RADIUS,diameter_m=2*RADIUS,circumference_m=2*math.pi*RADIUS,
                    panels=CFG['panels'],stitch_pairs=CFG['stitch_pairs'],stitch_rows=6 if SLUG=='cricket-ball' else 0,
                    editable_meshes=[o.name for o in bpy.data.objects[ROOT].children if o.type=='MESH'])
        (HERE/'reports/source-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    if '--skip-render' not in sys.argv:
        # Render the saved editable source, independent of temporary export state.
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
        render_views()
if __name__=='__main__':
    main()
    # This worker's Blender 5.3 PulseAudio teardown can hang after successful jobs.
    # All saves, exports and renders above are synchronous; bypass teardown only headless.
    if bpy.app.background:
        import os
        sys.stdout.flush();sys.stderr.flush();os._exit(0)
