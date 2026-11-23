"""Blender-world anatomical windows and compactly supported deformation fields."""
import numpy as np
from mathutils.bvhtree import BVHTree
from face import HAIR, bpy

CENTER = .000722

def masks(xyz):
    x,y,z=xyz.T
    a=np.abs(x-CENTER)
    front=(y<-.075)&(a<.158)&(z>.602)&(z<.838)
    return {
        "face": front,
        "eye_and_rim": front&(a>.042)&(a<.14)&(z>.692)&(z<.789),
        "brow": front&(a>.043)&(a<.136)&(z>=.789)&(z<.829),
        "nose": front&(a<.024)&(z>.681)&(z<.72),
        "lip_and_corners":front&(a<.039)&(z>.645)&(z<.681),
        "cheeks":front&(a>=.039)&(a<.146)&(z>.643)&(z<.699),
        "chin_and_lower_jaw":front&(a<.083)&(z>.602)&(z<=.645),
    }

def hair_distance(xyz):
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(HAIR))
    bpy.context.view_layer.update()
    objects=set(bpy.context.scene.objects)-before
    hair=next(o for o in objects if o.type=="MESH")
    tree=BVHTree.FromPolygons([hair.matrix_world@v.co for v in hair.data.vertices],[p.vertices[:] for p in hair.data.polygons])
    distances=np.array([tree.find_nearest(p)[3] for p in xyz])
    for o in objects:
        bpy.data.objects.remove(o,do_unlink=True)
    return distances

def smooth(x):
    t=np.clip(x,0,1)
    return t*t*(3-2*t)

def deformation(xyz,distances,state):
    x,y,z=xyz.T
    sx=x-CENTER
    a=np.abs(sx)
    envelope=(smooth((.158-a)/.020)*smooth((-.075-y)/.022)
              *smooth((z-.602)/.018)*smooth((.838-z)/.018)
              *smooth((distances-.016)/.016))
    def patch(cx,cz,rx,rz):
        # Compact support keeps the rest mesh byte-for-byte stationary.
        q=((a-cx)/rx)**2+((z-cz)/rz)**2
        return np.maximum(1-q,0)**2
    corners=patch(.024,.663,.031,.026)
    cheek=patch(.099,.680,.064,.045)
    brow=patch(.087,.787,.064,.040)
    eyelid=patch(.089,.742,.060,.059)
    mouth=patch(0,.662,.048,.027)
    jaw=patch(0,.636,.083,.048)
    delta=np.zeros_like(xyz)
    if state=="happy":
        delta[:,0]=np.sign(sx)*(.0036*corners+.0010*cheek)
        delta[:,1]=-.0039*cheek-.0011*eyelid
        orbit=smooth((a-.039)/.024)*smooth((.144-a)/.024)*smooth((z-.672)/.026)*smooth((.809-z)/.031)
        closure=np.clip(.31*(.744-z),-.0085,.0085)*orbit
        delta[:,2]=.0060*corners+.0072*cheek+.0018*brow+closure
    elif state=="surprised":
        delta[:,0]=-.0028*np.sign(sx)*corners
        delta[:,1]=.0020*mouth+.0008*jaw
        delta[:,2]=(.0054*brow+.085*(z-.742)*eyelid-.0063*jaw
                     +.0038*np.tanh((z-.665)/.004)*mouth)
    elif state=="sad":
        delta[:,0]=-.0007*np.sign(sx)*corners
        delta[:,1]=.0009*cheek-.0007*mouth
        delta[:,2]=(-.0056*corners-.0017*cheek+
                     (.0011-.0050*np.clip((a-.084)/.040,-1,1))*brow-.0016*eyelid)
    return delta*envelope[:,None]

def lid_relief(xyz,depth,distances,state):
    """Soften the deep source socket under painted lids, retaining near-hair vertices."""
    from face import LEFT,BOTTOM,SCALE,H,W
    x,y,z=xyz.T
    px=np.clip(np.rint((x-LEFT)*SCALE-.5).astype(int),0,W-1)
    row=H-.5-(z-BOTTOM)*SCALE
    upper=depth[H-1-421,px]
    lower=depth[H-1-640,px]
    t=np.clip((row-421)/(640-421),0,1)
    upper=np.where(np.isfinite(upper),upper,0.)
    lower=np.where(np.isfinite(lower),lower,0.)
    silhouette=upper*(1-t)+lower*t
    # A gently convex closed lid spans between the points above and below the orbit.
    desired=silhouette-.0016*4*t*(1-t)
    eye_x=np.abs(x-CENTER)
    window=(smooth((eye_x-.040)/.012)*smooth((.145-eye_x)/.014)
            *smooth((row-422)/42)*smooth((640-row)/41)
            *smooth((-.075-y)/.019)*smooth((distances-.016)/.016))
    strength={"happy":.0085,"surprised":.0026,"sad":.0043}[state]
    return -window*strength*np.tanh(np.maximum(y-desired,0)/.013)
