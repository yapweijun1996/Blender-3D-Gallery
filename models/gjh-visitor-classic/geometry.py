"""Geometry and skin contract shared by the interchangeable visitor parts."""
import math
import bpy
from mathutils import Vector


def linear_component(value):
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def srgb(code):
    s = code.lstrip('#')
    return tuple(int(s[i:i+2], 16) / 255 for i in (0, 2, 4)) + (1.,)


def layer_color(colors, i):
    return colors if isinstance(colors, str) else colors[min(i, len(colors)-1)]


class Geometry:
    def __init__(self, scene, atlas):
        self.scene = scene
        self.parts = {}
        self.materials = {}
        self.atlas = atlas

    def material(self, family):
        if family in self.materials:
            return self.materials[family]
        mat = bpy.data.materials.new('Classic • ' + family)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        shader = nodes.get('Principled BSDF')
        if family == 'Face ink':
            source = nodes.new('ShaderNodeTexImage')
            source.image = self.atlas
            source.interpolation = 'Linear'
            mat.node_tree.links.new(source.outputs['Alpha'], shader.inputs['Alpha'])
            mat.surface_render_method = 'DITHERED'
        else:
            source = nodes.new('ShaderNodeVertexColor')
            source.layer_name = 'Palette'
        mat.node_tree.links.new(source.outputs['Color'], shader.inputs['Base Color'])
        shader.inputs['Roughness'].default_value = {'Hair': .59, 'Skin': .80, 'Canvas': .84}.get(family, .74)
        shader.inputs['Specular IOR Level'].default_value = .24 if family != 'Face ink' else .12
        self.materials[family] = mat
        return mat

    def collection(self, slot):
        if slot not in self.parts:
            col = bpy.data.collections.new(slot)
            self.scene.collection.children.link(col)
            self.parts[slot] = col
        return self.parts[slot]

    def mesh(self, name, slot, verts, faces, colors, bone='Head', smooth=False):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        self.collection(slot).objects.link(obj)
        obj['partSlot'] = slot
        family = 'Skin'
        if slot == 'Hair':
            family = 'Hair'
        elif slot in ('Hoodie','Shorts','Jeans','Hat') or slot.startswith('Sock.'):
            family = 'Cotton'
        elif slot == 'Backpack' or slot.startswith('Shoe.'):
            family = 'Canvas'
        mesh.materials.append(self.material(family))
        paint = mesh.color_attributes.new(name='Palette',type='BYTE_COLOR',domain='CORNER')
        for p in mesh.polygons:
            p.use_smooth = smooth
            color = srgb(layer_color(colors,p.index))
            for i in p.loop_indices:
                paint.data[i].color_srgb = color
        for i, pt in enumerate(verts):
            weights = bone(*pt) if callable(bone) else bone if isinstance(bone,(str,dict)) else bone[i]
            if isinstance(weights, str):
                weights = {weights:1.}
            for b, weight in weights.items():
                if weight <= 0:
                    continue
                group = obj.vertex_groups.get(b) or obj.vertex_groups.new(name=b)
                group.add([i],weight,'REPLACE')
        return obj

    def rings(self,name,slot,levels,colors,bone,segments=8,smooth=False):
        verts=[]; faces=[]; face_colors=[]
        for z,x,y,rx,ry in levels:
            for i in range(segments):
                a = math.tau*i/segments
                verts.append((x+rx*math.sin(a), y-ry*math.cos(a), z))
        faces.append(tuple(reversed(range(segments))))
        face_colors.append(layer_color(colors,0))
        for k in range(len(levels)-1):
            for i in range(segments):
                a=k*segments+i; b=k*segments+(i+1)%segments
                faces.append((a,b,b+segments,a+segments))
                face_colors.append(layer_color(colors,k))
        faces.append(tuple(range((len(levels)-1)*segments,len(verts))))
        face_colors.append(layer_color(colors,len(levels)-2))
        return self.mesh(name,slot,verts,faces,face_colors,bone,smooth)

    def oval(self,name,slot,center,radii,color,bone,segments=8,steps=4,smooth=True):
        cx,cy,cz=center; rx,ry,rz=radii
        v=[(cx,cy,cz-rz)]; f=[]
        for k in range(1,steps):
            a=math.pi*k/steps
            for j in range(segments):
                b=math.tau*j/segments
                v.append((cx+rx*math.sin(a)*math.sin(b),cy-ry*math.sin(a)*math.cos(b),cz-rz*math.cos(a)))
        v.append((cx,cy,cz+rz))
        for j in range(segments):
            jj=(j+1)%segments
            f.append((0,1+jj,1+j))
            for k in range(steps-2):
                a=1+k*segments+j; b=1+k*segments+jj
                f.append((a,b,b+segments,a+segments))
            f.append((len(v)-1, 1+(steps-2)*segments+j,1+(steps-2)*segments+jj))
        return self.mesh(name,slot,v,f,color,bone,smooth)

    def tapered(self,name,slot,start,end,r1,r2,tint,bone,sides=8):
        a=Vector(start); b=Vector(end); axis=(b-a).normalized()
        u=axis.cross(Vector((0,1,0))).normalized(); v=axis.cross(u)
        pts=[]
        for origin,r in ((a,r1),(b,r2)):
            for j in range(sides):
                th=math.tau*j/sides
                pts.append(tuple(origin+r*(u*math.cos(th)+v*math.sin(th))))
        faces=[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]
        faces.extend((j,(j+1)%sides,(j+1)%sides+sides,j+sides) for j in range(sides))
        return self.mesh(name,slot,pts,faces,tint,bone,True)
