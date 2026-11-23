"""Derive drive-demo LODs from the editable, shipped gallery vehicle scenes."""
from collections import defaultdict
from dataclasses import dataclass
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT.parents[2] / 'models'
MODELS = {
    'car_saga': ('proton-saga-1985/scene.blend', 'ASSET_Proton_Saga_1985', 4.1, 5500),
    'car_hatchback_hd': ('hatchback-car/sources/hatchback-car.blend', 'ASSET_HatchbackCar', 4.0, 4500),
    'motorbike_hd': ('motorcycle/sources/motorcycle.blend', 'ASSET_Motorcycle', 2.0, 2200),
}
CATEGORIES = ('paint', 'glass', 'light', 'trim', 'metal', 'chrome', 'plate', 'tire')


@dataclass
class Part:
    name: str
    vertices: list
    faces: list
    styles: list
    smooth: list

    @property
    def triangles(self):
        return sum(len(f)-2 for f in self.faces)


def shader_of(material):
    return next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')


def category(name, material, is_wheel):
    if is_wheel:
        return 'tire' if any(k in material for k in ('Black', 'Rubber', 'Tire')) else 'metal'
    if 'paint' in material or material in ('Silver metallic body', 'Motorcycle burnt orange'):
        return 'paint'
    if material in ('Neutral smoky glazing', 'Clear glass alpha', 'Glazing blue-grey'):
        return 'glass'
    if name.startswith(('HEADLIGHT', 'TAIL_Light')) or any(k in material for k in (
        'headlamp', 'lens', 'reflector', 'prism',
    )):
        return 'light'
    if name.startswith('PLATE') or 'plate' in material.lower():
        return 'plate'
    if material == 'Polished narrow trim' and not name.startswith('Heritage'):
        return 'chrome'
    if material in ('Steel', 'Satin pressed steel'):
        return 'metal'
    return 'trim'


class Appearance:
    def __init__(self, asset):
        self.asset = asset
        self.materials = {}
        self.images = {}
        self.properties = {
            'car_saga': {
                'paint': (.72, .26, (.36,.385,.41), 1),
                'glass': (0, .10, (.022,.028,.034), .36),
                'trim': (0, .63, (1,1,1), 1),
                'metal': (.72, .31, (1,1,1), 1),
                'chrome': (.85, .22, (1,1,1), 1),
                'plate': (.03, .48, (1,1,1), 1),
                'tire': (0, .88, (1,1,1), 1),
                'light': (.045, .30, (1,1,1), 1),
            },
            'car_hatchback_hd': {
                'paint': (.35, .28, (.013411749,.178867504,.187316671), 1),
                'glass': (0, .20, (.263273418,.538235545,.638283193), .18),
                'trim': (0, .45, (1,1,1), 1),
                'metal': (.52, .45, (1,1,1), 1),
                'plate': (0, .45, (1,1,1), 1),
                'tire': (0, .45, (1,1,1), 1),
                'light': (0, .45, (1,1,1), 1),
            },
            'motorbike_hd': {
                'paint': (.25, .30, (.380056322,.033104766,.004400850), 1),
                'glass': (.20, .18, (.154872492,.393123120,.491905034), 1),
                'trim': (0, .45, (1,1,1), 1),
                'metal': (.65, .45, (1,1,1), 1),
                'tire': (0, .45, (1,1,1), 1),
                'light': (0, .45, (1,1,1), 1),
            },
        }[asset]

    def make(self, key):
        if key in self.materials:
            return self.materials[key]
        if key in bpy.data.materials:
            bpy.data.materials[key].name = '_source_' + key
        material = bpy.data.materials.new(key)
        material.use_nodes = True
        shader = shader_of(material)
        metallic, rough, rgb, alpha = self.properties[key]
        shader.inputs['Base Color'].default_value = (*rgb, 1)
        shader.inputs['Metallic'].default_value = metallic
        shader.inputs['Roughness'].default_value = rough
        shader.inputs['Alpha'].default_value = alpha
        material.diffuse_color = (*rgb, alpha)
        if self.asset == 'car_saga' and key in ('trim', 'glass'):
            shader.inputs['Specular IOR Level'].default_value = .10 if key == 'glass' else .15
        if alpha < 1:
            material.surface_render_method = 'BLENDED'
        if key not in ('paint', 'glass'):
            baked = material.node_tree.nodes.new('ShaderNodeVertexColor')
            baked.layer_name = 'BakedColor'
            material.node_tree.links.new(baked.outputs['Color'], shader.inputs['Base Color'])
        if key == 'light':
            shader.inputs['Emission Color'].default_value = (.55, .50, .43, 1)
            shader.inputs['Emission Strength'].default_value = .016
        self.materials[key] = material
        return material

    def sample(self, image, uv):
        if image.name not in self.images:
            w, h = image.size
            pixels = np.empty(w*h*4, dtype=np.float32)
            image.pixels.foreach_get(pixels)
            self.images[image.name] = pixels.reshape(h,w,4)
        pixels = self.images[image.name]
        h,w,_ = pixels.shape
        x, y = np.clip(uv, 0, 1) * (w-1, h-1)
        i,j = int(x),int(y)
        f,g = x-i,y-j
        value = ((1-f)*(1-g)*pixels[j,i] + f*(1-g)*pixels[j,min(w-1,i+1)]
                 + (1-f)*g*pixels[min(h-1,j+1),i] + f*g*pixels[min(h-1,j+1),min(w-1,i+1)])
        return tuple(float(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4) for c in value[:3])

    def style(self, name, material, wheel):
        key = category(name, material.name, wheel)
        rgb = tuple(shader_of(material).inputs['Base Color'].default_value[:3])
        if key in ('paint', 'glass'):
            rgb = (1,1,1)
        if self.asset == 'car_hatchback_hd' and wheel and material.name == 'Ivory':
            rgb = (.86,.88,.87)
        return key, rgb


def get_part(obj, mesh, appearance, wheel):
    verts = [obj.matrix_world @ v.co for v in mesh.vertices]
    styles, faces, smooth = [], [], []
    material_styles = [appearance.style(obj.name, mat, wheel) for mat in mesh.materials]
    images = [next((node.image for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE'), None)
              for mat in mesh.materials]
    uv = mesh.uv_layers.active
    for face in mesh.polygons:
        faces.append(tuple(face.vertices))
        key, rgb = material_styles[face.material_index]
        img = images[face.material_index]
        if img and uv:
            cols = tuple(appearance.sample(img, uv.data[i].uv) for i in face.loop_indices)
        else:
            cols = (rgb,) * len(face.vertices)
        styles.append((key, cols))
        smooth.append(face.use_smooth)
    return Part(obj.name, verts, faces, styles, smooth)


def uniform(obj, vertices, faces, smooth, appearance, wheel, material=None):
    key, rgb = appearance.style(obj.name, material or obj.data.materials[0], wheel)
    return Part(obj.name, vertices, faces, [(key, (rgb,)*len(f)) for f in faces], smooth)


def round_source(obj, segments, appearance, wheel):
    """Sample the original extruded cap contour in local coordinates."""
    rings = defaultdict(list)
    for vert in obj.data.vertices:
        rings[round(vert.co.z, 6)].append(vert.co.copy())
    if len(rings) != 2 or len({len(ring) for ring in rings.values()}) != 1:
        return None
    rings = [rings[z] for z in sorted(rings)]
    if len(rings[0]) < segments:
        return None
    radius_x = max(abs(v.x) for v in rings[0])
    radius_y = max(abs(v.y) for v in rings[0])
    if min(radius_x, radius_y) <= 0:
        return None
    vertices = []
    for ring in rings:
        ring.sort(key=lambda v: (math.atan2(v.y/radius_y,v.x/radius_x)+math.tau+.00001)%math.tau)
        vertices.extend(obj.matrix_world @ ring[round(i*len(ring)/segments)] for i in range(segments))
    faces = [tuple(reversed(range(segments))), tuple(range(segments,2*segments))]
    faces.extend((j,(j+1)%segments,(j+1)%segments+segments,j+segments) for j in range(segments))
    return uniform(obj, vertices, faces, [False,False]+[True]*segments, appearance, wheel)


def revolve(obj, profiles, segments, appearance, wheel, local_axis='Z', closed=True, material=None):
    """Rebuild rings from sampled source positions, around the original axle."""
    verts = []
    for radius, offset in profiles:
        for i in range(segments):
            a = math.tau*i/segments
            p = (radius*math.cos(a), radius*math.sin(a), offset) if local_axis == 'Z' else (
                radius*math.sin(a), offset, radius*math.cos(a))
            verts.append(obj.matrix_world @ Vector(p) if local_axis == 'Z' else wheel[1]+Vector(p))
    faces = []
    for j in range(len(profiles) if closed else len(profiles)-1):
        for i in range(segments):
            next_ring = (j+1)%len(profiles)
            face = (j*segments+i, j*segments+(i+1)%segments,
                    next_ring*segments+(i+1)%segments, next_ring*segments+i)
            faces.append(face)
    if not closed:
        last = (len(profiles)-1)*segments
        faces += [tuple(range(segments-1,-1,-1)), tuple(range(last,last+segments))]
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for face in faces:
        bm.faces.new([vs[i] for i in face])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.verts.index_update()
    faces = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    smooth = [True]*len(faces)
    if not closed:
        smooth[-2:] = [False,False]
    return uniform(obj, verts, faces, smooth, appearance, wheel, material)


def torus(obj, segments, num_profile, appearance, wheel):
    profile = sorted({(round(math.hypot(v.co.x,v.co.y),5),round(v.co.z,5))
                      for v in obj.data.vertices})
    radius = (min(p[0] for p in profile)+max(p[0] for p in profile))/2
    profile.sort(key=lambda p: (math.atan2(p[1],p[0]-radius)+math.tau+.00001)%math.tau)
    samples = [profile[round(i*len(profile)/num_profile)] for i in range(num_profile)]
    return revolve(obj, samples, segments, appearance, wheel)


def saga_ring(obj, profile_rows, segments, appearance, wheel, closed=True):
    midpoint = wheel[1]
    samples = []
    row_size = len(obj.data.vertices) // (12 if obj.name.startswith('High profile') else 9)
    for index in profile_rows:
        point = obj.matrix_world @ obj.data.vertices[index*row_size].co - midpoint
        samples.append((math.hypot(point.x,point.z),point.y))
    if not closed:
        samples[0] = (samples[1][0],samples[0][1])
        samples[-1] = (samples[-2][0],samples[-1][1])
    return revolve(obj,samples,segments,appearance,wheel,'X',closed)


def saga_rim(obj,appearance,wheel):
    # Source profile and 12 punched vents in the named rim from generate.py.
    # Only the exterior faces can be seen between the tire and hubcap.
    side = math.copysign(1,wheel[1].y)
    front = [(r*.90,t*side) for r,t in ((.125,.058),(.158,.057),(.190,.075))]
    rim = revolve(obj,front,20,appearance,wheel,'X',closed=False)
    rim.faces = rim.faces[:-2]
    rim.styles = rim.styles[:-2]
    rim.smooth = rim.smooth[:-2]
    for i in range(12):
        a = math.tau*i/12
        radial = Vector((math.sin(a),0,math.cos(a)))
        tangential = Vector((math.cos(a),0,-math.sin(a)))
        center = wheel[1]+.160*.90*radial+Vector((0,side*.062,0))
        points = [center + radial*d + tangential*t for d,t in (
            (-.006,-.011), (.005,-.011), (.005,.011), (-.006,.011),
        )]
        first = len(rim.vertices)
        rim.vertices.extend(points)
        rim.faces.append(tuple(range(first,first+4)))
        rim.styles.append(('metal',((.035,.039,.044),)*4))
        rim.smooth.append(False)
    return rim


def saga_cover(obj,appearance,wheel):
    center = wheel[1]
    num = len(obj.data.vertices)//9
    profiles = []
    for row in (4,7,8):
        p = obj.matrix_world @ obj.data.vertices[row*num].co - center
        profiles.append((math.hypot(p.x,p.z),p.y))
    side = math.copysign(1,center.y)
    count = 20
    verts = [center+Vector((0,profiles[-1][1],0))]
    for r,x in reversed(profiles[:-1]):
        verts += [center+Vector((r*math.sin(math.tau*i/count),x,r*math.cos(math.tau*i/count)))
                  for i in range(count)]
    faces = [(0,1+i,1+(i+1)%count) for i in range(count)]
    faces += [(1+i,1+i+count,1+(i+1)%count+count,1+(i+1)%count) for i in range(count)]
    if side<0:
        faces = [tuple(reversed(f)) for f in faces]
    return uniform(obj,verts,faces,[True]*len(faces),appearance,wheel)


def glaze(obj,appearance):
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    ring_count = 4
    count = (len(verts)-1)//ring_count
    outline = verts[-count:]
    points = [outline[j] for j in range(count) if j%6 in (0,5)]
    count = len(points)
    normal = Vector()
    for i in range(count):
        normal += (points[i]-verts[0]).cross(points[(i+1)%count]-verts[0])
    normal.normalize()
    vertices = [verts[0],*points]
    faces = [(0,1+i,1+(i+1)%count) for i in range(count)]
    part = uniform(obj,vertices,faces,[True]*count,appearance,None)
    miters = []
    for i,p in enumerate(points):
        prev = (p-points[i-1]).normalized().cross(normal)
        after = (points[(i+1)%count]-p).normalized().cross(normal)
        miter = (prev+after).normalized()
        miters.append(miter/max(.45,miter.dot(after)))
    loops = []
    # Use the original glazing edges as the datum for the dark seal and bright bead.
    for width, depth in ((-.003,.0005),(.005,.0012),(.010,.0014)):
        loops.append(len(part.vertices))
        part.vertices.extend(p+m*width+normal*depth for p,m in zip(points,miters))
    for row,key,rgb in ((0,'trim',(.004,.005,.006)), (1,'chrome',(.52,.55,.57))):
        a,b = loops[row:row+2]
        for i in range(count):
            j = (i+1)%count
            part.faces.append((a+i,b+i,b+j,a+j))
            part.styles.append((key,(rgb,)*4))
            part.smooth.append(False)
    return part


def polyline_ribbon(obj,appearance,path,outward,width):
    vertices = [point + Vector((0,0,height)) for point in path for height in (-width,width)]
    faces = [(j*2,j*2+1,j*2+3,j*2+2) for j in range(len(path)-1)]
    if (vertices[1]-vertices[0]).cross(vertices[3]-vertices[0]).dot(outward) < 0:
        faces = [tuple(reversed(face)) for face in faces]
    return uniform(obj,vertices,faces,[False]*len(faces),appearance,None)


def plate_border(obj,appearance):
    coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    outside = math.copysign(1,sum(p.x for p in coords))
    x = max(p.x*outside for p in coords)*outside
    ys,zs = [p.y for p in coords],[p.z for p in coords]
    y0,y1=min(ys)+.001,max(ys)-.001
    z0,z1=min(zs)+.001,max(zs)-.001
    vertices = []
    for inset in (0,.0025):
        yl,yr,zl,zh = y0+inset,y1-inset,z0+inset,z1-inset
        radius = .010-inset
        vertices.extend(Vector((x,y,z)) for y,z in (
            (yl+radius,zl),(yr-radius,zl),(yr,zl+radius),(yr,zh-radius),
            (yr-radius,zh),(yl+radius,zh),(yl,zh-radius),(yl,zl+radius),
        ))
    faces = [(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
    if outside < 0:
        faces = [tuple(reversed(face)) for face in faces]
    return uniform(obj,vertices,faces,[False]*len(faces),appearance,None)


def bumper_inlay(obj,appearance):
    coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    # Bevel resolution 0 in the source line leaves a four-vertex cross-section
    # per path station. Its exact centerline can be used as a two-face ribbon.
    if len(coords)%4:
        return simplify(get_part(obj,obj.data,appearance,None),24,5)
    centers = [sum(coords[i:i+4],Vector())/4 for i in range(0,len(coords),4)]
    outward = Vector((math.copysign(1,sum(p.x for p in coords)),0,0))
    return polyline_ribbon(obj,appearance,[p+outward*.001 for p in centers],outward,.0025)


def simplify_path(points, tolerance):
    if len(points) < 3:
        return points
    a,b = points[0],points[-1]
    ab = b-a
    inv_size = 1/ab.length_squared if ab.length_squared else 0
    distances = [(p-a-ab*max(0,min(1,(p-a).dot(ab)*inv_size))).length for p in points[1:-1]]
    idx = max(range(len(distances)),key=distances.__getitem__)
    if distances[idx] <= tolerance:
        return [a,b]
    return simplify_path(points[:idx+2],tolerance)[:-1]+simplify_path(points[idx+1:],tolerance)


def lettering_outline(part, side):
    mesh = bpy.data.meshes.new('_letter_faces')
    mesh.from_pydata(part.vertices, [], part.faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000003)
    bm.verts.index_update()
    boundary = [(edge.verts[0],edge.verts[1]) for edge in bm.edges if edge.is_boundary]
    next_edges = defaultdict(list)
    for a,b in boundary:
        next_edges[a.index].append(b.index)
        next_edges[b.index].append(a.index)
    points = {v.index:v.co.copy() for v in bm.verts}
    contours = []
    while next_edges:
        # Glyph contours are closed cycles after welding the planar caps.
        start = next(iter(next_edges))
        current = start
        loop = [points[start]]
        while current in next_edges:
            other = next_edges[current].pop()
            next_edges[other].remove(current)
            if not next_edges[current]:
                del next_edges[current]
            if not next_edges[other]:
                del next_edges[other]
            if other == start:
                break
            loop.append(points[other])
            current = other
        if len(loop)<3:
            continue
        pivot = max(range(len(loop)),key=lambda j:(loop[j]-loop[0]).length_squared)
        tolerance = .0014 if '(1985)' in part.name else .0011
        contour = simplify_path(loop[:pivot+1],tolerance)[:-1] + simplify_path(loop[pivot:]+[loop[0]],tolerance)[:-1]
        if len(contour) >= 3:
            contours.append(contour)
    bm.free()
    bpy.data.meshes.remove(mesh)
    original = [p for contour in contours for p in contour]
    coordinates = [Vector((p.y,p.z)) for p in original]
    boundary = []
    offset = 0
    for contour in contours:
        boundary.append(list(range(offset,offset+len(contour))))
        offset += len(contour)
    segments = [(loop[i],loop[(i+1)%len(loop)]) for loop in boundary for i in range(len(loop))]
    points, _, triangles, _, _, _ = geometry.delaunay_2d_cdt(coordinates,segments,[],0,1e-7)
    x = sum(p.x for p in original)/len(original)
    verts = [Vector((x,p.x,p.y)) for p in points]
    faces = []
    for face in triangles:
        y,z = sum((points[i] for i in face),Vector((0,0)))/3
        crossing = 0
        for i,j in segments:
            y0,z0 = coordinates[i]
            y1,z1 = coordinates[j]
            if (z0 > z) != (z1 > z) and y < y0+(y1-y0)*(z-z0)/(z1-z0):
                crossing += 1
        if crossing%2 == 0:
            continue
        a,b,c = [verts[i] for i in face]
        cross = (b-a).cross(c-a).x
        if abs(cross) > 1e-10:
            faces.append(tuple(face if cross*side>0 else reversed(face)))
    key,rgb = part.styles[0][0],part.styles[0][1][0]
    return Part(part.name,verts,faces,[(key,(rgb,)*3)]*len(faces),[False]*len(faces))



def source_uv(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    faces = [tuple(t.vertices) for t in mesh.loop_triangles]
    uv = [tuple(mesh.uv_layers.active.data[i].uv.copy() for i in t.loops) for t in mesh.loop_triangles]
    return points,faces,uv,BVHTree.FromPolygons(points,faces,all_triangles=True)


def headlamp_bake(obj,appearance):
    points,faces,uv,tree = source_uv(obj)
    y_lo,y_hi = min(p.y for p in points),max(p.y for p in points)
    z_lo,z_hi = min(p.z for p in points),max(p.z for p in points)
    image = next(n.image for n in obj.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE')
    x_front = min(p.x for p in points)-.1
    verts, cols = [], []
    ny,nz = 14,4
    for j in range(nz+1):
        z = z_lo+(z_hi-z_lo)*j/nz
        # The lamp narrows towards its upper corners in the source.
        edge = .001+(z-z_lo)*.079
        for i in range(ny+1):
            y = y_lo+edge+(y_hi-y_lo-2*edge)*i/ny
            p,n,index,_ = tree.ray_cast(Vector((x_front,y,z)),Vector((1,0,0)))
            if p is None:
                p,n,index,_ = tree.find_nearest(Vector((x_front+.10,y,z)))
                p = Vector((p.x,y,z))
            a,b,c = [points[i] for i in faces[index]]
            t0,t1,t2 = [Vector((*t,0)) for t in uv[index]]
            sample_uv = geometry.barycentric_transform(p,a,b,c,t0,t1,t2)
            c = appearance.sample(image,np.array(sample_uv[:2]))
            verts.append(p)
            cols.append(tuple(min(1,max(.012,v)) for v in c))
    out_faces = []
    for j in range(nz):
        for i in range(ny):
            n = j*(ny+1)+i
            out_faces.append((n,n+ny+1,n+ny+2,n+1))
    return Part(obj.name,verts,out_faces,[('light',tuple(cols[i] for i in face)) for face in out_faces],
                [True]*len(out_faces))


def cell_bake(obj,appearance):
    part = get_part(obj,obj.data,appearance,None)
    if obj.name.startswith('Front amber'):
        part.styles = [('light',((.40,.064,.001),)*len(face)) for face in part.faces]
        return part
    # Bake the atlas center and the source lens pigment into four facets.
    pigment = tuple(shader_of(obj.data.materials[0]).inputs['Base Color'].default_value[:3])
    mesh = obj.data
    f = next(f for f in mesh.polygons if f.material_index == 1)
    uv_layer = mesh.uv_layers.active
    average = sum((uv_layer.data[k].uv for k in f.loop_indices),Vector((0,0))) / len(f.loop_indices)
    image = next(n.image for n in mesh.materials[f.material_index].node_tree.nodes if n.type=='TEX_IMAGE')
    color = appearance.sample(image, np.array(average))
    baked = tuple(.74*a+.26*b for a,b in zip(pigment,color))
    boundary = [part.vertices[k] for k in f.vertices]
    center = sum(boundary,Vector()) / len(boundary)
    normal = (boundary[1]-boundary[0]).cross(boundary[2]-boundary[0]).normalized()
    verts = [center+normal*.0006,*boundary]
    n = len(boundary)
    faces = [(0,1+i,1+(i+1)%n) for i in range(n)]
    colors = [tuple(min(1,c*1.40) for c in baked)]
    colors += [tuple(v*(.88 if p.z>center.z else .56) for v in baked) for p in boundary]
    return Part(obj.name,verts,faces,[('light',tuple(colors[i] for i in f)) for f in faces],
                [True]*len(faces))



def simplify(part, target, angle, collapse=True):
    if part.triangles <= target:
        return part
    mesh = bpy.data.meshes.new('_lod_piece')
    mesh.from_pydata(part.vertices, [], part.faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    # A material and shading ID travels with faces through planar and quadric reduction.
    keys = list(dict.fromkeys((key, cols[0], smooth) for (key,cols),smooth in zip(part.styles,part.smooth)))
    index = {key:i for i,key in enumerate(keys)}
    bm.faces.ensure_lookup_table()
    for face, style, smooth in zip(bm.faces, part.styles, part.smooth):
        face.material_index = index[(style[0], style[1][0], smooth)]
        face.smooth = smooth
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.000002)
    bm.normal_update()
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(angle), use_dissolve_boundaries=False,
                             verts=list(bm.verts), edges=list(bm.edges), delimit={'MATERIAL'})
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    for face in list(bm.faces):
        if face.calc_area() < 1e-12:
            bm.faces.remove(face)
    count = len(bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = None
    if count > target and collapse:
        obj = bpy.data.objects.new('_lod_piece', mesh)
        bpy.context.scene.collection.objects.link(obj)
        modifier = obj.modifiers.new('Reduce', 'DECIMATE')
        modifier.ratio = target/count
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        mesh = obj.data
    verts = [v.co.copy() for v in mesh.vertices]
    faces, styles, smooth_flags = [], [], []
    for face in mesh.polygons:
        if face.area < 1e-12:
            continue
        key,rgb,smooth = keys[face.material_index]
        faces.append(tuple(face.vertices))
        styles.append((key,(rgb,)*len(face.vertices)))
        smooth_flags.append(smooth)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return Part(part.name,verts,faces,styles,smooth_flags)


def simplify_spokes(part, segments):
    adjacent = defaultdict(set)
    for face in part.faces:
        for j, i in enumerate(face):
            other = face[(j+1)%len(face)]
            adjacent[i].add(other)
            adjacent[other].add(i)
    remaining = set(adjacent)
    verts,faces,styles,smooth = [],[],[],[]
    material = part.styles[0][0]
    rgb = part.styles[0][1][0]
    while remaining:
        pending = [min(remaining)]
        group = []
        while pending:
            i = pending.pop()
            if i in remaining:
                remaining.remove(i)
                group.append(i)
                pending.extend(adjacent[i])
        points = np.array([part.vertices[i] for i in group])
        center = points.mean(axis=0)
        _,_,axes = np.linalg.svd(points-center,full_matrices=False)
        axis,u,v = axes
        if np.dot(np.cross(u,v),axis) < 0:
            v = -v
        projection = (points-center) @ axis
        radial = points-center-projection[:,None]*axis
        radius = np.linalg.norm(radial,axis=1).max()
        base = len(verts)
        for end in (projection.min(),projection.max()):
            for j in range(segments):
                angle = math.tau*j/segments
                verts.append(Vector(center + end*axis + radius*(math.cos(angle)*u+math.sin(angle)*v)))
        group_faces = [tuple(base+j for j in reversed(range(segments))),
                       tuple(base+j for j in range(segments,2*segments))]
        group_faces.extend((base+j,base+(j+1)%segments,base+(j+1)%segments+segments,base+j+segments)
                           for j in range(segments))
        faces.extend(group_faces)
        styles.extend((material,(rgb,)*len(face)) for face in group_faces)
        smooth.extend([False,False]+[True]*segments)
    return Part(part.name,verts,faces,styles,smooth)



def wheel_owner(obj, asset, rotation):
    current = obj.parent
    while current:
        n = current.name
        if n.startswith('PIVOT_Wheel_') and n.endswith('_Roll'):
            pivot = rotation @ current.matrix_world.translation
            suffix = ('F' if pivot.y < 0 else 'R')+('L' if pivot.x < 0 else 'R')
            return 'wheel_'+suffix, current.matrix_world.translation.copy()
        if n.startswith('ROLL_Wheel'):
            pivot = current.matrix_world.translation.copy()
            suffix = 'F' if pivot.y < 0 else 'R'
            if asset != 'motorbike_hd':
                suffix += 'L' if pivot.x < 0 else 'R'
            return 'wheel_'+suffix, pivot
        current = current.parent
    return None


def saga_rules(name):
    # Interior details hidden by closed doors and subpixel hardware are removed.
    discard = (
        'Tire tread', 'Tire molded', 'Rubber tire valve', 'Dark brake backing',
        'Wheel cover narrow', 'Small wheel cover center', 'Clear molded headlamp cover',
        'Headlamp narrow silver rim', 'Recessed headlamp back', 'Pressed rectangular lamp',
        'Recessed optical bulb', 'Amber front vertical', 'Amber lens horizontal',
        'Seat upholstery stitch', 'woven insert pleat', 'insert stitched piping',
        'armrest stitch', 'interior release lever', 'manual window crank',
        'latch plate', 'hinge leaf', 'body hinge bracket', 'body striker plate',
        'body latch striker', 'interior door pull', 'pocket upper welt',
        'lower interior storage pocket', 'pocket recessed face', 'lower kick panel',
        'washer nozzle', 'Cowl vent slot', 'Steering spoke', 'Folded sun visor',
        'Rearview mirror stalk', 'Intake vertical vane', 'Intake horizontal vane',
        'Door opening upright seal', 'door opening lower seal', 'door opening threshold',
        'Front seat side bolster', 'Dashboard center stack', 'fitted inner door card',
        'woven door insert', 'inner door card upper edge', 'padded upper vinyl rail',
        'interior armrest', 'armrest padded cap', 'Grille recessed vertical support',
        'top rubber bead', 'Headlight horizontal optical flute', ' body hinge pin',
        ' pocket fastening', 'Lock key slot', 'Boot key center', 'Boot key surround', 'Front door lock',
        'Rear glass heating element', 'Wiper pivot', 'Underbody exhaust pipe', 'Exhaust dark bore',
        'Rear center brake lamp housing', 'Steering column', 'Steering hub', 'Gear lever',
        'folded edge', 'structural frame', 'Door handle recess', 'Bonnet panel shutline', 'Boot panel shutline',
        'Rear SAGA lettering', 'Rear proton script', 'Exhaust outlet', ' door lower pressed contour',
        'Rear door upper shutline', 'Front seat cushion', 'Center console',
        'Inner door card', 'Black sill lower seam',

    )
    if any(token in name for token in discard):
        return 0,None
    if name.startswith('Headlight vertical optical flute'):
        return 0,None
    if name.startswith('Image-mapped glass headlamp'):
        return None,'headlamp_bake'
    if name.startswith(('Front amber corner lens','Segmented rear optical cell')):
        return None,'cell_bake'
    if name.startswith(('Heritage shield','Heritage sun')):
        return None,'source'
    if name.startswith(('Front windscreen','Rear screen','Front door window','Rear door window','Fixed rear quarterlight')):
        if 'surround' in name or 'channel' in name:
            return 0,None
        if 'belt ledge' not in name:
            return None,'glazing'
    if 'pillar' in name.lower() and 'reveal' not in name.lower():
        return 18,'evaluated'
    if name.startswith('Registration plate '):
        return 0,'front_lettering'
    if name.startswith('White registration plate border'):
        return None,'plate_border'
    if name.startswith(('Front windscreen','Rear screen')):
        return (35 if 'surround' in name or 'channel' in name else 42),'source'
    if any(token in name for token in ('door window', 'rear quarterlight', 'quarter window belt ledge')):
        return 16,'source'
    if name.startswith(('Molded front bumper', 'Molded rear bumper')) and 'inlay' not in name:
        return (157 if 'front' in name else 105),'evaluated'
    if name.startswith(('Continuous crowned roof', 'Crowned bonnet', 'Crowned boot')):
        return 115,'source'
    if name.startswith(('Black heritage registration plate','Front panel behind grille','Rear body face')):
        return 20,'base'
    if name.startswith(('Left', 'Right')) and any(token in name.lower() for token in ('plate','registration')):
        return 75,'evaluated'
    if 'red inlay' in name:
        return None,'bumper_inlay'
    if 'Red side molding' in name:
        return 20,'source'
    if 'structural frame' in name or 'weatherstrip' in name:
        return 24,'source'
    if any(token in name for token in ('folded edge', 'arch return', 'recessed wheelhouse','bumper arch transition')):
        return (25 if 'return' in name else 13),'source'
    if name.endswith(' panel') or ' panel.' in name:
        return 76,'source'
    if 'molding' in name:
        return 33,'source'
    if name.startswith(('Tapered black door mirror','Door handle recess','Black lift handle')):
        return 20,'evaluated'
    if name.startswith(('Shallow silver wheel cover','High profile radial tire','Pressed steel wheel')):
        return None,'wheel'
    if name.startswith('Rear seat cushion'):
        return 12,'base'
    if name.startswith(('Front head restraint','Front seat cushion','Front seat upholstered back','Rear seat','Sculpted padded dashboard')):
        return 30,'evaluated'
    return 14,'base'


def ordinary_rules(name, asset):
    short = name.partition('.')[0]
    if short in ('TYRE','RIM','INTERIOR_Steering'):
        return None,'torus'
    if short in ('HUB','FUEL_Tank','HEADLIGHT') and (asset=='motorbike_hd' or short=='HUB'):
        return 16 if asset == 'car_hatchback_hd' or short in ('FUEL_Tank','HEADLIGHT') else 12,'round'
    if short.startswith(('FRAME_', 'REAR_Shock', 'FRONT_Fork','HANDLEBAR','GRIP','EXHAUST','FOOTREST',
                         'STAND','MIRROR_Stem','A_Pillar','C_Pillar','DOOR_Frame')) and short != 'STAND_Foot':
        return 8,'round'
    if short in ('SPOKES','RIM_Spokes'):
        return 75 if short=='SPOKES' else 90,'spokes'
    if asset == 'motorbike_hd':
        return (35,'evaluated') if short in ('ENGINE','SEAT','TAIL','TAIL_Light') else (20,'base')
    if short in ('BODY_WheelArchSill','BODY_Nose','BODY_Tail','BONNET','ROOF','DOOR_Lower','REAR_Quarter',
                 'HEADLIGHT','TAIL_Light','MIRROR','HATCH_Glass','WINDSCREEN','REAR_Deck'):
        return 60,'evaluated'
    return 26,'evaluated'


def lamp_flute(obj, appearance, wheel):
    # A narrow double-sided quad preserves the lens ribs at their exact source positions.
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    x,y,z = zip(*points)
    center_y = (min(y)+max(y))/2
    front = min(x)-.0007
    w = .00075
    vertices = [Vector(p) for p in ((front,center_y-w,min(z)),(front,center_y+w,min(z)),
                                    (front,center_y+w,max(z)),(front,center_y-w,max(z)))]
    part = uniform(obj,vertices,[(3,2,1,0)],[False],appearance,wheel)
    part.styles = [('light',((.23,.25,.27),)*4)]
    return part


def extract(obj, asset, appearance, wheel, depsgraph, flute_ids):
    n = obj.name
    target, mode = saga_rules(n) if asset=='car_saga' else ordinary_rules(n,asset)
    if mode == 'front_lettering':
        part = get_part(obj,obj.data,appearance,wheel)
        x_side = math.copysign(1,obj.matrix_world.translation.x)
        selected = []
        for i, face in enumerate(part.faces):
            a,b,c = (part.vertices[j] for j in face[:3])
            cross = (b-a).cross(c-a)
            if cross.length > 0 and cross.normalized().x*x_side > .92:
                selected.append(i)
        item = Part(n,part.vertices,[part.faces[i] for i in selected],[part.styles[i] for i in selected],
                    [False]*len(selected))
        return lettering_outline(item,x_side)
    if n in flute_ids:
        return lamp_flute(obj,appearance,wheel)
    if not mode:
        return None
    if mode == 'torus':
        if n.startswith('INTERIOR'):
            segments, profile = 16,4
        elif n.startswith('RIM'):
            segments, profile = 20,3
        else:
            segments, profile = (24, 8 if asset == 'car_hatchback_hd' else 6)
        return torus(obj,segments,profile,appearance,wheel)
    if mode == 'round':
        result = round_source(obj,target,appearance,wheel)
        if result:
            return result
        target, mode = 36,'base'
    if mode == 'glazing':
        return glaze(obj,appearance)
    if mode == 'headlamp_bake':
        return headlamp_bake(obj,appearance)
    if mode == 'cell_bake':
        return cell_bake(obj,appearance)
    if mode == 'plate_border':
        return plate_border(obj,appearance)
    if mode == 'bumper_inlay':
        return bumper_inlay(obj,appearance)
    if mode == 'wheel':
        if n.startswith('High profile'):
            return saga_ring(obj,[0,2,4,6,8,10],20,appearance,wheel)
        if n.startswith('Shallow silver'):
            return saga_cover(obj,appearance,wheel)
        return saga_rim(obj,appearance,wheel)
    eval_obj = obj.evaluated_get(depsgraph) if mode == 'evaluated' else None
    mesh = eval_obj.to_mesh() if eval_obj else obj.data
    part = get_part(obj, mesh, appearance, wheel)
    if eval_obj:
        eval_obj.to_mesh_clear()
    if mode == 'spokes':
        return simplify_spokes(part, 5 if asset=='motorbike_hd' else 8)
    if target:
        angle = 1.2 if n.startswith(('Crowned','Continuous crowned')) else (4 if mode != 'evaluated' else 7)
        return simplify(part,target,angle)
    return part


def bounds(collection):
    points = [p for part in collection for face in part.faces for i in face for p in (part.vertices[i],)]
    return (Vector([min(p[i] for p in points) for i in range(3)]),
            Vector([max(p[i] for p in points) for i in range(3)]))


def assemble(name, parts, pivot, normalize, appearance):
    coordinates, faces, styles, smooth = [], [], [], []
    position = normalize @ pivot
    for part in parts:
        used = sorted({idx for face in part.faces for idx in face})
        if not used:
            continue
        mapping = {idx: len(coordinates)+j for j,idx in enumerate(used)}
        coordinates.extend(normalize @ part.vertices[idx]-position for idx in used)
        for face, style, is_smooth in zip(part.faces,part.styles,part.smooth):
            faces.append(tuple(mapping[i] for i in face))
            styles.append(style)
            smooth.append(is_smooth)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(coordinates,[],faces)
    mesh.update()
    used_styles = [x for x in CATEGORIES if any(s[0] == x for s in styles)]
    for key in used_styles:
        mesh.materials.append(appearance.make(key))
    colors = mesh.color_attributes.new(name='BakedColor',type='BYTE_COLOR',domain='CORNER')
    for face,(key,values),smooth_flag in zip(mesh.polygons,styles,smooth):
        face.material_index = used_styles.index(key)
        face.use_smooth = smooth_flag
        for loop,value in zip(face.loop_indices,values):
            colors.data[loop].color = (*value,1)
    mesh.color_attributes.active_color = colors
    obj = bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = position if name != 'body' else Vector()
    return obj


def run(asset):
    file, root_name, length, budget = MODELS[asset]
    bpy.ops.wm.open_mainfile(filepath=str(MODEL_ROOT/file),load_ui=False,use_scripts=False)
    bpy.context.preferences.filepaths.temporary_directory = str(ROOT/'.work')
    bpy.context.scene.frame_set(1)
    root = bpy.data.objects[root_name]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rotation = Matrix.Rotation(math.pi/2,4,'Z') if asset=='car_saga' else Matrix.Identity(4)
    parts = defaultdict(list)
    pivots = {}
    appearance = Appearance(asset)
    flutes = sorted(o.name for o in root.children_recursive if o.name.startswith('Headlight vertical optical flute'))
    flute_ids = set(flutes[::2])
    for obj in root.children_recursive:
        if obj.type != 'MESH':
            continue
        wheel = wheel_owner(obj,asset,rotation)
        part = extract(obj,asset,appearance,wheel,depsgraph,flute_ids)
        if not part:
            continue
        group = wheel[0] if wheel else 'body'
        if wheel:
            pivots[group] = rotation @ wheel[1]
        for i, p in enumerate(part.vertices):
            part.vertices[i] = rotation @ p
        parts[group].append(part)

    lo,hi = bounds(part for group in parts.values() for part in group)
    center = Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    scale = length/(hi.y-lo.y)
    normalize = Matrix.Scale(scale,4) @ Matrix.Translation(-center)
    pivots['body'] = center
    counts = {name:sum(p.triangles for p in group) for name,group in parts.items()}
    print('COUNTS',asset,counts,sum(counts.values()),'target',budget,flush=True)
    if sum(counts.values()) > budget:
        raise ValueError(f'{asset} has {sum(counts.values())} triangles, limit {budget}')
    with (ROOT/'.work'/f'{asset}-counts.txt').open('w') as log:
        for name, group in parts.items():
            print(name,file=log)
            for p in sorted(group,key=lambda p:-p.triangles):
                print(f'{p.triangles:4} {p.name}',file=log)
    bpy.ops.object.select_all(action='DESELECT')
    objects = [assemble(name,parts[name],pivots[name],normalize,appearance) for name in sorted(parts)]
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(ROOT/f'{asset}.glb'),export_format='GLB',use_selection=True,
        export_apply=False,export_yup=True,export_animations=False,export_texcoords=False,
        export_tangents=False,export_extras=False,export_cameras=False,export_lights=False,
        export_skins=False,export_all_vertex_colors=False)


if __name__ == '__main__':
    (ROOT/'.work').mkdir(exist_ok=True)
    requested = sys.argv[sys.argv.index('--')+1:]
    for asset in requested or MODELS:
        run(asset)
