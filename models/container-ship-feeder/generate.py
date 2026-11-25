"""Deterministic original vessel. Run: blender -b -P generate.py."""
import bpy, math, random
from pathlib import Path
from mathutils import Vector

SLUG = 'container-ship-feeder'
KIND = 'container'
L, B, DRAFT, FREE = (170, 27, 9, 9)
ROOT = Path(__file__).resolve().parent
for folder in ('exports', 'previews', 'sources'):
    (ROOT / folder).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
random.seed(42)

palette = {
    'red hull': ((.30,.065,.045,1), .7), 'upper hull': ((.045,.065,.073,1),.6),
    'boot top': ((.022,.025,.025,1),.6), 'deck': ((.21,.25,.23,1),.7),
    'white': ((.76,.78,.74,1),.48), 'dark window': ((.025,.085,.11,1),.3),
    'rail': ((.47,.49,.46,1),.55), 'yellow': ((.75,.48,.08,1),.58),
    'rust': ((.43,.14,.075,1),.7), 'container blue': ((.055,.19,.30,1),.65),
    'container red': ((.46,.095,.055,1),.68), 'container green': ((.12,.26,.20,1),.68),
    'container tan': ((.58,.49,.34,1),.72), 'pipe': ((.42,.43,.40,1),.5),
    'rubber': ((.025,.028,.027,1),.8), 'orange': ((.84,.27,.045,1),.55),
}
materials = {}
for name, (color, roughness) in palette.items():
    mat = bpy.data.materials.new(name); mat.diffuse_color = color; mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = roughness
    materials[name] = mat
# Accumulate disconnected components into one mesh per material, keeping draw calls bounded.
geo = {name: ([], []) for name in materials}
def mesh(mat, verts, faces):
    vs, fs = geo[mat]; n = len(vs); vs.extend(verts); fs.extend([tuple(n+i for i in f) for f in faces])
def box(mat, center, size):
    x,y,z=center; a,b,c=[v/2 for v in size]
    verts=[(x+i*a,y+j*b,z+k*c) for i,j,k in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    mesh(mat,verts,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
def beam(mat,a,b,width,depth=None):
    a,b=Vector(a),Vector(b); direction=b-a
    if direction.length<.0001: return
    u=direction.normalized(); ref=Vector((0,0,1)) if abs(u.z)<.95 else Vector((0,1,0))
    side=u.cross(ref).normalized()*width/2; other=u.cross(side).normalized()*(depth or width)/2
    verts=[tuple(p+s*side+t*other) for p in (a,b) for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    mesh(mat,verts,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
def cylinder(mat,center,radius,height,axis='Z',segments=12):
    x,y,z=center; verts=[]
    for s in (-1,1):
        for i in range(segments):
            a=2*math.pi*i/segments; p=radius*math.cos(a); q=radius*math.sin(a)
            verts.append((x+p,y+q,z+s*height/2) if axis=='Z' else (x+p,y+s*height/2,z+q))
    faces=[tuple(reversed(range(segments))),tuple(range(segments,2*segments))]
    faces += [(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
    mesh(mat,verts,faces)
def hull():
    # Section heights and offsets make a broad midbody, tapered stern and raked bow.
    stations=[(-.5,.23),(-.46,.69),(-.38,.96),(-.26,1),(.25,1),(.36,.95),(.43,.75),(.48,.43),(.5,.035)]
    def ring(z,scale):
        def pos(x,w,side):
            rake=max(0.0,x-.36)*max(0.0,(FREE-z)/(FREE+DRAFT))*.34
            return (L*(x-rake),side*B*w*scale/2,z)
        return [pos(x,w,-1) for x,w in stations]+[pos(x,w,1) for x,w in reversed(stations)]
    # Separate bands keep the anti-fouling paint, boot-top and topsides legible.
    levels=[(-DRAFT,.72,'red hull'),(-.45,.98,'red hull'),(.65,1,'boot top'),(FREE,1,'upper hull')]
    n=len(stations)*2
    for i in range(3):
        z1,s1,_=levels[i]; z2,s2,material=levels[i+1]
        verts=ring(z1,s1)+ring(z2,s2)
        faces=[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        mesh(material,verts,faces)
    mesh('red hull',ring(-DRAFT,.72),[tuple(reversed(range(n)))])
    mesh('deck',ring(FREE,1),[tuple(range(n))])

def railing(x1,x2,y,z,step):
    beam('rail',(x1,y,z+1),(x2,y,z+1),.12)
    for i in range(int((x2-x1)/step)+1):
        x=x1+i*step; beam('rail',(x,y,z),(x,y,z+1),.1)

def bridge(x, width, base, length, floors, floorh):
    # Deckhouse, setback bridge and dark wraparound wheelhouse glazing.
    box('white',(x,0,base+floors*floorh/2),(length,width,floors*floorh))
    for i in range(1,floors):
        box('rail',(x,0,base+i*floorh),(length+.3,width+.25,.18))
    z=base+floors*floorh
    box('white',(x+.2,0,z+floorh*.46),(length*.83,width*1.07,floorh*.92))
    for side in (-1,1):
        box('dark window',(x+.2,side*width*.538,z+floorh*.55),(length*.72,.07,floorh*.52))
        for j in range(1,5):
            box('white',(x-length*.30+j*length*.125,side*width*.542,z+floorh*.55),(.16,.1,floorh*.56))
    box('dark window',(x+.2+length*.416,0,z+floorh*.55),(.07,width*.94,floorh*.52))
    for y in (-.3,-.1,.1,.3): box('white',(x+.2+length*.418,y*width,z+floorh*.55),(.1,.13,floorh*.58))
    box('white',(x+.2,0,z+floorh),(length*.95,width*1.15,.32))
    beam('rail',(x,0,z+floorh),(x,0,z+floorh+floorh*1.5),.18)
    beam('rail',(x,-width*.25,z+floorh*2.15),(x,width*.25,z+floorh*2.15),.13)
    box('white',(x,0,z+floorh*2.18),(.4,width*.45,.16))
    for side in (-1,1):
        box('rail',(x+length*.35,side*(width/2+.08),base+1.2),(1.0,.12,2.4))
        box('dark window',(x+length*.35,side*(width/2+.15),base+1.45),(.68,.08,1.1))
    # Funnel placed abaft bridge.
    fx=x-length*.32
    box('white',(fx,0,z+floorh*1.4),(length*.20,width*.23,floorh*.8))
    box('boot top',(fx,0,z+floorh*1.82),(length*.21,width*.24,.35))
    box('orange',(fx,0,z+floorh*1.48),(length*.205,width*.235,.5))
    for side in (-1,1):
        railing(x-length*.43,x+length*.43,side*width*.57,z+floorh+.18,max(1.8,length/7))
    for side in (-1,1):
        for level in range(floors):
            for dx in (-.25, .05, .3):
                box('dark window',(x+dx*length,side*(width/2+.04),base+floorh*(level+.58)),(length*.10,.09,floorh*.3))
        box('white',(x-length*.37,side*(width/2+.07),base+floorh*.42),(length*.1,.12,floorh*.8))
    return z+floorh

def fittings():
    for side in (-1,1):
        railing(-L*.39,L*.33,side*B*.47,FREE+.15,max(3,L/30))
        for x in (-L*.4,L*.37):
            cylinder('yellow',(x,side*B*.36,FREE+.6),B*.025,1.2,segments=10)
    # bow windlass and anchor chain drums
    for y in (-B*.18,B*.18):
        cylinder('pipe',(L*.39,y,FREE+1),B*.035,B*.12,axis='Y')
        box('yellow',(L*.39,y,FREE+.35),(B*.12,B*.14,.7))
    box('white',(L*.37,0,FREE+.7),(L*.025,B*.18,1.4))
    # Dark anchor recesses and stock on the two forward topsides.
    for side in (-1,1):
        y=side*B*.38
        box('rubber',(L*.425,y,FREE*.60),(L*.018,.18,FREE*.3))
        beam('pipe',(L*.425,y,FREE*.70),(L*.425,y,FREE*.47),max(.15,B*.014))
        beam('pipe',(L*.412,y,FREE*.49),(L*.438,y,FREE*.49),max(.15,B*.014))

hull(); fittings()
# A submerged bulb, modeled as ring sections with capped ends.
def bow_bulb():
    segments=12
    sections=[(.40,.50),(.45,.80),(.49,1.0),(.505,.84),(.52,.30)]
    verts=[]
    for x,r in sections:
        for i in range(segments):
            angle=2*math.pi*i/segments
            verts.append((L*x, B*.09*r*math.cos(angle), -DRAFT*.55+B*.055*r*math.sin(angle)))
    faces=[tuple(reversed(range(segments))),tuple(range((len(sections)-1)*segments,len(sections)*segments))]
    for k in range(len(sections)-1):
        for i in range(segments):
            j=(i+1)%segments
            faces.append((k*segments+i,k*segments+j,(k+1)*segments+j,(k+1)*segments+i))
    mesh('red hull',verts,faces)
bow_bulb()

if KIND == 'container':
    bridge(-L*.38,B*.65,FREE,L*.11,3,2.8)
    # Feeder carries 40-foot boxes with varied colours and dark corner posts.
    colors=['container blue','container red','container green','container tan']
    for row in range(8):
        x=-L*.245+row*12.5
        for col in range(8):
            y=(col-3.5)*2.55
            for tier in range(3 if row in (0,7) else 4):
                z=FREE+1.45+tier*2.75
                color=colors[(row*7+col*3+tier*5)%4]
                box(color,(x,y,z),(12.05,2.42,2.65))
                # Painted corrugations are suggested by corner framing rather than extra bars.
                for side in (-1,1):
                    box(color,(x,y+side*1.22,z),(.08,.08,2.52))
                for dx in (-5.9,5.9):
                    box('rail',(x+dx,y,z),(.1,2.43,2.66))
                # edge/door detail visible from aerial and oblique views
                for dy in (-.65,.65): box('rail',(x+6.04,y+dy,z),(.025,.045,2.35))
    for side in (-1,1):
        # Tapered enclosed lifeboat mounted on davits.
        x=-L*.37; y=side*B*.37; z=FREE+5
        boat=[(x-2.8,y-.9,z+.8),(x+2.8,y-.9,z+.8),(x+2.8,y+.9,z+.8),(x-2.8,y+.9,z+.8),
              (x-2.1,y-.55,z-.8),(x+2.1,y-.55,z-.8),(x+2.1,y+.55,z-.8),(x-2.1,y+.55,z-.8)]
        mesh('orange',boat,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        box('white',(-L*.37,side*B*.37,FREE+5.94),(5.0,2.0,.16))
        for dx in (-2,2): beam('rail',(-L*.37+dx,side*B*.33,FREE+6.2),(-L*.37+dx,side*B*.40,FREE+4.3),.12)
elif KIND == 'tanker':
    bridge(-L*.4,B*.65,FREE,L*.105,3,3)
    # Long manifolds, cross pipes, valves and tank access domes on a clear deck.
    for y in (-B*.24,-B*.15,-B*.06,B*.04,B*.14,B*.24):
        beam('pipe',(-L*.31,y,FREE+1.5),(L*.37,y,FREE+1.5),.65)
        for x in (-L*.25,-L*.10,L*.05,L*.20,L*.34):
            box('yellow',(x,y,FREE+.65),(.5,1.1,1.3))
    for x in (-L*.22,-L*.06,L*.10,L*.26):
        beam('rust',(x,-B*.32,FREE+2.1),(x,B*.32,FREE+2.1),.7)
        for y in (-B*.32,B*.32): cylinder('yellow',(x,y,FREE+1.2),.7,2.4)
    for x in (-L*.28,-L*.12,L*.04,L*.20,L*.34):
        for y in (-B*.35,B*.35):
            cylinder('deck',(x,y,FREE+.5),2.4,1)
            cylinder('rail',(x,y,FREE+1.08),1.6,.18)
    for side in (-1,1): box('orange',(-L*.38,side*B*.36,FREE+5),(7,2.8,2))
elif KIND == 'bulk':
    bridge(-L*.41,B*.62,FREE,L*.095,3,2.7)
    # Five individual steel hatch covers and four deck cranes in the inter-hatch gaps.
    for i in range(5):
        x=-L*.24+i*L*.125
        box('rust',(x,0,FREE+1.0),(L*.105,B*.68,2))
        for j in range(1,6): box('rail',(x-L*.052+j*L*.105/6,0,FREE+2.03),(.13,B*.67,.12))
        for y in (-B*.33,B*.33): box('upper hull',(x,y,FREE+1.1),(L*.108,.35,2.2))
    for i in range(4):
        x=-L*.177+i*L*.125
        cylinder('yellow',(x,0,FREE+1.6),2.0,3.2)
        box('yellow',(x,0,FREE+4),(4,4,2))
        beam('yellow',(x,0,FREE+4.8),(x+8,0,FREE+17),1.2,1.5)
        beam('rail',(x+8,0,FREE+17),(x+8,0,FREE+5),.13)
        box('yellow',(x+8,0,FREE+4.7),(1.1,1.1,.6))
    for side in (-1,1): box('orange',(-L*.4,side*B*.35,FREE+4),(6,2.2,1.7))
else:
    # Compact working tug with a tall wheelhouse and heavy rubber protection.
    bridge(-2,B*.63,FREE,9,2,2.1)
    box('upper hull',(-L*.38,0,FREE+.5),(4,B*.55,1))
    for side in (-1,1):
        for x in (-12,-9,-6,-3,0,3,6,9,12):
            cylinder('rubber',(x,side*(B*.49+.15),.9),.65,.55,axis='Y',segments=12)
        beam('rubber',(-L*.4,side*B*.50,FREE-.5),(L*.38,side*B*.50,FREE-.5),.55)
    for y in (-2,-1,0,1,2): cylinder('rubber',(L*.47,y,1),.7,.5,axis='Y')
    cylinder('yellow',(-10,0,FREE+.8),1.1,1.6)
    box('orange',(-2,-B*.34,FREE+3),(2.7,.5,1))
    box('orange',(-2,B*.34,FREE+3),(2.7,.5,1))

for name,(verts,faces) in geo.items():
    if not verts: continue
    data=bpy.data.meshes.new(name); data.from_pydata(verts,[],faces); data.update()
    obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj); data.materials.append(materials[name])
# Generate a hull atlas procedurally. UV X follows ship length and
# UV Y follows elevation, so the bands line up on both sides and across materials.
def bake_hull_maps():
    # Work in metres so the waterline and the weathering scale remain consistent
    # across vessels with different draft and freeboard.
    import numpy as np
    size = 512
    rng = np.random.default_rng(87421)
    x = ((np.arange(size) + .5) / size - .5) * L
    z = ((np.arange(size) + .5) / size) * (DRAFT + FREE) - DRAFT
    xx, zz = np.meshgrid(x, z)

    def noise_field(spacing_x, spacing_z, octaves=3):
        result = np.zeros((size, size), dtype=np.float64)
        total = 0.0
        for octave in range(octaves):
            nx = max(2, int(math.ceil(L / spacing_x * 2**octave)) + 2)
            nz = max(2, int(math.ceil((DRAFT + FREE) / spacing_z * 2**octave)) + 2)
            values = rng.random((nz, nx))
            u = np.linspace(0, nx - 1.001, size)
            v = np.linspace(0, nz - 1.001, size)
            ix = u.astype(int); iz = v.astype(int)
            fx = u - ix; fz = v - iz
            fx = fx * fx * (3 - 2 * fx); fz = fz * fz * (3 - 2 * fz)
            rows = values[:, ix] * (1 - fx) + values[:, ix + 1] * fx
            field = rows[iz, :] * (1 - fz[:, None]) + rows[iz + 1, :] * fz[:, None]
            weight = .5**octave
            result += field * weight; total += weight
        return result / total

    fine = noise_field(2.4, 1.1, 4)
    fading = noise_field(18, 7, 3)
    fading = (fading - fading.min()) / (fading.max() - fading.min())
    # Original paint colours are linear RGB. Fade varies by up to six percent.
    stops = [(-DRAFT, (.23,.038,.023)), (-.55, (.30,.055,.030)),
             (-.45, (.018,.022,.021)), (.65, (.018,.022,.021)),
             (.9, (.055,.073,.078)), (FREE, (.055,.073,.078))]
    color = np.stack([np.interp(z, [s[0] for s in stops], [s[1][c] for s in stops])
                      for c in range(3)], axis=-1)[:, None, :] * np.ones((1, size, 1))
    color *= (1 + .12 * (fading - .5))[:, :, None]

    # Faint plate joins remain visible, while only a random subset sheds rust.
    pitch = 7.5
    seam_x = np.arange(-L / 2, L / 2, pitch)
    distance = np.abs((xx + L / 2 + pitch / 2) % pitch - pitch / 2)
    color *= (1 - .035 * np.exp(-.5 * (distance / .11)**2))[:, :, None]

    # Random, independent run origins prevent rust repeating at plating pitch.
    # Most start at the deck edge; smaller runs start at seams and the anchor pocket.
    streaks = np.zeros((size, size), dtype=np.float64)
    origins = [(rng.uniform(-L*.46, L*.46), FREE, rng.uniform(min(.8, FREE*.45), max(.81, FREE*.85)))
               for _ in range(max(12, int(L / 3.5)))]
    origins += [(sx, rng.uniform(FREE*.45, FREE*.85),
                 rng.uniform(.6, max(.61, FREE*.65))) for sx in seam_x
                if rng.random() < .38]
    origins += [(L*.425, FREE*.46, max(.45, FREE*.30))]
    for sx, top, length in origins:
        width = rng.uniform(.10, .27) * max(1, L / 100)**.3
        down = top - zz
        run = np.exp(-.5 * ((xx - sx + (fine - .5) * .25) / width)**2)
        run *= np.clip(down / .20, 0, 1) * np.clip(1 - down / length, 0, 1)**.65
        streaks = np.maximum(streaks, run * rng.uniform(.35, .85))
    streaks *= np.clip(.45 + fine, 0, 1)
    rust = np.array((.092, .028, .013))  # linear RGB: approximately sRGB .335, .183, .118
    color = color * (1 - streaks[:, :, None]) + rust * streaks[:, :, None]

    # A continuous wet film fades smoothly over 1.5 m on either side of z=0.
    wet = np.clip(1 - np.abs(zz) / 1.5, 0, 1)
    wet = wet * wet * (3 - 2 * wet)
    color *= (1 - .25 * wet)[:, :, None]
    rough = .76 - .17 * wet

    baked = []
    for name, pixels, non_color in [('Hull color atlas', color, False),
                                    ('Hull roughness atlas', np.repeat(rough[:, :, None], 3, axis=2), True)]:
        img = bpy.data.images.new(name, width=size, height=size, alpha=False)
        if non_color:
            img.colorspace_settings.name = 'Non-Color'
        # Generated image buffers are packed as raw PNG samples, so encode color
        # to sRGB explicitly; roughness stays linear data.
        if not non_color:
            pixels = np.where(pixels <= .0031308, pixels * 12.92,
                              1.055 * np.power(pixels, 1 / 2.4) - .055)
        rgba = np.concatenate((pixels, np.ones((size, size, 1))), axis=2).astype(np.float32)
        img.pixels.foreach_set(rgba.ravel())
        img.pack()
        baked.append(img)
    for name in ('red hull','boot top','upper hull'):
        obj=bpy.data.objects[name]
        uvmap=obj.data.uv_layers.new(name='Hull atlas')
        for poly in obj.data.polygons:
            for li in poly.loop_indices:
                v=obj.data.vertices[obj.data.loops[li].vertex_index].co
                uvmap.data[li].uv=((v.x/L)+.5,(v.z+DRAFT)/(DRAFT+FREE))
        target=materials[name]; n=target.node_tree.nodes; l=target.node_tree.links
        bsdf=n.get('Principled BSDF')
        color=n.new('ShaderNodeTexImage'); color.image=baked[0]; l.new(color.outputs['Color'],bsdf.inputs['Base Color'])
        roughness=n.new('ShaderNodeTexImage'); roughness.image=baked[1]; roughness.image.colorspace_settings.name='Non-Color'; l.new(roughness.outputs['Color'],bsdf.inputs['Roughness'])
bake_hull_maps()

# Save editable generated source, and export only vessel objects.
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'sources'/(SLUG+'.blend')))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(ROOT/'exports'/(SLUG+'.glb')),export_format='GLB',use_selection=True,export_yup=True)
# Render actual exported GLB from three views, no studio objects exported.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'exports'/(SLUG+'.glb')))
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.render.resolution_x=1200; scene.render.resolution_y=800; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.world=bpy.data.worlds.new('Studio world'); scene.world.color=(.19,.19,.19)
scene.view_settings.view_transform='AgX'
def aim(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def area(location,energy,size):
    data=bpy.data.lights.new('studio','AREA'); data.energy=energy; data.shape='DISK'; data.size=size
    obj=bpy.data.objects.new('studio',data); scene.collection.objects.link(obj); obj.location=location; aim(obj,(0,0,FREE))
area((L*.2,-L*.6,L*.9),L*L*16,L*.8)
area((-L*.6,L*.3,L*.6),L*L*9,L*.7)
camdata=bpy.data.cameras.new('camera'); cam=bpy.data.objects.new('camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO'; camdata.ortho_scale=L*1.32
for name,pos,target,scale in [
    ('side',(0,-L*1.4,FREE*.7),(0,0,FREE*.4),L*1.15),
    ('hero',(L*.8,-L*1.3,L*.17),(0,0,FREE*.6),L*1.25),
    ('bridge',(-L*.20,-L*.25,FREE+L*.14),(-L*.38,0,FREE+8),L*.29),
    ('stern',(-L*.85,L*1.05,L*.72),(0,0,FREE*.6),L*1.32),
    ('top',(L*.02,-L*.1,L*1.5),(0,0,FREE*.6),L*1.32)]:
    camdata.ortho_scale=scale; cam.location=pos; aim(cam,target); scene.render.filepath=str(ROOT/'previews'/(name+'.png')); bpy.ops.render.render(write_still=True)
print('FINISHED',SLUG)
