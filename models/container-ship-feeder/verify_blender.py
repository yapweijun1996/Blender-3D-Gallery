"""Check GLB container, binary accessors, and Blender reimported geometry."""
import bpy, math, json, struct, hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
slug=D.name
expected={'container-ship-feeder':(170,27,9,9),'oil-tanker-aframax':(245,42,13,11),'bulk-carrier-handymax':(190,32,10,10),'harbour-tug':(32,11,3.5,3)}
L,B,draft,free=expected[slug]
p=D/'exports'/(slug+'.glb'); b=p.read_bytes()
assert len(b)<=2000000 and b[:4]==b'glTF'
magic,version,total=struct.unpack_from('<4sII',b);assert version==2 and total==len(b)
jlen,jkind=struct.unpack_from('<I4s',b,12);assert jkind==b'JSON'
g=json.loads(b[20:20+jlen]); assert g['asset']['version']=='2.0'
offset=20+jlen; blen,bkind=struct.unpack_from('<I4s',b,offset); assert bkind==b'BIN\x00' and offset+8+blen==len(b)
binbuf=b[offset+8:]; assert len(g['buffers'])==1 and not g['buffers'][0].get('uri') and g['buffers'][0]['byteLength']<=len(binbuf)
assert not g.get('extensionsRequired')
assert g.get('images') and all(image.get('mimeType')=='image/png' and 'bufferView' in image and 'uri' not in image for image in g['images'])
for image in g['images']:
    view=g['bufferViews'][image['bufferView']]; start=view.get('byteOffset',0)
    png=binbuf[start:start+view['byteLength']]
    assert png[:8]==b'\x89PNG\r\n\x1a\n'
    width,height=struct.unpack_from('>II',png,16)
    assert 0<width<=1024 and 0<height<=1024
assert any('baseColorTexture' in m.get('pbrMetallicRoughness',{}) and 'metallicRoughnessTexture' in m.get('pbrMetallicRoughness',{}) for m in g['materials'])
formats={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}
components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}
def values(index):
    a=g['accessors'][index]; v=g['bufferViews'][a['bufferView']]; code,size=formats[a['componentType']]; n=components[a['type']]
    start=v.get('byteOffset',0)+a.get('byteOffset',0); stride=v.get('byteStride',size*n)
    assert v.get('buffer',0)==0 and stride>=size*n and start>=v.get('byteOffset',0)
    assert start+(a['count']-1)*stride+size*n<=v.get('byteOffset',0)+v['byteLength']<=len(binbuf)
    return [struct.unpack_from('<'+code*n,binbuf,start+i*stride) for i in range(a['count'])]
# Inspect untransformed glTF coordinates independently of Blender's importer.
node=next(n for n in g['nodes'] if n.get('name')=='upper hull')
assert not any(k in node for k in ('matrix','translation','rotation','scale'))
hull_mesh=g['meshes'][node['mesh']]
gltf_positions=[v for primitive in hull_mesh['primitives'] for v in values(primitive['attributes']['POSITION'])]
assert abs(min(v[0] for v in gltf_positions)+L/2)<.01 and abs(max(v[0] for v in gltf_positions)-L/2)<.01
assert any(abs(v[1]-free)<.01 and abs(abs(v[2])-B/2)<.01 for v in gltf_positions)
# The pointed end is +X, rather than merely an axis-symmetric bounding box.
bow=max(abs(v[2]) for v in gltf_positions if abs(v[0]-L/2)<.01)
stern=max(abs(v[2]) for v in gltf_positions if abs(v[0]+L/2)<.01)
assert bow<stern
triangles=0
for m in g['meshes']:
    for prim in m['primitives']:
        assert prim.get('mode',4)==4
        pos=values(prim['attributes']['POSITION']); assert all(math.isfinite(v) for row in pos for v in row)
        idx=values(prim['indices']); assert len(idx)%3==0 and all(0<=v[0]<len(pos) for v in idx)
        for key,accessor in prim['attributes'].items():
            v=values(accessor);assert len(v)==len(pos) and all(math.isfinite(x) for row in v for x in row),key
        triangles+=len(idx)//3
assert triangles<=40000
# The GLB is imported with Blender's glTF loader, and inspected in original Z-up space.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(p))
objs=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert objs
assert not any(o.type in {'LIGHT','CAMERA'} for o in bpy.context.scene.objects)
hull=bpy.data.objects['upper hull']; low=bpy.data.objects['red hull']
def bounds(o):
    vs=[o.matrix_world@v.co for v in o.data.vertices]
    return [[min(v[i] for v in vs),max(v[i] for v in vs)] for i in range(3)]
h=bounds(hull); lo=bounds(low)
assert abs(h[0][0]+L/2)<.01 and abs(h[0][1]-L/2)<.01,h
assert abs((h[1][1]-h[1][0])-B)<.01,h
assert abs(lo[2][0]+draft)<.01 and any(abs((hull.matrix_world@v.co).z-free)<.01 and abs(abs((hull.matrix_world@v.co).y)-B/2)<.01 for v in hull.data.vertices),(lo,h)
assert lo[2][0]<0<h[2][1]
for obj in objs:
    obj.data.calc_loop_triangles()
    for t in obj.data.loop_triangles:
        a,c,d=[obj.data.vertices[i].co for i in t.vertices]
        assert (c-a).cross(d-a).length>1e-9, (obj.name,t.index)
print('CHECK_RESULT '+json.dumps({'slug':slug,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'triangles':triangles,'meshes':len(g['meshes']),'hull_bounds_blender_m':h,'draft_m':draft,'freeboard_m':free,'blender_reimport':'PASS','binary_structure':'PASS','degenerate_triangles':0}))
