"""GLB packaging and Blender scene helpers for the male module build."""
from copy import deepcopy
import json
from pathlib import Path
import struct
import tempfile

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
MALE = HERE.parent
PARTS = MALE.parents[1]
STUDIO = PARTS / 'studio-modules/body-male/work'
NEUTRAL = PARTS / 'master/GJH_Chibi_Master_rigged.blend'
MASTER = MALE / 'master_male.blend'
MOTION = MALE / 'round2/motion_male_fixed.glb'
LEGACY = ('idle','walk','run','wave','jump','nod','dance')
ACTIONS = ('sit_down','sit_idle','stand_up','hold_item')
CARRY = ('hold_box','hold_bag','take_item')
CLIPS = LEGACY + ACTIONS + CARRY
BANKS = (PARTS/'body-fix/motion_fixed.glb', PARTS/'actions-fix/actions_fixed.glb',
         PARTS/'actions-hold2/hold_actions.glb')
DTYPES = {5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
WIDTHS = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}


class GLB:
    def __init__(self, path):
        self.path = Path(path)
        raw = self.path.read_bytes()
        size, = struct.unpack_from('<I', raw, 12)
        self.doc = json.loads(raw[20:20+size])
        self.binary = raw[28+size:]
        self.nodes = self.doc['nodes']
        self.ids = {n['name']:i for i,n in enumerate(self.nodes)
                    if n.get('name','').startswith('mixamorig:')}
        self.parents = {child:i for i,node in enumerate(self.nodes) for child in node.get('children',())}

    def accessor(self, idx):
        a = self.doc['accessors'][idx]
        v = self.doc['bufferViews'][a['bufferView']]
        dt = np.dtype(DTYPES[a['componentType']])
        width = WIDTHS[a['type']]
        start = v.get('byteOffset',0) + a.get('byteOffset',0)
        return np.ndarray((a['count'],width), dt, self.binary, start,
                          strides=(v.get('byteStride',width*dt.itemsize),dt.itemsize))

    def view(self, idx):
        view = self.doc['bufferViews'][idx]
        start = view.get('byteOffset', 0)
        return self.binary[start:start+view['byteLength']]


class Writer:
    def __init__(self, doc):
        self.doc = doc
        self.binary = bytearray()
        self.doc['buffers'] = [{}]
        self.doc['bufferViews'] = []

    def add_view(self, content, extra=None):
        self.binary.extend(b'\0'*(-len(self.binary)%4))
        view = dict(extra or {}, buffer=0,byteOffset=len(self.binary),byteLength=len(content))
        self.doc['bufferViews'].append(view)
        self.binary.extend(content)
        return len(self.doc['bufferViews'])-1

    def accessor(self, values, kind, bounds=False):
        a = np.asarray(values, dtype='<f4').reshape(-1,WIDTHS[kind])
        idx = self.add_view(a.tobytes())
        descriptor = dict(bufferView=idx,componentType=5126,count=len(a),type=kind)
        if bounds:
            descriptor.update(min=a.min(axis=0).tolist(), max=a.max(axis=0).tolist())
        self.doc.setdefault('accessors',[]).append(descriptor)
        return len(self.doc['accessors'])-1

    def write(self, path):
        self.binary.extend(b'\0'*(-len(self.binary)%4))
        self.doc['buffers'][0]['byteLength'] = len(self.binary)
        js = json.dumps(self.doc,separators=(',',':')).encode()
        js += b' '*(-len(js)%4)
        header = struct.pack('<4sIIII',b'glTF',2,28+len(js)+len(self.binary),len(js),0x4e4f534a)
        path.write_bytes(header + js + struct.pack('<I4s',len(self.binary),b'BIN\0') + self.binary)


def transcode(source, destination, color_size, data_size):
    """Keep geometry and graph bytes intact and repack resized embedded textures."""
    doc = deepcopy(source.doc)
    if not doc.get('images'):
        destination.write_bytes(source.path.read_bytes())
        return
    base = {doc['textures'][m['pbrMetallicRoughness']['baseColorTexture']['index']]['source']
            for m in doc['materials'] if 'baseColorTexture' in m.get('pbrMetallicRoughness',{})}
    alpha = {doc['textures'][m['pbrMetallicRoughness']['baseColorTexture']['index']]['source']
             for m in doc['materials'] if m.get('alphaMode','OPAQUE')!='OPAQUE'
             and 'baseColorTexture' in m.get('pbrMetallicRoughness',{})}
    pack = Writer(doc)
    image_ids = {image['bufferView']:i for i,image in enumerate(doc['images'])}
    with tempfile.TemporaryDirectory(dir=HERE/'.runtime') as temp:
        for i, view in enumerate(source.doc['bufferViews']):
            blob = source.view(i)
            if i in image_ids:
                j = image_ids[i]
                dst = doc['images'][j]
                origin = Path(temp)/('in.jpg' if dst['mimeType']=='image/jpeg' else 'in.png')
                origin.write_bytes(blob)
                image = bpy.data.images.load(str(origin), check_existing=False)
                if j not in base:
                    image.colorspace_settings.name = 'Non-Color'
                cap = color_size if j in base else data_size
                w,h = image.size
                scale = min(1,cap/max(w,h))
                if scale < 1:
                    image.scale(round(w*scale),round(h*scale))
                if scale < 1 or (j in base and j not in alpha and dst['mimeType']!='image/jpeg'):
                    fmt = 'JPEG' if j in base and j not in alpha else 'PNG'
                    target = Path(temp)/('out.jpg' if fmt=='JPEG' else 'out.png')
                    image.file_format = fmt
                    image.save(filepath=str(target))
                    blob = target.read_bytes()
                    dst['mimeType'] = 'image/jpeg' if fmt=='JPEG' else 'image/png'
                bpy.data.images.remove(image)
            extra = {k:v for k,v in view.items() if k not in ('buffer','byteOffset','byteLength')}
            assert pack.add_view(blob,extra)==i
    pack.write(destination)


def import_objects(path, **kwargs):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), **kwargs)
    return set(bpy.context.scene.objects) - before


def write_json(path, value):
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(value,indent=2)+'\n')
    temp.replace(path)
