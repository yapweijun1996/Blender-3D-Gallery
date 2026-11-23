"""Write indexed, texture-free glTF 2.0 from the reduced geometry."""
import json
import struct
from pathlib import Path

from geometry import bounds
from mathutils import Vector

SURFACES = {
    'paint': (.37, .15, (1,1,1)),
    'glass': (.23, .05, (1,1,1)),
    'tire': (.44, .2, (1,1,1)),
    'light': (.28, 0, (1,1,1)),
    'trim': (.45, .18, (1,1,1)),
    'wall': (.61, .05, (1,1,1)),
    'roof': (.55, .05, (1,1,1)),
    'window': (.23, .05, (1,1,1)),
    'metal': (.4, .35, (1,1,1)),
    'concrete': (.82, 0, (1,1,1)),
    'chrome': (.25, .70, (1,1,1)),
    'plate': (.56, .06, (1,1,1)),
    'rubber': (.67, 0, (1,1,1)),
    'seat': (.49, 0, (1,1,1)),
    'screen': (.33, 0, (1,1,1)),
}

def axis(vector):
    x,y,z = vector
    return (x,z,-y)

class GLB:
    def __init__(self):
        self.bin = bytearray()
        self.doc = {'asset':{'version':'2.0','generator':'MRT kit from Blender 5.1 gallery exports'},
                    'scene':0,'scenes':[{'nodes':[]}],'nodes':[],'meshes':[],
                    'materials':[],'accessors':[],'bufferViews':[]}
        self.materials = {}
        self.paint_base = (1,1,1,1)

    def material(self, name, transparent=False):
        key = (name, transparent)
        if key not in self.materials:
            rough,metal,base = SURFACES[name]
            mat = {'name':name,'pbrMetallicRoughness':{
                'baseColorFactor':self.paint_base if name=='paint' else [*base,1],'metallicFactor':metal,'roughnessFactor':rough}}
            if name in ('glass','window') or transparent:
                mat.update(alphaMode='BLEND',doubleSided=True)
            if name == 'light':
                mat['emissiveFactor'] = [.08,.08,.08]
            self.materials[key] = len(self.doc['materials'])
            self.doc['materials'].append(mat)
        return self.materials[key]

    def accessor(self, items, kind, component, fmt, target, limits=False, normalized=False):
        self.bin.extend(b'\0'*(-len(self.bin)%4))
        payload = b''.join(struct.pack('<'+fmt,*item) for item in items)
        view = {'buffer':0,'byteOffset':len(self.bin),'byteLength':len(payload),'target':target}
        self.bin.extend(payload)
        accessor = {'bufferView':len(self.doc['bufferViews']),'componentType':component,
                    'count':len(items),'type':kind}
        self.doc['bufferViews'].append(view)
        if limits:
            columns = list(zip(*items))
            accessor.update(min=[min(c) for c in columns],max=[max(c) for c in columns])
        if normalized:
            accessor['normalized'] = True
        self.doc['accessors'].append(accessor)
        return len(self.doc['accessors'])-1

    def primitive(self, triangles, pivot, material, transparent):
        vertices, indices = {}, []
        for tri in triangles:
            for p,n,c in tri:
                pos = tuple(struct.unpack('<3f',struct.pack('<3f',*axis(p-pivot))))
                normal = tuple(round(a,6) for a in axis(n.normalized()))
                # 16-bit normalized linear colors retain the dark transit blues.
                color = tuple(round(max(0,min(1,a))*65535) for a in c)
                key = (pos,normal,color)
                if key not in vertices:
                    vertices[key] = len(vertices)
                indices.append((vertices[key],))
        p,n,c = list(zip(*vertices))
        attrs = {
            'POSITION':self.accessor(p,'VEC3',5126,'3f',34962,limits=True),
            'NORMAL':self.accessor(n,'VEC3',5126,'3f',34962),
        }
        if material != 'paint':
            attrs['COLOR_0'] = self.accessor(c,'VEC4',5123,'4H',34962,normalized=True)
        return {'attributes':attrs,'indices':self.accessor(indices,'SCALAR',5123,'H',34963),
                'material':self.material(material,transparent)}

    def write(self, model, path):
        lo,hi = bounds(v[0] for mesh in model.meshes.values() for tris in mesh.values() for tri in tris for v in tri)
        origin = Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
        paint_colors = {v[2] for mesh in model.meshes.values() for tri in mesh.get('paint',()) for v in tri}
        if paint_colors:
            assert len(paint_colors)==1, 'Tintable paint must be a uniform base factor'
            self.paint_base, = paint_colors
        transparent = {name for mesh in model.meshes.values() for name,tris in mesh.items()
                       if any(v[2][3]<1 for tri in tris for v in tri)}
        for group in sorted(model.meshes, key=lambda name:(name!='body',name)):
            mesh = model.meshes[group]
            pivot = origin if group=='body' else model.pivots[group]
            node = {'name':group,'mesh':len(self.doc['meshes'])}
            if group != 'body':
                node['translation'] = axis(pivot-origin)
            if group in model.moves:
                node['extras'] = {'openTranslationMeters':axis(model.moves[group])}
            self.doc['scenes'][0]['nodes'].append(len(self.doc['nodes']))
            self.doc['nodes'].append(node)
            self.doc['meshes'].append({'name':group,'primitives':[
                self.primitive(triangles,pivot,name,name in transparent)
                for name,triangles in sorted(mesh.items())]})
        self.bin.extend(b'\0'*(-len(self.bin)%4))
        self.doc['buffers'] = [{'byteLength':len(self.bin)}]
        payload = json.dumps(self.doc,separators=(',',':')).encode()
        payload += b' '*(-len(payload)%4)
        header = struct.pack('<III',0x46546c67,2,28+len(payload)+len(self.bin))
        Path(path).write_bytes(header+struct.pack('<I4s',len(payload),b'JSON')+payload+
                               struct.pack('<I4s',len(self.bin),b'BIN\0')+self.bin)
        return tuple(origin)
