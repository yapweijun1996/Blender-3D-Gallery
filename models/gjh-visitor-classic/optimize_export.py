"""Simplify covered contours in the runtime copy of the Classic visitor."""
from math import ceil, floor
import bmesh
import numpy as np


def weld(obj, pairs):
    """Keep the authored position, shading normal and weights of each target."""
    if not pairs:
        return
    mesh = obj.data
    normals = {tuple(v.co): tuple(v.normal) for v in mesh.vertices}
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        targets = {bm.verts[i]: bm.verts[j] for i, j in pairs}
        bmesh.ops.weld_verts(bm, targetmap=targets)
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.update()
    mesh.normals_split_custom_set_from_vertices([normals[tuple(v.co)] for v in mesh.vertices])


def columns(rows, sides, remove, offset=0):
    return [(offset + row*sides+i, offset + row*sides+j)
            for row in rows for i,j in remove]


def simplify_back_of_head(obj):
    # Leave the complete forward half untouched: the facial ink matches those
    # exact facets. Keep the axial extrema of every authored cranium section.
    rings = {}
    for v in obj.data.vertices:
        rings.setdefault(round(v.co.z,6),[]).append(v)
    pairs = []
    for ring in rings.values():
        if len(ring)<12:
            continue
        cy = (max(v.co.y for v in ring)+min(v.co.y for v in ring))*.5
        back = [v for v in ring if v.co.y>cy+.013]
        back.sort(key=lambda v:v.co.x)
        for i in range(1, len(back)-1, 2):
            if abs(back[i].co.x)>.015:
                pairs.append((back[i].index, back[i-1].index))
    weld(obj,pairs)


def trim_empty_ink(obj, alpha):
    """Drop whole invisible primitives with a two-texel filtering border."""
    mesh=obj.data
    uv=mesh.uv_layers.active.data
    height,width=alpha.shape
    empty=[]
    for p in mesh.polygons:
        coords=[uv[i].uv for i in p.loop_indices]
        x0=max(0,floor(min(u.x for u in coords)*width)-2)
        x1=min(width,ceil(max(u.x for u in coords)*width)+2)
        y0=max(0,floor(min(u.y for u in coords)*height)-2)
        y1=min(height,ceil(max(u.y for u in coords)*height)+2)
        if not alpha[y0:y1,x0:x1].any():
            empty.append(p.index)
    if not empty or len(empty)==len(mesh.polygons):
        return
    # Face patches have authored split normals. Preserve those per loop after
    # removing unused faces; neighboring polygons often share a position.
    old_normals={(tuple(mesh.vertices[l.vertex_index].co),tuple(uv[l.index].uv)):
                 tuple(mesh.corner_normals[l.index].vector) for l in mesh.loops}
    bm=bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[bm.faces[i] for i in empty],context='FACES')
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.update()
    uv=mesh.uv_layers.active.data
    mesh.normals_split_custom_set([old_normals[(tuple(mesh.vertices[l.vertex_index].co),
                                                tuple(uv[l.index].uv))] for l in mesh.loops])


def optimize_export(api):
    width,height=api.atlas.size
    pixels=np.empty(width*height*4,dtype=np.float32)
    api.atlas.pixels.foreach_get(pixels)
    alpha=pixels.reshape((height,width,4))[:,:,3]
    for slot, collection in api.parts.items():
        for obj in collection.objects:
            name=obj.name
            nv=len(obj.data.vertices)
            if obj.data.uv_layers and obj.data.materials[0]==api.material('Face ink'):
                trim_empty_ink(obj,alpha)
            elif name=='Head • cheek and jaw':
                simplify_back_of_head(obj)
            elif slot=='Hair' and 'Nape and underlayer' not in name and 'Crown' not in name:
                # The fourth vertex is behind the scalp on every lock section.
                # Closing the underside directly between side edges preserves
                # its outer crest and silhouette, even on a detached hair slot.
                weld(obj,[(i+3,i) for i in range(0,nv-1,4)])
            elif name=='Torso and neck':
                weld(obj,columns(range(nv//8),8,[(3,4),(5,4)]))
            elif name.startswith(('Braided drawcord','Drawcord aglet')):
                # Preserve the frontal ridge and both side extrema of the
                # narrow cord. Its fourth edge faces the fleece.
                weld(obj,columns(range(nv//4),4,[(1,0)]))
            elif name.startswith(('Backpack shell','Front zip pocket')):
                weld(obj,columns(range(nv//8),8,[(1,0),(7,0)]))
            elif name.startswith('Puff sleeve and violet cuff'):
                # Keep the cuff and outer arm. The medial sleeve lies against
                # the fleece and can share vertices through the shoulder.
                medial=6 if name.endswith('L') else 2
                weld(obj,columns(range(4,nv//8),8,[(medial-1,medial),(medial+1,medial)]))
            elif name=='Classic fleece':
                weld(obj,columns(range(nv//12),12,[(5,6),(7,6)]))
            elif name.startswith('Folded sock'):
                weld(obj,columns([0],8,[(1,0),(3,4),(5,4),(7,0)]))
            elif name.startswith('Leg •'):
                weld(obj,columns([0,nv//8-1],8,[(1,0),(3,4),(5,4),(7,0)]))
            elif name.startswith('Ear •'):
                # Only collapse rear-side edges; the ear relief decal is
                # projected onto the forward-facing facets of this object.
                pairs=[]
                for row in range(3):
                    ring=list(obj.data.vertices)[1+row*14:1+(row+1)*14]
                    cy=sum(v.co.y for v in ring)/len(ring)
                    for i in (1,3,5,7,9,11,13):
                        src,dst=ring[i],ring[(i+1)%14]
                        if min(src.co.y,dst.co.y)>cy+.005:
                            pairs.append((src.index,dst.index))
                weld(obj,pairs)
            elif name.startswith(('Wrist •','Palm •')):
                sides=6 if name.startswith('Wrist') else 8
                weld(obj,columns(range((nv-2)//sides),sides,[(1,2),(sides-1,0)],offset=1))
            elif slot.split('.')[0] in {'Thumb','Index','Middle','Ring','Pinky'}:
                # One edge from each ring lies on the palm-facing side.
                weld(obj,[(2,3),(7,8)])
