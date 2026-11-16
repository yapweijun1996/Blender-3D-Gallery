"""Original procedural sports asset; deterministic Blender 5.3, metre units."""
from pathlib import Path
import sys, math, json
import bpy, bmesh
import numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG=HERE.name
CONFIG={'golf-ball':('GolfBall',.04267),'bowling-ball':('BowlingBall',.2159),'medicine-ball':('MedicineBall',.28),'beach-ball':('BeachBall',.5),'ice-hockey-puck':('IceHockeyPuck',.0762)}
PASCAL,D=CONFIG[SLUG]; R=D/2; H=.0254 if SLUG=='ice-hockey-puck' else D
ROOT='ASSET_'+PASCAL
TARGET=Vector((0,0,H/2))

def material(name,color,rough=.5):
    m=bpy.data.materials.new(name); m.use_nodes=True; m.diffuse_color=(*color,1)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=0
    if SLUG in ('bowling-ball','beach-ball'): p.inputs['Coat Weight'].default_value=.35
    return m

def texture(m,kind):
    """Bake deterministic analytic UV fields to a source PNG; export embeds JPEG."""
    w,h=1024,512; u,v=np.meshgrid((np.arange(w)+.5)/w,(np.arange(h)+.5)/h)
    if kind=='swirl':
        x=np.cos(2*np.pi*u)*np.sin(np.pi*v); y=np.sin(2*np.pi*u)*np.sin(np.pi*v); z=np.cos(np.pi*v)
        f=.5+.5*np.sin(13*x+7*z+3*np.sin(6*y+3*z)+2*np.sin(8*z-4*x))
        f=np.clip((f-.35)*3,0,1)[...,None]
        rgb=np.array([.035,.07,.16])*(1-f)+np.array([.45,.12,.24])*f
    else:
        if kind=='knurl':
            a=2*np.pi*(96*u+8*v); b=2*np.pi*(96*u-8*v)
            dx=.25*(np.cos(a)+np.cos(b)); dy=.25*(np.cos(a)-np.cos(b))
        else:
            dx=.23*np.sin(2*np.pi*160*u)*np.cos(2*np.pi*80*v)
            dy=.23*np.cos(2*np.pi*160*u)*np.sin(2*np.pi*80*v)
        nz=np.ones_like(u); norm=np.sqrt(dx*dx+dy*dy+nz*nz)
        rgb=np.stack((-dx/norm*.5+.5,-dy/norm*.5+.5,nz/norm*.5+.5),axis=-1)
    rgba=np.concatenate((rgb,np.ones((h,w,1))),axis=-1).astype(np.float32)
    im=bpy.data.images.new(SLUG+'_'+kind,width=w,height=h,alpha=False)
    if kind!='swirl': im.colorspace_settings.name='Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.filepath_raw=str(HERE/'sources/textures'/ (SLUG+'_'+kind+'.png')); im.file_format='PNG'; im.save(); im.filepath='//textures/'+SLUG+'_'+kind+'.png'
    nodes=m.node_tree.nodes; links=m.node_tree.links; t=nodes.new('ShaderNodeTexImage'); t.image=im
    p=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    if kind=='swirl': links.new(t.outputs['Color'],p.inputs['Base Color'])
    else:
        n=nodes.new('ShaderNodeNormalMap'); links.new(t.outputs['Color'],n.inputs['Color']); links.new(n.outputs['Normal'],p.inputs['Normal'])

def sphere(name,r=R,loc=None,segments=96,rings=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=r,location=loc or (0,0,R))
    o=bpy.context.object; o.name=name
    for p in o.data.polygons:p.use_smooth=True
    return o

def mesh(name,vs,fs,mat):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o);o.data.materials.append(mat)
    for p in me.polygons:p.use_smooth=True
    return o

def golf(root):
    # Frequency-six geodesic grid: 10*f^2+2 = 362 symmetric dimple centres.
    bm=bmesh.new(); bmesh.ops.create_icosphere(bm,subdivisions=1,radius=1)
    verts=[v.co.copy().normalized() for v in bm.verts]; faces=[[v.index for v in f.verts] for f in bm.faces];bm.free()
    pts=[]; tris=[]; ids={}
    def idx(v):
        v=v.normalized(); k=tuple(round(x,7) for x in v)
        if k not in ids:ids[k]=len(pts);pts.append(v)
        return ids[k]
    for face in faces:
        a,b,c=[verts[i] for i in face];grid={}
        for i in range(7):
            for j in range(7-i):grid[i,j]=idx((a*(6-i-j)+b*i+c*j)/6)
        for i in range(6):
            for j in range(6-i):
                tris.append((grid[i,j],grid[i+1,j],grid[i,j+1]))
                if i+j<5:tris.append((grid[i+1,j],grid[i+1,j+1],grid[i,j+1]))
    assert len(pts)==362
    adj=[[] for _ in pts]
    for t in tris:
        q=sum((pts[i] for i in t),Vector()).normalized()
        for i in t:adj[i].append(q)
    vs=[]; fs=[]
    for c,qs in zip(pts,adj):
        axis=c.cross(Vector((0,0,1)))
        if axis.length<.1:axis=c.cross(Vector((0,1,0)))
        axis.normalize(); other=c.cross(axis)
        qs.sort(key=lambda q:math.atan2(q.dot(other),q.dot(axis)))
        boundary=[]
        for i,q in enumerate(qs):boundary.extend([q,(q+qs[(i+1)%len(qs)]).normalized()])
        rings=[]
        for ring in range(3):
            rr=[]
            for q in boundary:
                tangent=(q-c*c.dot(q)).normalized()
                if ring==0:p=q*R
                else:
                    angle=.073 if ring==1 else .040; depth=.000025 if ring==1 else .00017
                    p=(c*math.cos(angle)+tangent*math.sin(angle))*(R-depth)
                rr.append(len(vs));vs.append(tuple(p+TARGET))
            rings.append(rr)
        n=len(boundary)
        for a,b in zip(rings,rings[1:]):
            for j in range(n):fs.append((a[j],a[(j+1)%n],b[(j+1)%n],b[j]))
        center=len(vs);vs.append(tuple(c*(R-.00021)+TARGET))
        for j in range(n):fs.append((rings[-1][j],rings[-1][(j+1)%n],center))
    o=mesh('BALL_DimpledCover',vs,fs,material('White urethane',(.82,.82,.8),.26));o.parent=root
    # Weld cell borders, then orient outward; source stays editable geometry.
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
    return {'dimples':362,'dimple_centres_gltf':[[p.x*R,p.z*R+R,-p.y*R] for p in pts]}

def build(root):
    if SLUG=='golf-ball':return golf(root)
    if SLUG=='ice-hockey-puck':
        bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=R,depth=H,location=(0,0,H/2));o=bpy.context.object;o.name='PUCK_Rubber'
        bevel=o.modifiers.new('Rounded moulded edges','BEVEL');bevel.width=.00065;bevel.segments=3
        m=material('Vulcanized black rubber',(.0025,.003,.0035),.72);texture(m,'knurl');o.data.materials.append(m)
        o.data.materials.append(material('Smooth black faces',(.0025,.003,.0035),.72))
        # Satin carbon-filled rubber: broad, weak dielectric highlights on black faces.
        for mat in o.data.materials:
            bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            bsdf.inputs['Specular IOR Level'].default_value=.08
        for p in o.data.polygons:p.use_smooth=len(p.vertices)==4;p.material_index=0 if len(p.vertices)==4 else 1
        o.parent=root;return {'knurled_band':True,'edge_radius_m':.00065,'rubber_base_colour_linear':[.0025,.003,.0035],'rubber_roughness':.72,'rubber_specular_ior_level':.08}
    o=sphere('BALL_Shell');o.parent=root
    if SLUG=='bowling-ball':
        m=material('Two colour reactive resin',(.1,.1,.1),.10);texture(m,'swirl');o.data.materials.append(m)
        holes=[]
        for i,(x,y,z,r,depth) in enumerate([(-.018,-.035,.10,.010,.055),(.018,-.035,.10,.010,.055),(0,-.094,.052,.013,.065)]):
            direction=Vector((x,y,z)).normalized(); surface=direction*R+TARGET
            bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=depth+.03,location=surface-direction*(depth-.03)/2)
            cut=bpy.context.object;cut.name='CUTTER_Hole_'+str(i+1);cut.rotation_euler=direction.to_track_quat('Z','Y').to_euler();cut.hide_render=True;cut.display_type='WIRE'
            mod=o.modifiers.new('Drilled hole '+str(i+1),'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;cut.hide_set(True)
            holes.append({'surface':[surface.x,surface.z,-surface.y],'direction':[direction.x,direction.z,-direction.y],'radius_m':r,'depth_m':depth})
        return {'holes':holes,'hole_openings':3}
    if SLUG=='medicine-ball':
        mats=[material('Charcoal grip rubber',(.025,.03,.035),.7),material('Muted teal grip rubber',(.025,.26,.23),.65)]
        for m in mats:texture(m,'grip');o.data.materials.append(m)
        for p in o.data.polygons:
            z=sum(o.data.vertices[i].co.z for i in p.vertices)/len(p.vertices)
            p.material_index=int(abs(z)<R*.42)
        valve=sphere('VALVE_Fill',.004,(0,-R+.001,R),32,16);valve.scale=(1,.35,1);valve.data.materials.append(material('Valve rubber',(.008,.009,.01)));valve.parent=root
        return {'fill_valves':1,'two_tone_bands':True}
    # Six distinct vinyl gore regions separated by shallow real radial weld recesses.
    colors=[(.8,.035,.025),(.95,.63,.02),(.025,.42,.1),(.035,.21,.8),(.75,.04,.3),(.03,.65,.7)]
    for i,c in enumerate(colors):o.data.materials.append(material('GORE_'+str(i+1),c,.22))
    o.data.materials.append(material('CAP_White',(.85,.85,.83),.22))
    for v in o.data.vertices:
        p=v.co;theta=math.atan2(p.y,p.x)%(2*math.pi); a=theta%(math.pi/3)
        if min(a,math.pi/3-a)<.001 and abs(p.z)<R*.968:p*=1-.0015/R
    for p in o.data.polygons:
        c=sum((o.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
        p.material_index=6 if abs(c.z)>R*.965 else int((math.atan2(c.y,c.x)%(2*math.pi))/(math.pi/3))%6
    valve=sphere('VALVE_InflationPlug',.009,(0,0,D-.002),32,16);valve.scale.z=.32;valve.data.materials.append(o.data.materials[6]);valve.parent=root
    return {'coloured_gores':6,'white_caps':2,'inflation_valves':1}

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def studio():
    s=bpy.context.scene;s.world=bpy.data.worlds.new('Slate studio');s.world.use_nodes=True
    bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.12,.16,.2,1);bg.inputs['Strength'].default_value=.45
    scale=D/.2386
    for name,loc,power in [('Key',(-.6,-.9,1.3),42),('Fill',(.9,-.3,.8),26),('Rim',(.2,.7,1),38)]:
        bpy.ops.object.light_add(type='AREA',location=Vector(loc)*scale);l=bpy.context.object;l.name='STUDIO_'+name;l.data.energy=power*scale**2;l.data.shape='DISK';l.data.size=.9*scale;aim(l,TARGET)
    bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=D*1.38
    s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.seed=0;s.cycles.use_denoising=True
    s.render.resolution_x=s.render.resolution_y=900;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'

def export():
    root=bpy.data.objects[ROOT];copies=[];bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    for o in list(root.children_recursive):
        if o.type!='MESH':continue
        me=bpy.data.meshes.new_from_object(o.evaluated_get(dg),depsgraph=dg)
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=bm.faces)
        bad=[f for f in bm.faces if f.calc_area()<1e-10]
        if bad:bmesh.ops.delete(bm,geom=bad,context='FACES')
        bm.to_mesh(me);bm.free()
        c=bpy.data.objects.new('EXPORT_'+o.name,me);bpy.context.scene.collection.objects.link(c);c.matrix_world=o.matrix_world.copy();c.parent=root;copies.append(c)
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for c in copies:c.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(HERE/'exports/optimized.glb'),export_format='GLB',use_selection=True,export_yup=True,export_animations=False,export_extras=True,export_cameras=False,export_lights=False,export_image_format='JPEG',export_jpeg_quality=86,export_tangents=SLUG in ('medicine-ball','ice-hockey-puck'))
    for c in copies:bpy.data.objects.remove(c,do_unlink=True)

def render_views():
    s=bpy.context.scene
    for name,delta in [('hero',(.55,-.9,.55)),('front',(0,-1.1,.05)),('side',(1.1,0,.08)),('3q',(-.62,-.85,.6))]:
        s.camera.location=TARGET+Vector(delta)*(D/.2386);aim(s.camera,TARGET);s.render.image_settings.file_format='PNG';s.render.filepath=str(HERE/'previews'/ (name+'.png'));bpy.ops.render.render(write_still=True)
        if name=='hero':s.render.image_settings.file_format='WEBP';s.render.image_settings.quality=86;bpy.data.images['Render Result'].save_render(str(HERE/'previews/hero.webp'),scene=s)

def main():
    bpy.context.preferences.system.audio_device='None'
    for d in ['sources','sources/textures','exports','previews','reports','metadata']:(HERE/d).mkdir(parents=True,exist_ok=True)
    if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/ (SLUG+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
        s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=bpy.data.objects.new(ROOT,None);s.collection.objects.link(root)
        for k,v in {'units':'metres','front_axis':'Blender -Y / glTF +Z','up_axis':'Blender +Z / glTF +Y'}.items():root[k]=v
        features=build(root);studio()
        (HERE/'reports/source-geometry.json').write_text(json.dumps({'blender_version':bpy.app.version_string,'diameter_m':D,'height_m':H,**features},indent=2)+'\n')
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/ (SLUG+'.blend')),compress=True)
    if '--previews-only' not in sys.argv:export()
    if '--skip-render' not in sys.argv:render_views()
if __name__=='__main__':
    main()
    # This host's PulseAudio teardown can hang after successful background jobs.
    # All files have been synchronously saved; bypass only process teardown.
    if bpy.app.background:
        import os
        sys.stdout.flush();sys.stderr.flush();os._exit(0)
