"""Solar System Asset Factory. Run through Blender MCP or Blender 5.1 Python.
No downloads or third-party executable code. Existing non-factory scenes are preserved.
Usage in Blender: exec(compile(open(PATH).read(), PATH, 'exec')); build('earth')
"""
import bpy, numpy as np, math, json, hashlib
from pathlib import Path
from mathutils import Vector, noise
ROOT = Path(__file__).resolve().parents[1]
FACT_URL = 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/'
# Diameter is equatorial; periods are rounded reference values, not ephemerides.
FACTS = {
 'sun': (1391400, None, 7.25, 609.12, 0),
 'mercury': (4879,88.0,.034,1407.6,57.9), 'venus':(12104,224.7,177.4,-5832.5,108.2),
 'earth':(12756,365.2,23.4,23.9,149.6), 'mars':(6792,687,25.2,24.6,228),
 'jupiter':(142984,4331,3.1,9.9,778.5), 'saturn':(120536,10747,26.7,10.7,1432),
 'uranus':(51118,30589,97.8,-17.2,2867), 'neptune':(49528,59800,28.3,16.1,4515),
 'moon':(3475,27.3,6.7,655.7,.384), 'pluto':(2376,90560,119.5,-153.3,5906.4),
}
LABELS={'asteroid-01':'Cratered rocky asteroid','asteroid-02':'Elongated asteroid','asteroid-03':'Angular fractured asteroid','asteroid-04':'Rubble-pile-inspired asteroid','asteroid-05':'Porous rocky asteroid','comet':'Comet nucleus'}
NOTES={
 'sun':'Procedural granulation and sunspots are artistic approximations, not an observation at a specific date. Warm color enhanced for display; no halo. Sun tilt is relative to the ecliptic; rotation is the adopted 16 degree latitude reference.',
 'mercury':'Procedural crater distribution and shallow radial relief are illustrative, not mapped Mercury topography.',
 'venus':'Opaque cloud-top representation. Procedural yellow/cream variations are enhanced; the surface is intentionally concealed.',
 'earth':'Caltech/JPL/USGS topographic land/ocean map; stylized colors rather than photographic Blue Marble; synthetic separate clouds and thin tinted atmosphere are illustrative, not current weather or physical scattering.',
 'mars':'Viking albedo mosaic preserves broad geographic regions including Tharsis/Olympus Mons region; no elevation dataset is used. Warm color enhancement and microrelief are illustrative; mapped bright poles are retained.',
 'jupiter':'Procedural cloud bands and Great Red Spot are representative, not a current observation; no terrain displacement.',
 'saturn':'Procedural cloud bands and ring optical profile, including an explicit Cassini gap. Relative ring radii approximate C/B/A rings; optical depth is artistic, not particle simulation.',
 'uranus':'Subtle procedural bands; 97.8 degree obliquity retained in metadata, not baked into geometry. No terrain displacement.',
 'neptune':'Restrained blue cloud bands are illustrative; no invented named storm. Color enhanced for visual identification.',
 'moon':'NASA CGI Moon Kit albedo preserves maria and mapped impact features. Added micro-normal texture is illustrative, not LOLA elevation.',
 'pluto':'New Horizons MVIC enhanced-color mosaic preserves Tombaugh Regio. Sparse/unobserved southern coverage is filled with a neutral procedural icy continuation, explicitly not measured terrain.',
}
ALL=list(FACTS)+list(LABELS)

def image(name, pixels, noncolor=False):
 h,w,c=pixels.shape
 if c==3: pixels=np.concatenate((pixels,np.ones((h,w,1),np.float32)),2)
 im=bpy.data.images.new(name,width=w,height=h,alpha=True)
 im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
 im.pixels.foreach_set(np.clip(pixels,0,1).astype(np.float32).ravel())
 im.filepath_raw=str(ROOT/'textures'/(name+'.png')); im.file_format='PNG'; im.save(); im.pack()
 return im

def field(w,h,seed):
 # Periodic harmonic fields have no longitude seam and are deterministic.
 rng=np.random.default_rng(seed); u=np.arange(w,dtype=np.float32)[None,:]/w; v=np.linspace(0,1,h,dtype=np.float32)[:,None]
 a=np.zeros((h,w),np.float32)
 for f,amp in [(3,.26),(7,.15),(17,.08),(43,.04),(103,.018),(217,.008)]:
  a+=amp*np.sin(2*np.pi*(f*u+np.sin(v*(f*.7)+rng.random()*6)*.23)+rng.random()*6)*np.cos(v*f*1.9+rng.random()*6)
 return u,v,a

def craters(h,w,seed,count=180):
 rng=np.random.default_rng(seed); a=np.zeros((h,w),np.float32)
 for i in range(count):
  x=rng.integers(w); y=rng.integers(int(h*.08),int(h*.92)); r=rng.uniform(3,40)*(w/2048)
  ry=max(2,int(r*1.5)); rx=max(2,int(ry/max(.25,math.sin(y/h*math.pi))))
  yy=np.arange(max(0,y-ry),min(h,y+ry+1)); xx=np.arange(x-rx,x+rx+1)
  d=np.sqrt(((xx-x)*max(.25,math.sin(y/h*math.pi))/r)[None,:]**2+((yy-y)/r)[:,None]**2)
  z=-.65*np.exp(-(d/.64)**4)+.4*np.exp(-((d-.92)/.12)**2)
  a[np.ix_(yy,xx%w)]+=z*.15
 return a

def normal_from_height(name,a,strength):
 dy,dx=np.gradient(a)
 n=np.stack((-dx*strength, -dy*strength,np.ones_like(a)),2); n/=np.linalg.norm(n,axis=2,keepdims=True)
 return image(name,n*.5+.5,True)

def material(name,tex=None,rough=.8,normal=None,emission=False,alpha=False,color=(.7,.7,.7,1)):
 m=bpy.data.materials.new(name); m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=color
 p.inputs['Alpha'].default_value=color[3]; p.inputs['Metallic'].default_value=0; p.inputs['Roughness'].default_value=rough
 if tex:
  t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=tex
  m.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color'])
  if alpha: m.node_tree.links.new(t.outputs['Alpha'],p.inputs['Alpha'])
  if emission:
   m.node_tree.links.new(t.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=1.0
 if normal:
  t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=normal
  n=m.node_tree.nodes.new('ShaderNodeNormalMap'); m.node_tree.links.new(t.outputs['Color'],n.inputs['Color']);m.node_tree.links.new(n.outputs['Normal'],p.inputs['Normal'])
 if alpha: m.surface_render_method='DITHERED';m.use_transparency_overlap=False
 return m

def sphere(name,scene,root,mat,segments=96,rings=48,radial=None,scale=(1,1,1)):
 # Single pole vertices and triangle caps avoid zero-area UV-sphere triangles.
 verts=[(0,0,-scale[2]*(radial(Vector((0,0,-1))) if radial else 1))]; uv=[(.5,0)]
 for j in range(1,rings):
  lat=-math.pi/2+j/rings*math.pi
  for i in range(segments):
   u=i/segments;lon=(u-.5)*math.tau
   d=Vector((math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)))
   r=radial(d) if radial else 1
   verts.append(tuple(d[k]*r*scale[k] for k in range(3)));uv.append((u,j/rings))
 top=len(verts);verts.append((0,0,scale[2]*(radial(Vector((0,0,1))) if radial else 1)));uv.append((.5,1));faces=[]
 for i in range(segments):faces.append((0,1+(i+1)%segments,1+i))
 for j in range(rings-2):
  for i in range(segments):
   a=1+j*segments+i;b=1+j*segments+(i+1)%segments
   faces.append((a,b,b+segments,a+segments))
 for i in range(segments):faces.append((top,1+(rings-2)*segments+i,1+(rings-2)*segments+(i+1)%segments))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.parent=root;mesh.materials.append(mat)
 layer=mesh.uv_layers.new(name='UVMap')
 for poly in mesh.polygons:
  poly.use_smooth=True
  us=[uv[mesh.loops[l].vertex_index][0] for l in poly.loop_indices]
  seam=max(us)-min(us)>.5
  for l in poly.loop_indices:
   vi=mesh.loops[l].vertex_index;u,v=uv[vi]
   if seam and u<.5:u+=1
   if vi in (0,top):u=sum((uv[mesh.loops[k].vertex_index][0]+(1 if seam and uv[mesh.loops[k].vertex_index][0]<.5 else 0)) for k in poly.loop_indices if mesh.loops[k].vertex_index not in (0,top))/2
   layer.data[l].uv=(u,v)
 return obj

def build(asset):
 assert asset in ALL,asset
 assert not (ROOT/'exports'/(asset+'.glb')).exists(), 'Refusing to overwrite existing asset; move factory outputs before intentional regeneration.'
 seed=100+ALL.index(asset)*37
 scene=bpy.data.scenes.new('SOLAR_'+asset);bpy.context.window.scene=scene
 root=bpy.data.objects.new('ASSET_'+asset.replace('-','_').title(),None);scene.collection.objects.link(root)
 root['asset_id']=asset;root['normalized_radius']=1.;root['scientific_notes']=NOTES.get(asset,'Fictional procedural small body; not a reconstruction of a named observed object.')
 if asset in FACTS:root['axial_tilt_degrees']=FACTS[asset][2]
 w,h=(1024,512) if asset in LABELS else (2048,1024)
 u,v,a=field(w,h,seed); lat=(v-.5)*math.pi; lon=(u-.5)*math.tau
 normal=None;radial=None;rough=.86
 if asset in ('earth','mars','moon','pluto'):
  tex=bpy.data.images.load(str(ROOT/'reference'/(asset+'.jpg')),check_existing=False);tex.name=asset+'-albedo';tex.colorspace_settings.name='sRGB'
  if tex.size[0]>2048:tex.scale(2048,1024)
  if asset=='mars':
   px=np.array(tex.pixels[:],np.float32).reshape(tex.size[1],tex.size[0],4);px[:,:,:3]*=np.array([1,.72,.64]);tex.pixels.foreach_set(px.ravel())
  if asset=='pluto':
   px=np.array(tex.pixels[:],np.float32).reshape(tex.size[1],tex.size[0],4)
   missing=np.max(px[:,:,:3],2)<.035
   px[missing,:3]=(.46,.41,.36)
   tex.pixels.foreach_set(px.ravel())
  tex.filepath_raw=str(ROOT/'textures'/(asset+'-albedo.png'));tex.file_format='PNG';tex.save();tex.pack()
  if asset!='earth':normal=normal_from_height(asset+'-normal',a+craters(h,w,seed,100 if asset=='moon' else 50),4)
 elif asset in ('sun','mercury') or asset in LABELS:
  crater=craters(h,w,seed,650 if asset=='asteroid-05' else (280 if asset!='sun' else 0))
  z=a+crater
  if asset=='sun':
   gran=np.sin(2*math.pi*197*u+5*np.sin(v*179))*np.cos(v*349+4*np.sin(2*math.pi*61*u))
   z=.10*gran+a*.5
   spots=np.zeros((h,w),np.float32)
   for cx,cy,rx,ry in [(.66,.55,.017,.012),(.72,.43,.009,.011),(.34,.62,.012,.007),(.49,.39,.008,.006)]:
    d=((u-cx)/rx)**2+((v-cy)/ry)**2;spots+=.88*np.exp(-d*2)+.22*np.exp(-d*.3)
   rgb=np.stack(np.broadcast_arrays(.96+z*.15-spots*.8,.30+z*.4-spots*.26,.035+z*.12-spots*.025),2)
  else:
   base={'mercury':(.44,.42,.39),'asteroid-01':(.38,.32,.26),'asteroid-02':(.3,.28,.26),'asteroid-03':(.47,.4,.32),'asteroid-04':(.29,.28,.26),'asteroid-05':(.36,.32,.28),'comet':(.17,.18,.19)}[asset]
   rgb=np.stack([np.clip(c+z*.42,.02,.9) for c in base],2)
   if asset=='comet':
    frost=np.clip((a-.12)*3,0,.4);rgb+=frost[:,:,None]*np.array([.8,.9,1])
   normal=normal_from_height(asset+'-normal',z,8 if asset in LABELS else 5)
   def radial(d):
    q=noise.noise_vector(d*3.7,noise_basis='PERLIN_ORIGINAL');r=1+.035*q.x
    if asset in LABELS:r+=.14*noise.noise(d*2.4,noise_basis='PERLIN_ORIGINAL')+.035*noise.noise(d*13)
    return r
  tex=image(asset+'-albedo',rgb)
 else:
  warp=a*.12+.013*np.sin(u*math.tau*9+v*24)
  b=np.sin((v+warp*.12)*math.pi*32);fine=np.sin((v+warp*.09)*math.pi*127)
  if asset=='jupiter':
   rgb=np.stack(np.broadcast_arrays(.72+.13*b+.025*fine+a*.1,.57+.13*b+.02*fine+a*.1,.43+.12*b+.015*fine+a*.08),2)
   x=(u-.66)/.048;y=(v-.38)/.027;d=x*x+y*y;mask=np.clip((1.15-d)*5,0,1)
   spot=np.stack(np.broadcast_arrays(.66+.1*np.sin(d*14),.30+.05*np.sin(d*14),.18+.04*np.sin(d*14)),2)
   rgb=rgb*(1-mask[:,:,None])+spot*mask[:,:,None]
  elif asset=='saturn':rgb=np.stack(np.broadcast_arrays(.77+.045*b+.008*fine+a*.04,.67+.043*b+.008*fine+a*.03,.48+.035*b+.006*fine+a*.03),2)
  elif asset=='venus':rgb=np.stack(np.broadcast_arrays(.87+a*.16+.018*b,.76+a*.2+.017*b,.53+a*.2+.015*b),2)
  elif asset=='uranus':rgb=np.stack(np.broadcast_arrays(.37+.01*b+a*.025,.74+.013*b+a*.03,.79+.012*b+a*.025),2)
  else:rgb=np.stack(np.broadcast_arrays(.12+.003*b+a*.008,.34+.005*b+a*.012,.72+.006*b+a*.012),2)
  tex=image(asset+'-albedo',rgb);rough=.65
 mat=material(asset+' | surface',tex,rough,normal,emission=asset=='sun')
 if asset in LABELS:
  shape={'asteroid-01':(1,.85,.8),'asteroid-02':(1.45,.62,.63),'asteroid-03':(1,.83,.72),'asteroid-04':(1.06,.87,.82),'asteroid-05':(.95,.83,1),'comet':(1.25,.72,.67)}[asset]
  def rocky(d):
   r=1+.19*noise.noise(d*2.6,noise_basis='PERLIN_ORIGINAL')+.045*noise.noise(d*12)
   if asset=='comet':r*=.72+.4*abs(d.x)
   if asset=='asteroid-05':r-=.045*max(0,noise.noise(d*12))
   return r
  body=sphere(asset+' | nucleus',scene,root,mat,64,32,rocky,shape)
  if asset=='asteroid-03':
   dec=body.modifiers.new('Fracture facets','DECIMATE');dec.ratio=.22;bpy.context.view_layer.objects.active=body;body.select_set(True);bpy.ops.object.modifier_apply(modifier=dec.name)
   for p in body.data.polygons:p.use_smooth=False
  if asset=='asteroid-04':
   rng=np.random.default_rng(seed)
   for i in range(48):
    d=Vector(rng.normal(size=3)).normalized();r=rng.uniform(.10,.23)
    peb=sphere('Rubble clast %02d'%i,scene,root,mat,12,6,scale=(r,r*.8,r*.7));peb.location=Vector((d.x*shape[0],d.y*shape[1],d.z*shape[2]))*.93
 else:body=sphere(asset+' | body',scene,root,mat,radial=radial)
 if asset=='earth':
  cloud=np.clip((a+.10)*2,0,.78)*np.maximum(0,np.cos(lat))**.25
  rgba=np.ones((h,w,4),np.float32);rgba[:,:,:3]=.95;rgba[:,:,3]=cloud
  cm=material('Earth | synthetic cloud deck',image('earth-clouds',rgba),.93,alpha=True)
  sphere('Earth | clouds',scene,root,cm,96,48,scale=(1.009,)*3)
  am=material('Earth | thin atmosphere',rough=1,color=(.18,.5,.95,.065));am.surface_render_method='DITHERED';am.use_backface_culling=True
  sphere('Earth | atmosphere',scene,root,am,64,32,scale=(1.018,)*3)
 if asset=='saturn':
  # Radial strip UV. Cassini Division is a true empty annulus, not a painted line.
  rw=1024;t=np.linspace(0,1,rw);opacity=.35+.22*np.sin(t*121)**2+.2*np.sin(t*399)**2
  rgba=np.ones((4,rw,4),np.float32);rgba[:,:,:3]=np.stack((.68+.13*np.sin(t*75)**2,.60+.12*np.sin(t*75)**2,.45+.13*np.sin(t*75)**2),1)[None,:,:];rgba[:,:,3]=opacity
  rm=material('Saturn | semitransparent icy rings',image('saturn-rings',rgba),.9,alpha=True);rm.use_backface_culling=False
  for ri,ro in [(1.24,1.525),(1.525,1.95),(2.025,2.27)]:
   verts=[];faces=[]
   for k in range(257):
    a=k/256*math.tau
    for r in (ri,ro):verts.append((r*math.cos(a),r*math.sin(a),0))
   for k in range(256):faces.append((2*k,2*k+1,2*k+3,2*k+2))
   me=bpy.data.meshes.new('Ring annulus');me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new('Saturn | ring %.3f'%ri,me);scene.collection.objects.link(ob);ob.parent=root;me.materials.append(rm)
   layer=me.uv_layers.new(name='UVMap')
   for p in me.polygons:
    for l in p.loop_indices:
     vv=me.vertices[me.loops[l].vertex_index].co;layer.data[l].uv=((vv.length-1.24)/(2.27-1.24),.5)
 # Studio remains in source only, never GLB.
 world=bpy.data.worlds.new('Studio '+asset);world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.18,.21,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
 for name,loc,power,size in [('Key',(3,-4,5),550,4),('Fill',(-4,-1,2),250,5),('Rim',(1,3,3),400,3)]:
  data=bpy.data.lights.new('STUDIO_'+name,'AREA');data.energy=power;data.shape='DISK';data.size=size;ob=bpy.data.objects.new(data.name,data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
 camdata=bpy.data.cameras.new('STUDIO_Camera');cam=bpy.data.objects.new('STUDIO_Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
 cam.location=(3.1,4.7,2.4) if asset=='jupiter' else ((5.6,0,2.4) if asset=='pluto' else (3.1,-4.7,2.4));cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=5.3 if asset=='saturn' else 3.2
 scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
 scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'previews'/(asset+'.png'))
 scene.view_settings.view_transform='AgX'
 bpy.context.view_layer.update()
 bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
 for o in root.children_recursive:o.select_set(True)
 bpy.context.view_layer.objects.active=body
 bpy.ops.export_scene.gltf(filepath=str(ROOT/'exports'/(asset+'.glb')),export_format='GLB',use_selection=True,use_active_scene=True,export_extras=True,export_animations=False,export_yup=True,export_tangents=True,export_cameras=False,export_lights=False)
 bpy.data.libraries.write(str(ROOT/'sources'/(asset+'.blend')),{scene},fake_user=True,compress=True)
 bpy.ops.render.render(write_still=True)
 f=FACTS.get(asset)
 provenance=json.loads((ROOT/'reference'/'provenance.json').read_text())
 meta=dict(id=asset,name=LABELS.get(asset,asset.title()),category='Small bodies' if asset in LABELS else ('Star' if asset=='sun' else 'Solar System'),status='draft',created='2026-11-04',blender_version=bpy.app.version_string,creation_method='Blender Python through Blender MCP',generator='scripts/generate.py',seed=seed,paths=dict(glb='exports/'+asset+'.glb',source='sources/'+asset+'.blend',preview='previews/'+asset+'.png'),display=dict(radius=1,units='normalized, not meters',north_axis='Blender +Z / glTF +Y',uv='Equirectangular: u=0 west seam, v=0 south; no horizontal mirror',axial_tilt_baked=False,previewRotationY={'jupiter':-2.05,'pluto':-1.1}.get(asset,0)),scientific_properties=dict(diameter_km=f[0],orbital_period_days=f[1],axial_tilt_degrees=f[2],rotation_period_hours=f[3],semi_major_axis_million_km=f[4],orbit_primary='Earth' if asset=='moon' else ('galactic orbit not modeled' if asset=='sun' else 'Sun'),source=FACT_URL if asset!='sun' else 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html') if f else None,accuracy_notes=root['scientific_notes'],attribution=[x for x in provenance if x['id']==asset],rights='Original procedural geometry/materials: redistribution terms pending owner decision. Referenced maps retain NASA/source usage terms. No endorsement.',animations='None; orbit, spin and dynamic comet tail belong to Three.js.')
 (ROOT/'metadata'/(asset+'.json')).write_text(json.dumps(meta,indent=2)+'\n')
 result={'id':asset,'glb_bytes':(ROOT/'exports'/(asset+'.glb')).stat().st_size,'scene':scene.name,'source':str(ROOT/'sources'/(asset+'.blend'))}
 return result

if __name__ == '__main__':
 import sys
 chosen=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ALL
 for asset in chosen: print(json.dumps(build(asset)))
