"""Deterministic Pomelo STEM v8.2: original geometry, headless Blender only.

Generic mesh/export helpers adapted from the read-only BlenderChibi example.
All character geometry is authored here for the supplied Pomelo design board.
"""
from __future__ import annotations
import argparse
import json
import math
import struct
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT = Path(__file__).resolve().parent
TAU = math.tau
SCENE = None
M = {}
CLIPS = {"Idle": 60, "Wave": 36, "Blink": 72}
EXPRESSIONS = ("happy", "laugh", "surprised", "wink", "thinking", "sad")
PALETTE = {"pomelo": "CBE85A", "cream": "FFFBE6", "leaf": "4A9F2D", "blush": "FFB6B6", "eye": "293226"}

def linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def rgba(hex_color):
    return tuple(linear(int(hex_color[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1,)


def material(name, color, roughness=.55, metallic=0, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba(color)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = rgba(color)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metallic
    if emission:
        p.inputs["Emission Color"].default_value = rgba(color)
        p.inputs["Emission Strength"].default_value = emission
    mat.use_backface_culling = True
    return mat




def empty(name, parent=None, loc=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None)
    SCENE.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    ob.empty_display_size = .035
    return ob


def mesh(name, vertices, faces, mat, parent=None, smooth=True, outline=0):
    data = bpy.data.meshes.new(name + "_Mesh")
    data.from_pydata(vertices, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    SCENE.collection.objects.link(ob)
    ob.parent = parent
    data.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    for p in data.polygons:
        p.use_smooth = smooth
    if mat in [M.get(key) for key in ('pomelo', 'leaf', 'eye')]:
        tint = (.22, .22, .19) if mat == M.get('eye') else (1, 1, 1)
        vertex_tint(ob, lambda p: tint)
    if outline:
        add_outline(ob, outline)
    return ob


def add_outline(ob, width=.0015):
    data = ob.data.copy()
    data.name = ob.name + "_InvertedHullMesh"
    data.materials.clear()
    data.materials.append(M["edge"])
    for attribute in list(data.color_attributes):
        data.color_attributes.remove(attribute)
    bm = bmesh.new()
    bm.from_mesh(data)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * width
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    outline = bpy.data.objects.new(ob.name + "__Outline", data)
    SCENE.collection.objects.link(outline)
    outline.parent = ob
    outline["technique"] = "Inverted hull; inward winding; single-sided ink material"
    outline["width_m"] = width
    if hasattr(outline, "visible_shadow"):
        outline.visible_shadow = False
    return outline




def spow(v, power):
    return math.copysign(abs(v) ** power, v)


def ellipsoid(name, loc, scale, mat, parent=None, segments=28, rings=16, power=2, outline=0):
    verts = [(0, -scale[1], 0)]
    for j in range(1, rings):
        phi = -math.pi / 2 + math.pi * j / rings
        radial = math.cos(phi) ** (2 / power)
        for i in range(segments):
            theta = TAU * i / segments
            verts.append((scale[0] * radial * spow(math.cos(theta), 2 / power),
                          scale[1] * spow(math.sin(phi), 2 / power),
                          scale[2] * radial * spow(math.sin(theta), 2 / power)))
    end = len(verts)
    verts.append((0, scale[1], 0))
    faces = []
    for i in range(segments):
        faces.append((0, 1 + (i + 1) % segments, 1 + i))
    for j in range(rings - 2):
        a = 1 + j * segments
        b = a + segments
        for i in range(segments):
            n = (i + 1) % segments
            faces.append((a + i, a + n, b + n, b + i))
    a = 1 + (rings - 2) * segments
    for i in range(segments):
        faces.append((a + i, a + (i + 1) % segments, end))
    ob = mesh(name, verts, faces, mat, parent, outline=outline)
    ob.location = loc
    return ob




def tube(name, points, radius, mat, parent=None, sides=8, closed=False, outline=0):
    points = [Vector(p) for p in points]
    verts, faces = [], []
    tangents = []
    for j in range(len(points)):
        tangent = (points[(j + 1) % len(points)] - points[(j - 1) % len(points)]) if closed else (points[min(j + 1, len(points) - 1)] - points[max(j - 1, 0)])
        tangents.append(tangent.normalized())
    # A stable least-aligned reference avoids frame flips at the top and bottom of rings.
    axes = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    reference = min(axes, key=lambda axis: sum(abs(t.dot(axis)) for t in tangents))
    for j, point in enumerate(points):
        tangent = tangents[j]
        u = tangent.cross(reference)
        if u.length < .01:
            u = tangent.cross(Vector((1, 0, 0)))
        u.normalize()
        v = tangent.cross(u).normalized()
        for i in range(sides):
            a = TAU * i / sides
            verts.append(point + radius * (math.cos(a) * u + math.sin(a) * v))
    steps = len(points) if closed else len(points) - 1
    for j in range(steps):
        for i in range(sides):
            a = j * sides + i
            b = j * sides + (i + 1) % sides
            c = ((j + 1) % len(points)) * sides
            faces.append((a, b, c + (i + 1) % sides, c + i))
    if not closed:
        faces.extend([tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + i for i in range(sides))])
    return mesh(name, verts, faces, mat, parent, outline=outline)


def rounded_stroke(name, points, radius, mat, parent, sides=8):
    ob = tube(name, points, radius, mat, parent, sides)
    for label, p in [("Start", points[0]), ("End", points[-1])]:
        ellipsoid(name + "_" + label, p, (radius,) * 3, mat, parent, 8, 6)
    return ob




def descendants(root):
    return [root] + list(root.children_recursive)


def world_bounds(objects):
    bpy.context.view_layer.update()
    coords = [ob.matrix_world @ v.co for ob in objects if ob.type == "MESH" for v in ob.data.vertices]
    return ([min(p[i] for p in coords) for i in range(3)], [max(p[i] for p in coords) for i in range(3)])


def normalize_character(root):
    low, high = world_bounds(descendants(root))
    factor = 1 / (high[2] - low[2])
    # Bake uniform normalization into mesh vertices and node translations, retaining an identity root.
    for ob in descendants(root):
        if ob == root:
            continue
        ob.location *= factor
        if ob.type == "MESH":
            for v in ob.data.vertices:
                v.co *= factor
    for ob in root.children:
        ob.location.z -= low[2] * factor
    bpy.context.view_layer.update()
    root["height_m"] = 1.0
    root["normalization_scale"] = factor
    root["assembly_floor_offset"] = -low[2] * factor
    root["front_blender"] = "-Y"
    root["front_gltf"] = "+Z"
    root["up_gltf"] = "+Y"
    return factor




def stash_action(owner, clip, action):
    track = owner.animation_data.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, 0, action)
    strip.blend_type = "REPLACE"
    strip.extrapolation = "NOTHING"
    track.mute = True
    owner.animation_data.action = None


def bind_mesh(ob, rig, parent, weights):
    world = ob.matrix_world.copy()
    ob.data.transform(world)
    ob.parent = parent
    ob.matrix_world = Matrix.Identity(4)
    ob.vertex_groups.clear()
    for bone in sorted({name for row in weights for name, value in row.items() if value > 0}):
        group = ob.vertex_groups.new(name=bone)
        for i, row in enumerate(weights):
            if row.get(bone, 0) > 0:
                group.add([i], row[bone], "REPLACE")
    modifier = ob.modifiers.new("Skin including ink hull", "ARMATURE")
    modifier.object = rig
    modifier.use_deform_preserve_volume = False  # Match glTF linear blend skinning.
    ob["skin_binding"] = "Normalized explicit weights; ink copies physical vertex weights"


def smoothstep(a, b, x):
    t = max(0, min(1, (x-a)/(b-a)))
    return t*t*(3-2*t)


def wave_arm_rest(pose):
    z=.253 if pose=='hero' else .207
    return [Vector(p) for p in ((.175,-.035,z-.020),(.135,-.010,z-.038),(.246 if pose=='hero' else .241,-.088,z))]


def add_wave_capsule(name, a, b, parent):
    """Low-poly thick capsule; folded inside the existing torso at rest."""
    axis=(b-a).normalized()
    u=axis.cross(Vector((0,0,1))).normalized();v=axis.cross(u)
    radius=.041
    vertices=[a-axis*radius]
    stations=[(a,-.707,.707),(a,0,1),(b,0,1),(b,.707,.707)]
    for center,along,radial in stations:
        for i in range(12):
            theta=TAU*i/12
            vertices.append(center+axis*(along*radius)+(u*math.cos(theta)+v*math.sin(theta))*(radius*radial))
    vertices.append(b+axis*radius)
    faces=[]
    for i in range(12):faces.append((0,1+(i+1)%12,1+i))
    for j in range(3):
        for i in range(12):
            n=(i+1)%12;lo=1+j*12;hi=lo+12
            faces.append((lo+i,lo+n,hi+n,hi+i))
    for i in range(12):faces.append((37+i,37+(i+1)%12,49))
    return mesh(name,vertices,faces,M['cream'],parent,outline=.00050)


def rig_character(root):
    """Preserve R4 meshes and skeleton; add folded, fixed-length Wave links."""
    # These short folded links are inside the R4 torso/mitten at rest.
    if root['expression'] not in ('thinking','sad'):
        f,floor=root['normalization_scale'],root['assembly_floor_offset']
        a,b,c=[p*f+Vector((0,0,floor)) for p in wave_arm_rest(root['pose'])]
        add_wave_capsule('Body/R_UpperArm',a,b,root)
        add_wave_capsule('Body/R_Forearm',b,c,root)
    bpy.context.view_layer.update()
    objects = descendants(root)
    meshes = [o for o in objects if o.type == 'MESH']
    f, floor = root['normalization_scale'], root['assembly_floor_offset']
    def point(p):
        return Vector(p)*f + Vector((0,0,floor))
    specs = [('Root',(0,0,0),(0,0,.08),None),
             ('Body',(0,.025,.12),(0,.025,.30),'Root'),
             ('Head',(0,.025,.32),(0,.025,.75),'Body'),
             ('Stem',(0,.004,.901),(0,.004,.932),'Head')]
    for side,label in [(-1,'L'),(1,'R')]:
        x,z = (.246,.253) if root['pose']=='hero' else (.241,.207)
        elbow=.475 if side>0 else .222
        wrist=.655 if side>0 else x
        tip=.715 if side>0 else x+.035
        specs += [
            ('Shoulder.'+label,(side*.17,-.088,z),(side*.205,-.088,z),'Body'),
            ('Arm.'+label,(side*.205,-.088,z),(side*elbow,-.088,z),'Shoulder.'+label),
            ('Forearm.'+label,(side*elbow,-.088,z),(side*wrist,-.088,z),'Arm.'+label),
            ('Hand.'+label,(side*wrist,-.088,z),(side*tip,-.088,z),'Forearm.'+label),
            ('Leg.'+label,(side*.115,.025,.15),(side*.115,-.04,.07),'Root'),
            ('Foot.'+label,(side*.115,-.04,.07),(side*.115,-.11,.04),'Leg.'+label),
            ('LeafBase.'+label,(side*.01,.004,.918),(side*.08,.004,.955),'Stem'),
            ('LeafTip.'+label,(side*.08,.004,.955),(side*.16,.004,.988),'LeafBase.'+label),
        ]
    weights = {}
    for ob in meshes:
        rows=[]
        for vertex in ob.data.vertices:
            p=(ob.matrix_world @ vertex.co-Vector((0,0,floor)))/f
            name=ob.name
            if name.startswith('Leaves/'):
                if 'Stem' in name:
                    row={'Stem':1.0}
                else:
                    label='L' if '/L_' in name else 'R'
                    t=smoothstep(.04,.14,abs(p.x))
                    row={'LeafBase.'+label:1-t,'LeafTip.'+label:t}
            elif name.startswith(('Head/','Face/')):
                row={'Head':1.0}
            elif '_CreamFoot' in name:
                row={'Foot.'+('L' if '/L_' in name else 'R'):1.0}
            elif name.startswith('Body/R_UpperArm'):
                row={'Arm.R':1.0}
            elif name.startswith('Body/R_Forearm'):
                row={'Forearm.R':1.0}
            elif 'Mitten' in name or 'RaisedForearm' in name:
                label='L' if '/L_' in name else 'R'
                row={'Hand.'+label:1.0}
            elif name.startswith('Body/Torso'):
                # The broad shoulder rises under the head; its hull uses the
                # same weights. No cream limb is lengthened to reach the cheek.
                q=.65*smoothstep(.11,.17,p.x)*smoothstep(.16,.225,p.z)*(1-smoothstep(.245,.355,p.z))
                row={'Body':1-q,'Shoulder.R':q}
            elif 'NeckFillet' in name:
                t=smoothstep(.285,.343,p.z)
                row={'Body':1-t,'Head':t}
            else:
                row={'Body':1.0}
            rows.append({k:v for k,v in row.items() if v>0})
        weights[ob]=rows
    for ob in meshes:
        if '__Outline' in ob.name:
            assert len(ob.data.vertices)==len(ob.parent.data.vertices)
            weights[ob]=weights[ob.parent]
            ob['outline_source']=ob.parent.name
    data=bpy.data.armatures.new(root.name+'_Skeleton')
    rig=bpy.data.objects.new(root.name+'_Rig',data)
    SCENE.collection.objects.link(rig);rig.parent=root
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    for name,a,b,parent in specs:
        bone=data.edit_bones.new(name);bone.head=point(a);bone.tail=point(b)
        if parent: bone.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    worlds={ob:ob.matrix_world.copy() for ob in meshes}
    for ob in meshes:
        ob.parent=root;ob.matrix_world=worlds[ob]
    bpy.context.view_layer.update()
    for ob in meshes: bind_mesh(ob,rig,root,weights[ob])
    eyes=[ob for ob in meshes if any(t in ob.name for t in ('_Eye','_WhiteHighlight'))]
    for ob in eyes:
        ob.shape_key_add(name='Basis');key=ob.shape_key_add(name='Blink')
        for v,target in zip(ob.data.vertices,key.data):
            p=(v.co-Vector((0,0,floor)))/f
            z=.557+(p.z-.557)*.055
            # Flatten the oval on the same curved mask rather than into it.
            y=face_y(p.x,z)+(p.y-face_y(p.x,p.z))
            target.co=point((p.x,y,z))
    arms=[ob for ob in meshes if '/R_CreamMitten' in ob.name]
    rig['arm_pose']=root['pose']
    rig['normalization_floor']=floor
    animate_rig(rig,eyes,arms,f)
    root['rig_bones']=[name for name,*_ in specs]
    root['rest_pose']='Original R4 meshes preserved; short capsule links folded inside torso; exact loop seam'
    root['animation_clips_seconds']={name:end/24 for name,end in CLIPS.items()}
    return rig


def animate_rig(rig, eyes, arms, factor):
    rig.animation_data_create()
    for bone in rig.pose.bones: bone.rotation_mode='QUATERNION'
    def rotation(name,axis,angle):
        b=rig.pose.bones[name]
        b.rotation_quaternion=Quaternion(b.bone.matrix_local.to_3x3().inverted() @ Vector(axis),angle)
    def move(name,delta):
        b=rig.pose.bones[name]
        b.location=b.bone.matrix_local.to_3x3().inverted() @ (Vector(delta)*factor)
    foot_geometry={}
    for side in ('L','R'):
        name='Foot.'+side
        bone=rig.data.bones[name]
        ob=next(o for o in SCENE.objects if o.type=='MESH' and o.name.startswith('Body/'+side+'_CreamFoot') and '__Outline' not in o.name and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers))
        foot_geometry[name]=(bone.matrix_local.copy(),[bone.matrix_local.inverted() @ v.co for v in ob.data.vertices],min(v.co.z for v in ob.data.vertices))
    for clip,end in CLIPS.items():
        action=bpy.data.actions.new(rig.name+'/'+clip);rig.animation_data.action=action
        for frame in range(end+1):
            u=frame/end
            arm_targets=[]
            for b in rig.pose.bones: b.matrix_basis=Matrix.Identity(4)
            if clip=='Idle':
                breath=math.sin(math.pi*u)**2
                move('Body',(0,0,.0035*breath))
                rig.pose.bones['Body'].scale=(1+.006*breath,1,1+.004*breath)
                rotation('Head',(0,1,0),math.radians(.5)*math.sin(TAU*u))
            if clip=='Wave':
                lift=smoothstep(0,9,frame)*(1-smoothstep(27,36,frame))
                pulse=math.sin(TAU*(frame-9)/9.5)*smoothstep(8,10,frame)*(1-smoothstep(26,28,frame))
                if arms:
                    clearance=smoothstep(0,5,frame)*(1-smoothstep(31,36,frame))
                    shoulder_delta=Vector((.100*clearance,-.180*clearance,.080*lift))
                    # Fixed-length folded links rotate; the shoulder adds a
                    # small shrug beneath the head instead of extending cream.
                    move('Shoulder.R',shoulder_delta)
                    rest_a,rest_b,rest_c=wave_arm_rest(rig['arm_pose'])
                    rest_upper=rest_b-rest_a;rest_fore=rest_c-rest_b
                    upper_target=Vector((.90,-.20,.38)).normalized()
                    fore_target=Quaternion((0,1,0),math.radians(18*pulse)) @ Vector((.65,-.35,.67)).normalized()
                    upper_rot=rest_upper.normalized().rotation_difference(upper_target)
                    fore_rot=rest_fore.normalized().rotation_difference(fore_target)
                    upper_rot=Quaternion().slerp(upper_rot,lift)
                    fore_rot=Quaternion().slerp(fore_rot,lift)
                    posed_a=rest_a+shoulder_delta
                    posed_b=posed_a+upper_rot @ rest_upper
                    posed_c=posed_b+fore_rot @ rest_fore
                    # Store target transforms, then apply after the body lean.
                    arm_targets=[('Arm.R',rest_a,posed_a,upper_rot),
                                 ('Forearm.R',rest_b,posed_b,fore_rot),
                                 ('Hand.R',rest_c,posed_c,Quaternion((0,1,0),math.radians(-35+18*pulse)*lift))]
                    for side in ('L','R'):
                        foot=rig.pose.bones['Foot.'+side]
                        squash=.018*lift*(.5+.5*math.sin(TAU*(frame-9)/9.5))
                        # Scale around the sole so contact remains stable.
                        foot.scale=(1+squash*.5,1,1-squash)
                        bind,points,sole=foot_geometry['Foot.'+side]
                        scaled_sole=min((bind @ Vector(tuple(p[i]*foot.scale[i] for i in range(3)))).z for p in points)
                        move('Foot.'+side,(0,0,(sole-scaled_sole)/factor))
                rotation('Body',(0,1,0),math.radians(-1.5)*lift)
                lag=smoothstep(5,11,frame)*(1-smoothstep(27,35,frame))
                rotation('Head',(0,1,0),math.radians(2.5)*lag)
            if clip in ('Idle','Wave'):
                rotation('Stem',(1,0,0),math.radians(.7)*math.sin(TAU*u))
                for side,label in [(-1,'L'),(1,'R')]:
                    rotation('LeafBase.'+label,(0,1,0),side*math.radians(1.4)*math.sin(TAU*u))
                    # A phase-delayed second link; envelope makes loop/rest exact.
                    rotation('LeafTip.'+label,(1,0,0),math.radians(2)*math.sin(TAU*u-.6)*math.sin(math.pi*u)**2)
                if clip=='Wave':
                    follow=smoothstep(5,12,frame)*(1-smoothstep(27,36,frame))
                    rotation('Stem',(1,0,0),math.radians(.7)*math.sin(TAU*(frame-11)/9.5)*follow)
                    for side,label in [(-1,'L'),(1,'R')]:
                        rotation('LeafBase.'+label,(0,1,0),side*math.radians(1.4)*math.sin(TAU*(frame-12)/9.5)*follow)
                        rotation('LeafTip.'+label,(1,0,0),math.radians(2)*math.sin(TAU*(frame-13)/9.5)*follow)
            if arm_targets:
                bpy.context.view_layer.update()
                body=rig.pose.bones['Body']
                body_deform=body.matrix @ body.bone.matrix_local.inverted()
                floor=Vector((0,0,rig['normalization_floor']))
                for name,rest,posed,rotation_q in arm_targets:
                    deform=Matrix.Translation(posed*factor+floor) @ rotation_q.to_matrix().to_4x4() @ Matrix.Translation(-rest*factor-floor)
                    bone=rig.pose.bones[name]
                    bone.matrix=body_deform @ deform @ bone.bone.matrix_local
                    bpy.context.view_layer.update()
            for b in rig.pose.bones:
                for channel in ('location','rotation_quaternion','scale'):
                    b.keyframe_insert(channel,frame=frame,group=b.name)
        stash_action(rig,clip,action)
    for ob in eyes:
        keys=ob.data.shape_keys;keys.animation_data_create();key=keys.key_blocks['Blink']
        for clip,end in CLIPS.items():
            action=bpy.data.actions.new(ob.name+'/'+clip);keys.animation_data.action=action
            samples=[(0,0),(28,0),(31,.65),(33,1),(35,1),(38,0),(72,0)] if clip=='Blink' else [(0,0),(end,0)]
            for frame,value in samples:
                key.value=value;key.keyframe_insert('value',frame=frame)
            stash_action(keys,clip,action)
        key.value=0
    for b in rig.pose.bones: b.matrix_basis=Matrix.Identity(4)
    SCENE.frame_set(0)


def bind_kit(row, rig):
    """Six named mount joints preserve transform control under glTF skin roots."""
    meshes=[o for o in descendants(row) if o.type=='MESH']
    worlds={o:o.matrix_world.copy() for o in meshes};parents={o:o.parent for o in meshes}
    mounts=[o for o in descendants(row) if o.name.startswith('Mount_')]
    mount_names={o:o.name for o in mounts}
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True)
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    for mount in mounts:
        b=rig.data.edit_bones.new(mount.name)
        b.head=mount.matrix_world.translation;b.tail=b.head+Vector((0,0,.1))
        b.parent=rig.data.edit_bones['Root']
    bpy.ops.object.mode_set(mode='OBJECT')
    bindings={}
    for ob in meshes:
        if '__Outline' in ob.name:ob['outline_source']=ob.parent.name
        p=ob.parent
        while p not in mounts:p=p.parent
        bindings[ob]=mount_names[p];ob['expression_mount']=mount_names[p]
    for mount in mounts:mount.name='Source_'+mount.name
    for ob in meshes:
        ob.parent=row;ob.matrix_world=worlds[ob]
    bpy.context.view_layer.update()
    for ob in meshes:
        bind_mesh(ob,rig,row,[{bindings[ob]:1.0} for _ in ob.data.vertices]);ob['kit_display']=True
        world=ob.matrix_world.copy();ob.parent=parents[ob];ob.matrix_world=world
    rig.parent['expression_mount_joints']=list(mount_names.values())


def finalize_glb(path):
    """Losslessly pack rigid weights and use validator-compatible skin roots."""
    raw = path.read_bytes()
    length = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20:20+length])
    binary = raw[28+length:]
    replacements = {}
    weights = {p["attributes"]["WEIGHTS_0"] for m in doc["meshes"] for p in m["primitives"]
               if "WEIGHTS_0" in p["attributes"]}
    for index in sorted(weights):
        a = doc["accessors"][index]
        if a["componentType"] != 5126:
            continue
        v = doc["bufferViews"][a["bufferView"]]
        assert not a.get("byteOffset",0) and v.get("byteStride",16) == 16
        values = np.frombuffer(binary, dtype="<f4", count=a["count"]*4, offset=v["byteOffset"])
        if np.all((values == 0) | (values == 1)):
            # UNORM8 encodes 0 and 1 exactly. Blended weights remain FLOAT.
            replacements[a["bufferView"]] = (values*255).astype(np.uint8).tobytes()
            a["componentType"] = 5121
            a["normalized"] = True
            if "byteStride" in v:
                v["byteStride"] = 4
    packed = bytearray()
    shared_blocks = {}
    for i,view in enumerate(doc["bufferViews"]):
        packed.extend(b"\0"*((-len(packed))%4))
        block = replacements.get(i, binary[view["byteOffset"]:view["byteOffset"]+view["byteLength"]])
        # Reuse identical immutable buffers (indices, normals, rigid weights,
        # colors) across expression figures. Geometry and weights are lossless.
        signature = (block, view.get('target'), view.get('byteStride'))
        offset = shared_blocks.get(signature)
        if offset is None:
            offset = len(packed)
            shared_blocks[signature] = offset
            packed.extend(block)
        view["byteOffset"], view["byteLength"] = offset, len(block)
    doc["buffers"][0]["byteLength"] = len(packed)
    # glTF ignores parents of skinned mesh nodes. Our nodes have baked identity
    # transforms; make them scene roots to remove NODE_SKINNED_MESH_NON_ROOT.
    skinned = {i for i,n in enumerate(doc["nodes"]) if "skin" in n}
    for n in doc["nodes"]:
        if "children" in n:
            n["children"] = [i for i in n["children"] if i not in skinned]
            if not n["children"]:
                del n["children"]
    for scene in doc["scenes"]:
        scene["nodes"] = list(dict.fromkeys(scene["nodes"]+sorted(skinned)))
    if doc.get("animations"):
        doc["animations"] = sorted(doc["animations"], key=lambda a:list(CLIPS).index(a["name"]))
    header = json.dumps(doc, separators=(",",":"), ensure_ascii=False).encode()
    header += b" "*((-len(header))%4)
    packed.extend(b"\0"*((-len(packed))%4))
    total = 12+8+len(header)+8+len(packed)
    path.write_bytes(struct.pack("<4sII",b"glTF",2,total)+struct.pack("<I4s",len(header),b"JSON")+
                     header+struct.pack("<I4s",len(packed),b"BIN\0")+packed)


def animation_owners(scene):
    owners = []
    for ob in scene.objects:
        if ob.animation_data:
            owners.append(ob)
        if ob.type == "MESH" and ob.data.shape_keys and ob.data.shape_keys.animation_data:
            owners.append(ob.data.shape_keys)
    return owners


def activate_clip(scene, clip, frame):
    for ob in scene.objects:
        if ob.type == "ARMATURE":
            for bone in ob.pose.bones:
                bone.matrix_basis = Matrix.Identity(4)
        if ob.type == "MESH" and ob.data.shape_keys:
            for key in ob.data.shape_keys.key_blocks[1:]:
                key.value = 0
    matched = 0
    offsets = []
    for owner in animation_owners(scene):
        owner.animation_data.action = None
        for track in owner.animation_data.nla_tracks:
            track.mute = track.name != clip
            matched += not track.mute
            if not track.mute:
                offsets.append(track.strips[0].frame_start-track.strips[0].action_frame_start)
    assert matched, (clip, [o.name for o in animation_owners(scene)])
    # Blender's glTF importer places time zero at scene frame one.
    frame += min(offsets)
    scene.frame_set(int(frame), subframe=frame-int(frame))
    bpy.context.view_layer.update()


def export_glb(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    original_parents = {ob:(ob.parent,ob.matrix_world.copy()) for ob in objects if ob.type=='MESH'}
    for ob,(_,world) in original_parents.items():
        ob.parent=objects[0];ob.matrix_world=world
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True,
        export_yup=True, export_apply=False, export_animations=True,
        export_animation_mode="ACTIONS", export_merge_animation="NLA_TRACK",
        export_force_sampling=True, export_frame_range=False,
        export_skins=True, export_rest_position_armature=True,
        export_anim_single_armature=False, export_optimize_animation_size=True,
        export_optimize_animation_keep_anim_armature=False,
        export_optimize_animation_keep_anim_object=False,
        export_optimize_disable_viewport=False,
        export_cameras=False, export_lights=False, export_extras=True,
        export_texcoords=False, export_normals=True, export_materials="EXPORT",
        export_image_format="NONE", export_attributes=False,
        export_vertex_color='NAME', export_vertex_color_name='Color',
        export_all_vertex_colors=False, export_active_vertex_color_when_no_material=False,
    )
    for ob,(parent,world) in original_parents.items():
        ob.parent=parent;ob.matrix_world=world
    bpy.context.view_layer.update()
    finalize_glb(path)
    return inspect_glb(path)


def inspect_glb(path):
    raw = path.read_bytes()
    length = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20:20 + length])
    triangles = sum(doc["accessors"][p["indices"]]["count"] // 3 for m in doc.get("meshes", []) for p in m["primitives"])
    info = {"bytes": len(raw), "triangles": triangles, "meshes": len(doc.get("meshes", [])), "nodes": len(doc.get("nodes", [])),
            "materials": len(doc.get("materials", [])), "images": len(doc.get("images", [])), "animations": len(doc.get("animations", [])),
            "outline_nodes": sum(n.get("name", "").endswith("__Outline") for n in doc["nodes"]),
            "extensions_used": doc.get("extensionsUsed", [])}
    print("EXPORT_METRICS", path.name, json.dumps(info), flush=True)
    return info


def aim(ob, point):
    ob.rotation_euler = (Vector(point) - ob.location).to_track_quat("-Z", "Y").to_euler()



# The head is a pear-shaped superellipsoid with a continuous recessed face opening.
HEAD_A, HEAD_B, HEAD_C, HEAD_Z, HEAD_P = .377, .265, .325, .600, 2.30
FACE_Z = .535


def materials():
    for key, color in PALETTE.items():
        M[key] = material(key.title() + ' | #' + color, color,
                          .33 if key in ('pomelo', 'eye') else .45)
    M['eye'].node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .14
    M['eye'].node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .20
    M['white'] = material('Eye highlights | #FFFFFF', 'FFFFFF', .22)
    M['mouth'] = material('Mouth interior | deep warm red', '650F08', .38)
    M['mouth'].node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .08
    M['tongue'] = material('Tongue | warm coral', 'FF7565', .38)
    M['vein'] = material('Leaf midrib | soft green', '75B443', .40)
    M['sole'] = material('Soft warm cream sole', 'E8D5A2', .53)
    M['blush_soft'] = material('Blush | #FFB6B6 fading into #FFFBE6', 'FFFFFF', .53)
    M['edge'] = material('Dark olive outline | inverted hull', '3C542B', 1)
    M['mount'] = material('Kit pale green mounts', 'E2EECF', .72)
    p = M['edge'].node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (0, 0, 0, 1)
    p.inputs['Emission Color'].default_value = rgba('3C542B')
    p.inputs['Emission Strength'].default_value = 1
    # Reduce broad white reflections without changing the specified base colors.
    for key in ('pomelo', 'cream', 'leaf', 'blush'):
        M[key].node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .28
    for key in ('pomelo', 'leaf', 'eye', 'blush_soft'):
        mat = M[key]
        tree = mat.node_tree
        color = tree.nodes.new('ShaderNodeVertexColor'); color.layer_name = 'Color'
        multiply = tree.nodes.new('ShaderNodeMixRGB'); multiply.blend_type = 'MULTIPLY'
        multiply.inputs[0].default_value = 1
        multiply.inputs[1].default_value = mat.diffuse_color
        tree.links.new(color.outputs['Color'], multiply.inputs[2])
        tree.links.new(multiply.outputs[0], tree.nodes.get('Principled BSDF').inputs['Base Color'])
        mat['palette_srgb'] = PALETTE.get(key, 'FFB6B6')
    for key, roughness, coat in [('pomelo', .36, .10), ('leaf', .38, .10), ('eye', .19, .08)]:
        p = M[key].node_tree.nodes.get('Principled BSDF')
        p.inputs['Roughness'].default_value = roughness
        p.inputs['Coat Weight'].default_value = coat
        p.inputs['Coat Roughness'].default_value = .23 if key == 'eye' else .36
    # Opaque PBR with warm gradients suggests waxy toy plastic without transparent shells.


def vertex_tint(ob, color_at):
    attribute = ob.data.color_attributes.get('Color') or ob.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='POINT')
    for vertex, item in zip(ob.data.vertices, attribute.data):
        item.color = tuple(color_at(vertex.co)) + (1,)
    ob.data.color_attributes.active_color = attribute
    return ob


def fruit_tint(p):
    # Keep bright green edges; preserve blue to avoid a lemon-yellow shift.
    edge = min(1, abs(p.x) / .39) ** 3
    low = max(0, min(1, (.55 - p.z) / .30))
    return (.94 + .06 * (1-edge), 1 - .012 * low, .92 + .08 * edge)


def head_q(x, z):
    t = (z - HEAD_Z) / HEAD_C
    return abs(t) ** HEAD_P + abs(x / (HEAD_A * (1 - .17 * t))) ** HEAD_P


def head_y(x, z, back=False):
    depth = HEAD_B * max(0, 1 - head_q(x, z)) ** (1 / HEAD_P)
    return depth if back else -depth


def face_y(x, z):
    return head_y(x, z) + .006


def face_boundary(a):
    x = .336 * math.cos(a)
    sine = math.sin(a)
    z = FACE_Z + (.267 if sine > 0 else .235) * sine
    if sine > 0:
        z -= .076 * math.exp(-(abs(x) / .090) ** 1.25)
    return x, z


def head_boundary(x, z):
    dx, dz = x, z - FACE_Z
    low, high = 1.0, 4.0
    for _ in range(42):
        t = (low + high) / 2
        if head_q(t * dx, FACE_Z + t * dz) < 1:
            low = t
        else:
            high = t
    return low * dx, FACE_Z + low * dz


def orient_front(ob):
    if sum(p.normal.y * p.area for p in ob.data.polygons) > 0:
        bm = bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(ob.data); bm.free()
    return ob


def radial_patch(name, boundary, center, surface, mat, parent, rings=7, dome=0):
    n = len(boundary)
    cx, cz = center
    verts = [(cx, surface(cx, cz) - dome, cz)]
    for j in range(1, rings + 1):
        r = j / rings
        for bx, bz in boundary:
            x, z = cx + r * (bx - cx), cz + r * (bz - cz)
            y = surface(x, z) - dome * max(0, 1 - r * r) ** .65
            verts.append((x, y, z))
    faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    for j in range(rings - 1):
        a, b = 1 + j * n, 1 + (j + 1) * n
        for i in range(n):
            k = (i + 1) % n
            faces.append((a + i, b + i, b + k, a + k))
    return orient_front(mesh(name, verts, faces, mat, parent))


def ellipse_patch(name, x, z, rx, rz, mat, parent, offset=.002, dome=.001, surface=face_y, segments=32, rings=5):
    boundary = [(x + rx * math.cos(a), z + rz * math.sin(a)) for a in np.linspace(0, TAU, segments, endpoint=False)]
    return radial_patch(name, boundary, (x, z), lambda xx, zz: surface(xx, zz) - offset, mat, parent, rings, dome)


def smile_boundary(expression, n=96):
    if expression == 'surprised':
        return [(.024 * math.cos(a), .437 + .038 * math.sin(a)) for a in np.linspace(0, TAU, n, endpoint=False)]
    width = .084 if expression == 'laugh' else .079
    return [(width * math.cos(a), .454 + (.008 if math.sin(a) >= 0 else .104) * math.sin(a))
            for a in np.linspace(0, TAU, n, endpoint=False)]


def build_head(parent, expression):
    n = 96
    boundary = [face_boundary(a) for a in np.linspace(0, TAU, n, endpoint=False)]
    outer = [head_boundary(x, z) for x, z in boundary]
    verts, faces = [], []
    # Cosine spacing concentrates samples at the silhouette for a smooth side view.
    for t, lip in zip((0, .012, .035, .075, .12, .18, .25, .32, .39, .46, .53, .60,
                       .67, .74, .80, .85, .89, .925, .952, .973, .986, .994, .999, 1),
                      (.006, .002, -.003, -.003, -.001) + (0,)*19):
        for (ix, iz), (ox, oz) in zip(boundary, outer):
            x, z = ix * (1 - t) + ox * t, iz * (1 - t) + oz * t
            verts.append((x, head_y(x, z) + lip, z))
    for j in range(1, 20):
        t = 1 - math.cos(math.pi * j / 40)
        for ox, oz in outer:
            x, z = ox * (1 - t), FACE_Z + (oz - FACE_Z) * (1 - t)
            verts.append((x, head_y(x, z, True), z))
    ring_count = len(verts) // n
    for j in range(ring_count-1):
        for i in range(n):
            k = (i + 1) % n
            faces.append((j * n + i, j * n + k, (j + 1) * n + k, (j + 1) * n + i))
    rear = len(verts); verts.append((0, head_y(0, FACE_Z, True), FACE_Z))
    for i in range(n):
        faces.append(((ring_count-1) * n + i, (ring_count-1) * n + (i + 1) % n, rear))
    # A shallow crown dip gives the paired stems a soft seat.
    verts = [(x, y, z - .005 * math.exp(-(x / .032) ** 2 - (y / .038) ** 2) * max(0, min(1, (z - .87) / .04))) for x, y, z in verts]
    shell = mesh('Head/PomeloShell', verts, faces, M['pomelo'], parent, outline=.00085)
    vertex_tint(shell, fruit_tint)
    shell['shape'] = 'Pear profile, broad cheeks, tapered crown; continuous green shell with recessed face opening'
    if expression in ('thinking', 'sad'):
        radial_patch('Head/CreamFaceMask', boundary, (0, FACE_Z), face_y, M['cream'], parent, 14)
    else:
        # A real opening lets the dark mouth recede behind the cream surface.
        opening = smile_boundary(expression, n)
        mask_verts, mask_faces = [], []
        for j in range(15):
            t = j / 14
            for (ix, iz), (ox, oz) in zip(opening, boundary):
                x, z = ix * (1-t) + ox*t, iz * (1-t) + oz*t
                mask_verts.append((x, face_y(x, z), z))
        for j in range(14):
            for i in range(n):
                k = (i + 1) % n
                mask_faces.append((j*n+i, j*n+k, (j+1)*n+k, (j+1)*n+i))
        orient_front(mesh('Head/CreamFaceMask', mask_verts, mask_faces, M['cream'], parent))
    return shell


def surface_stroke(name, points, radius, mat, parent, offset=.003):
    return rounded_stroke(name, [(x, face_y(x, z) - offset, z) for x, z in points], radius, mat, parent, sides=8)


def mouth(parent, expression):
    name = 'Face/' + expression.title() + '/Mouth'
    if expression in ('thinking', 'sad'):
        rx = .029 if expression == 'sad' else .022
        pts = [(rx * t, .425 + .011 * (1 - t * t)) for t in np.linspace(-1, 1, 18)]
        surface_stroke(name + '_Frown', pts, .0042, M['eye'], parent)
    elif expression == 'surprised':
        radial_patch(name + '_OpenO', smile_boundary(expression), (0, .437), face_y, M['mouth'], parent, 6, -.010)
        ellipse_patch(name + '_Tongue', 0, .417, .016, .012, M['tongue'], parent, -.003, .002)
    else:
        radial_patch(name + '_OpenSmile', smile_boundary(expression), (0, .416), face_y, M['mouth'], parent, 7, -.012)
        ellipse_patch(name + '_Tongue', 0, .384, .056, .030, M['tongue'], parent, -.003, .005, segments=40)


def face_features(parent, expression):
    group = empty('Expression_' + expression.title(), parent)
    group['expression'] = expression
    for side, label in [(-1, 'L'), (1, 'R')]:
        cx, cz = side * .148, .557
        prefix = 'Face/' + expression.title() + '/' + label
        if expression == 'laugh':
            pts = [(cx + .041 * math.cos(a), cz - .006 + .041 * math.sin(a)) for a in np.linspace(.12, math.pi - .12, 24)]
            surface_stroke(prefix + '_LaughEye', pts, .008, M['eye'], group)
        elif expression == 'wink' and side == 1:
            surface_stroke(prefix + '_WinkEye', [(cx + .029, cz + .024), (cx - .026, cz), (cx + .029, cz - .024)], .007, M['eye'], group)
        else:
            rx, rz = (.051, .074) if expression != 'sad' else (.046, .065)
            eye = ellipse_patch(prefix + '_Eye', cx, cz, rx, rz, M['eye'], group, .003, .018, segments=40, rings=7)
            vertex_tint(eye, lambda p: (.22, .22, .19))
            def eye_surface(x, z, cx=cx, cz=cz, rx=rx, rz=rz):
                q = ((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2
                return face_y(x, z) - .003 - .018 * max(0, 1 - q) ** .65
            ellipse_patch(prefix + '_WhiteHighlight', cx + .010, cz + .030, .017, .022, M['white'], group, .0014, .001, eye_surface, 24, 4)
        blush = ellipse_patch(prefix + '_Blush', side * .244, .461, .042, .033, M['blush_soft'], group, .0007, .0005, segments=32, rings=6)
        def blush_color(p, side=side):
            r = math.sqrt(((p.x - side * .244) / .042) ** 2 + ((p.z - .461) / .033) ** 2)
            fade = max(0, min(1, (r - .68) / .32)) ** 1.5
            return tuple(a * (1-fade) + b*fade for a,b in zip(rgba(PALETTE['blush'])[:3], rgba(PALETTE['cream'])[:3]))
        vertex_tint(blush, blush_color)
        if expression == 'sad':
            pts = [(cx + side * t, .642 - .38 * t) for t in np.linspace(-.018, .021, 12)]
            surface_stroke(prefix + '_WorriedBrow', pts, .0032, M['eye'], group)
    mouth(group, expression)
    return group


def leaf(parent, side):
    name = 'Leaves/' + ('L' if side < 0 else 'R')
    # A small solid lens with a gently swept central ridge and softly pointed ends.
    length = .176 if side < 0 else .167
    axis = Vector((side * .87, -.24 if side < 0 else .30, .49)).normalized()
    cross = Vector((-side * .49, 0, .87)).normalized()
    normal = axis.cross(cross).normalized()
    if normal.y > 0:
        normal = -normal
    origin = Vector((side * .010, .004, .918))
    n, rows = 12, 16
    verts = [origin]
    for j in range(1, rows):
        t = j / rows
        width = .042 * math.sin(math.pi * t) ** .85
        thickness = .014 * math.sin(math.pi * t)
        center = origin + axis * (length * t) + Vector((0, -.023 * math.sin(math.pi * t), .003 * math.sin(math.pi * t)))
        for i in range(n):
            a = TAU * i / n
            verts.append(center + cross * (width * math.cos(a)) + normal * (thickness * math.sin(a)))
    end = len(verts); verts.append(origin + axis * length)
    faces = [(0, 1 + (i + 1) % n, 1 + i) for i in range(n)]
    for j in range(rows - 2):
        for i in range(n):
            a, b = 1 + j * n + i, 1 + j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    for i in range(n):
        faces.append((1 + (rows - 2) * n + i, 1 + (rows - 2) * n + (i + 1) % n, end))
    # Keep the complete blade height within the board's 7-9% target, including its width.
    verts = [(v[0], v[1], origin.z + .85 * (v[2] - origin.z)) for v in verts]
    blade = mesh(name + '_Blade', verts, faces, M['leaf'], parent, outline=.00065)
    def leaf_color(p):
        t = max(0, min(1, (p - origin).dot(axis) / length))
        middle = math.sin(math.pi * t)
        return (.88 + .12 * middle, .90 + .10 * middle, .60 + .20 * middle)
    vertex_tint(blade, leaf_color)
    pts = []
    for t in np.linspace(.09, .93, 20):
        c = origin + axis * (length * t) + Vector((0, -.023 * math.sin(math.pi * t), .003 * math.sin(math.pi * t)))
        pts.append(c + normal * (.014 * math.sin(math.pi * t) + .0007))
    pts = [(v[0], v[1], origin.z + .85 * (v[2] - origin.z)) for v in pts]
    tube(name + '_Midrib', pts, .0012, M['vein'], parent, 6)


def lobed_mesh(name, loc, lobes, parent, blend=.008):
    # Radial union of overlapping ellipsoids: a single continuous surface with
    # deliberate lobes, rather than barely visible bumps on a capsule.
    ob = ellipsoid(name, loc, (1, 1, 1), M['cream'], parent, 36, 20)
    for vertex in ob.data.vertices:
        direction = vertex.co.normalized()
        radius = 0
        for center, scale in lobes:
            d = [direction[i] / scale[i] for i in range(3)]
            c = [center[i] / scale[i] for i in range(3)]
            a = sum(v*v for v in d)
            b = sum(v*w for v, w in zip(d, c))
            discriminant = b*b - a*(sum(v*v for v in c)-1)
            if discriminant < 0:
                continue
            candidate = (b + math.sqrt(discriminant)) / a
            overlap = max(0, blend - abs(radius-candidate)) / blend
            radius = max(radius, candidate) + blend * overlap*overlap / 4
        vertex.co = direction * radius
    ob.data.update()
    return ob


def mitten(name, loc, side, parent, raised=False):
    hand = lobed_mesh(name, loc, [
        ((0, 0, 0), (.050, .050, .051)),
        ((-side*.043, -.020, .012), (.028, .032, .029)),
    ], parent, blend=.009)
    if raised:
        for v in hand.data.vertices:
            v.co *= .90
    add_outline(hand, .00050)
    hand.rotation_euler.y = side * (-.20 if raised else .12)
    hand['shape'] = 'Round palm with a prominent rounded inner thumb, smoothly joined'
    return hand


def foot_mesh(label, side, parent):
    foot = lobed_mesh('Body/' + label + '_CreamFoot', (side * .115, -.040, 0), [
        ((0, .006, 0), (.080, .077, .059)),
        ((-.033, -.050, .009), (.044, .054, .058)),
        (( .033, -.050, .009), (.044, .054, .058)),
    ], parent, blend=.012)
    foot.location.z = -min(v.co.z for v in foot.data.vertices) + .0006
    foot.data.materials.append(M['sole'])
    for p in foot.data.polygons:
        if sum(foot.data.vertices[i].co.z for i in p.vertices) / len(p.vertices) < -.050:
            p.material_index = 1
    foot.data.update()
    add_outline(foot, .00055)
    foot.rotation_euler.z = side * math.radians(10)
    foot['shape'] = 'Rounded heel and two full toe lobes with a visible cleft; warm underside'
    return foot


def neck_blend(parent, torso):
    # A tangent fillet covers the intersecting rear/side surfaces. The original
    # head, face rim and torso stay editable; no front mask vertices are altered.
    head = next(ob for ob in descendants(parent.parent)
                if ob.name.startswith('Head/PomeloShell') and not ob.name.endswith('__Outline'))
    surfaces = []
    for ob in (head, torso):
        ob.data.calc_loop_triangles()
        vertices = [v.co+ob.location for v in ob.data.vertices]
        triangles = [tuple(t.vertices) for t in ob.data.loop_triangles]
        normals = [v.normal.copy() for v in ob.data.vertices]
        surfaces.append((BVHTree.FromPolygons(vertices, triangles, all_triangles=True), vertices, triangles, normals))

    def samples(angle, z):
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        values = []
        for tree, vertices, triangles, normals in surfaces:
            hit, _, index, distance = tree.ray_cast(Vector((0, .025, z)), direction, .6)
            if hit is None:
                values.append((0, direction))
            else:
                indices = triangles[index]
                normal = barycentric_transform(hit, *(vertices[i] for i in indices),
                                               *(normals[i] for i in indices)).normalized()
                values.append((distance, normal))
        return values

    def radii(angle, z):
        return tuple(sample[0] for sample in samples(angle, z))

    start, end = -.55, math.pi+.55

    def width(angle):
        t = max(0, min(1, (angle-start)/.30, (end-angle)/.30))
        return .0001 + .038*t*t*(3-2*t)

    def point(angle, z):
        rh, rt = radii(angle, z)
        k = width(angle)
        r = max(rh, rt) + max(0, k-abs(rh-rt))**2/(4*k)
        return Vector((r*math.cos(angle), .025+r*math.sin(angle), z))

    vertices, normals, faces = [], [], []
    columns, rows = 48, 10
    for i in range(columns+1):
        angle = start+(end-start)*i/columns
        limits = []
        for sign in (-1, 1):
            low, high = .276, .354
            for _ in range(32):
                z = (low+high)/2
                rh, rt = radii(angle, z)
                if rh-rt < sign*width(angle):
                    low = z
                else:
                    high = z
            limits.append((low+high)/2)
        for j in range(rows+1):
            z = limits[0]+(limits[1]-limits[0])*j/rows
            vertices.append(point(angle, z))
            (rh, nh), (rt, nt) = samples(angle, z)
            h = max(0, min(1, .5+.5*(rh-rt)/width(angle)))
            direction = Vector((math.cos(angle), math.sin(angle), 0))
            # Match the existing smooth shading at both boundaries, including
            # interpolation on the actual polygonal head rather than an ideal sphere.
            normal = h*nh/max(.05, nh.dot(direction)) + (1-h)*nt/max(.05, nt.dot(direction))
            normals.append(normal.normalized())
    for i in range(columns):
        for j in range(rows):
            a = i*(rows+1)+j
            faces.append((a, a+rows+1, a+rows+2, a+1))
    collar = mesh('Body/NeckFillet', vertices, faces, M['pomelo'], parent)
    # Recalculation on an open concave strip can choose inward winding. Match
    # the analytic outward normals explicitly, including for glTF culling.
    if sum(p.normal.x*p.center.x + p.normal.y*(p.center.y-.025)
           for p in collar.data.polygons) < 0:
        bm = bmesh.new(); bm.from_mesh(collar.data)
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(collar.data); bm.free()
    vertex_tint(collar, fruit_tint)
    collar.data.normals_split_custom_set_from_vertices(normals)
    collar['shape'] = 'Tangent rear/side fillet, smooth radial union of head and torso'


def body(parent, pose, expression):
    group = empty('Body', parent)
    torso = ellipsoid('Body/Torso', (0, .025, .208), (.239, .148, .147), M['pomelo'], group, 36, 22, 2.4)
    vertex_tint(torso, lambda p: fruit_tint(p + torso.location))
    neck_blend(group, torso)
    def belly_surface(x, z):
        q = abs(x / .239) ** 2.4 + abs((z - .208) / .147) ** 2.4
        return .025 - .148 * max(.001, 1 - q) ** (1 / 2.4)
    ellipse_patch('Body/CreamBelly', 0, .169, .123, .077, M['cream'], group, .0018, .002, belly_surface, 48, 8)
    for side, label in [(-1, 'L'), (1, 'R')]:
        foot_mesh(label, side, group)
        if expression in ('thinking', 'sad') and side == 1:
            a, b, c, d = [Vector(v) for v in ((.204, -.020, .257), (.210, -.13, .263), (.193, -.19, .298), (.181, -.226, .335))]
            arm_points = [(1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d for t in np.linspace(0, 1, 18)]
            tube('Body/R_RaisedForearm', arm_points, .024, M['cream'], group, 10)
            mitten('Body/R_ChinMitten', (.181, -.226, .354), side, group, raised=True)
        else:
            x, z = (.246, .253) if pose == 'hero' else (.241, .207)
            mitten('Body/' + label + '_CreamMitten', (side * x, -.088, z), side, group)
    return group


def build_character(name='PomeloStemMascot', expression='happy', pose='hero'):
    root = empty(name)
    root['expression'] = expression
    root['pose'] = pose
    root['palette'] = json.dumps(PALETTE, sort_keys=True)
    root['units'] = 'metres'
    head = empty('Head', root)
    build_head(head, expression)
    face_features(head, expression)
    leaves = empty('Leaves', root)
    ellipsoid('Leaves/Stem', (0, .004, .918), (.010, .011, .022), M['leaf'], leaves, 16, 12, 2.3, .0006)
    leaf(leaves, -1); leaf(leaves, 1)
    body(root, pose, expression)
    normalize_character(root)
    return root


def visibility(root, visible):
    for ob in descendants(root):
        ob.hide_render = not visible
        ob.hide_set(not visible)


def text_geometry(name, content, loc, size, parent):
    data = bpy.data.curves.new(name + '_Bfont', 'FONT')
    data.body = content; data.size = size; data.align_x = 'CENTER'; data.align_y = 'CENTER'
    data.resolution_u = 3; data.extrude = .00025
    ob = bpy.data.objects.new(name, data); SCENE.collection.objects.link(ob)
    ob.parent = parent; ob.location = loc; ob.rotation_euler.x = math.pi / 2
    data.materials.append(M['edge'])
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.convert(target='MESH')
    return ob


def build_kit(root):
    row = empty('KIT_ExpressionMountRow', root, (0, 1.55, 0))
    row['description'] = 'Six complete expression figures on a separate visible row; local character feet remain at zero'
    mounts = []
    for i, expression in enumerate(EXPRESSIONS):
        mount = empty(f'Mount_{i + 1:02d}_Expression_{expression.title()}', row, ((i - 2.5) * .93, 0, 0))
        figure = build_character('KitFigure_' + expression.title(), expression, 'hero')
        figure.parent = mount
        # Base and label sit behind the foot plane, preserving the contract floor.
        ellipsoid('MountBase_' + expression.title(), (0, .035, .0004), (.425, .185, .00035), M['mount'], mount, 32, 10, 3)
        mounts.append(mount)
    return row, mounts


def setup_studio():
    studio = empty('STUDIO_SourceOnly')
    # Cycles does not honor Material.use_backface_culling. Reproduce glTF's culling
    # with a source-only shader after exports, including on reimported hull meshes.
    ink = bpy.data.materials.new('Studio only | ray-correct inverted hull culling')
    ink.use_nodes = True
    nt = ink.node_tree; nt.nodes.clear()
    output = nt.nodes.new('ShaderNodeOutputMaterial')
    geometry = nt.nodes.new('ShaderNodeNewGeometry')
    emission = nt.nodes.new('ShaderNodeEmission'); emission.inputs[0].default_value = rgba('3C542B')
    light_path = nt.nodes.new('ShaderNodeLightPath')
    nt.links.new(light_path.outputs['Is Camera Ray'], emission.inputs['Strength'])
    transparent = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(geometry.outputs['Backfacing'], mix.inputs[0])
    nt.links.new(emission.outputs[0], mix.inputs[1]); nt.links.new(transparent.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], output.inputs['Surface'])
    for ob in SCENE.objects:
        if ob.type == 'MESH' and ('__Outline' in ob.name or '_InvertedHullMesh' in ob.name):
            ob.data.materials.clear(); ob.data.materials.append(ink)
            ob.visible_shadow = False
            ob.visible_diffuse = False
            ob.visible_glossy = False
            ob.visible_transmission = False
    world = bpy.data.worlds.new('Soft pale-green studio')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = rgba('FFFCEF')
    world.node_tree.nodes['Background'].inputs[1].default_value = .42
    SCENE.world = world
    for name, loc, power, size, color in [
        ('Key', (-1.5, -2, 2.8), 125, 1.9, 'FFF3D4'),
        ('Fill', (2, -1.8, 1.8), 55, 2.0, 'FFFAEC'),
        ('Rim', (1.2, 1.8, 2.5), 85, 2.2, 'FFFFDC'),
        ('FrontSoftbox', (0, -3, .7), 20, 2.0, 'FFFBEF'),
        ('LowBounce', (0, -2, .25), 30, 2.0, 'FFF0CA'),
    ]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        ob = bpy.context.object; ob.name = 'Studio_' + name; ob.parent = studio
        ob.data.energy = power * .65; ob.data.shape = 'DISK'; ob.data.size = size
        ob['studio_base_location'] = loc
        ob.data.use_shadow = True; ob.data.color = rgba(color)[:3]; aim(ob, (0, 0, .5))
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.001))
    floor = bpy.context.object; floor.name = 'Studio_ShadowCatcher'; floor.parent = studio
    floor.is_shadow_catcher = True
    floor.data.materials.append(material('Studio floor', 'FFFCEF', .85))
    bpy.ops.object.camera_add(location=(1.6, -3.3, 1.0))
    camera = bpy.context.object; camera.name = 'PreviewCamera'; camera.parent = studio
    camera.data.type = 'ORTHO'; camera.data.ortho_scale = 1.20
    SCENE.camera = camera
    SCENE.render.engine = 'CYCLES'
    SCENE.cycles.samples = 24
    SCENE.cycles.use_denoising = True
    SCENE.cycles.seed = 0
    SCENE.cycles.use_animated_seed = False
    SCENE.cycles.max_bounces = 6
    SCENE.render.resolution_x = 768; SCENE.render.resolution_y = 768
    SCENE.render.resolution_percentage = 100
    SCENE.render.image_settings.file_format = 'PNG'; SCENE.render.image_settings.color_mode = 'RGBA'
    SCENE.render.film_transparent = True
    SCENE.view_settings.view_transform = 'Standard'; SCENE.view_settings.look = 'None'
    SCENE.view_settings.exposure = -.68
    return studio


def apply_compositing():
    tree = bpy.data.node_groups.new('Pale green studio background', 'CompositorNodeTree')
    SCENE.compositing_node_group = tree
    tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    out = tree.nodes.new('NodeGroupOutput')
    layer = tree.nodes.new('CompositorNodeRLayers')
    yy, xx = np.mgrid[0:1024, 0:1024].astype(np.float32)
    xx /= 1023; yy /= 1023
    t = np.clip(.20 + .65 * yy + .24 * np.exp(-((xx - .38) ** 2 + (yy - .68) ** 2) / .20), 0, 1)
    lower, upper = np.array(rgba('EAF1E1')[:3]), np.array(rgba('FFFFFF')[:3])
    pixels = np.ones((1024, 1024, 4), dtype=np.float32)
    pixels[:, :, :3] = lower * (1 - t[:, :, None]) + upper * t[:, :, None]
    # Exposure applies after compositing; compensate the backdrop only.
    pixels[:, :, :3] *= 2 ** (-SCENE.view_settings.exposure)
    backdrop = bpy.data.images.new('Studio pale-green gradient', width=1024, height=1024, alpha=True, float_buffer=True)
    backdrop.pixels.foreach_set(pixels.ravel()); backdrop.pack()
    im = tree.nodes.new('CompositorNodeImage'); im.image = backdrop
    over = tree.nodes.new('CompositorNodeAlphaOver')
    over.inputs['Factor'].default_value = 1
    tree.links.new(im.outputs['Image'], over.inputs['Background'])
    tree.links.new(layer.outputs['Image'], over.inputs['Foreground'])
    tree.links.new(over.outputs['Image'], out.inputs['Image'])


def render_one(name, loc, target=(0, 0, .5), scale=1.20):
    SCENE.objects['Studio_ShadowCatcher'].hide_render = name == 'expressions'
    SCENE.camera.location = loc; aim(SCENE.camera, target); SCENE.camera.data.ortho_scale = scale
    angle = math.atan2(loc[0] - target[0], -(loc[1] - target[1]))
    for light in SCENE.objects:
        if light.type == 'LIGHT' and 'studio_base_location' in light:
            x, y, z = light['studio_base_location']
            light.location = (target[0] + x*math.cos(angle)-y*math.sin(angle), target[1] + x*math.sin(angle)+y*math.cos(angle), z + target[2] - .5)
            aim(light, target)
    SCENE.render.filepath = str(ROOT / 'previews' / (name + '.png'))
    print('RENDER_VIEW', name, flush=True)
    bpy.ops.render.render(write_still=True)


def image_canvas(name, items, width, height, background=(.96, .98, .93, 1), labels=()):
    canvas = np.empty((height, width, 4), dtype=np.float32); canvas[:] = background
    loaded = []
    for item in items:
        path, x, y, tw, th, *crop = item
        im = bpy.data.images.load(str(path), check_existing=False); loaded.append(im)
        iw, ih = im.size
        pix = np.asarray(im.pixels[:], dtype=np.float32).reshape(ih, iw, 4)
        if crop:
            sx, sy, iw, ih = crop[0]
            pix = pix[sy:sy+ih, sx:sx+iw]
        fx = np.clip((np.arange(tw)+.5)*iw/tw-.5, 0, iw-1)
        fy = np.clip((np.arange(th)+.5)*ih/th-.5, 0, ih-1)
        ix, iy = fx.astype(int), fy.astype(int)
        wx, wy = (fx-ix)[None, :, None], (fy-iy)[:, None, None]
        top = pix[iy[:, None], ix[None, :]]*(1-wx) + pix[iy[:, None], np.minimum(ix+1,iw-1)[None, :]]*wx
        bottom = pix[np.minimum(iy+1,ih-1)[:, None], ix[None, :]]*(1-wx) + pix[np.minimum(iy+1,ih-1)[:, None], np.minimum(ix+1,iw-1)[None, :]]*wx
        canvas[y:y + th, x:x + tw] = top*(1-wy) + bottom*wy
    # Compact built-in bitmap captions keep comparison sheets font-independent.
    glyphs = {
        'R': ('11110','10001','10001','11110','10100','10010','10001'),
        'F': ('11111','10000','10000','11110','10000','10000','10000'),
        'O': ('01110','10001','10001','10001','10001','10001','01110'),
        'N': ('10001','11001','11001','10101','10011','10011','10001'),
        'T': ('11111','00100','00100','00100','00100','00100','00100'),
        'S': ('01111','10000','10000','01110','00001','00001','11110'),
        'I': ('11111','00100','00100','00100','00100','00100','11111'),
        'D': ('11110','10001','10001','10001','10001','10001','11110'),
        'E': ('11111','10000','10000','11110','10000','10000','11111'),
        'X': ('10001','10001','01010','00100','01010','10001','10001'),
        'P': ('11110','10001','10001','11110','10000','10000','10000'),
        '1': ('00100','01100','00100','00100','00100','00100','01110'),
        '2': ('01110','10001','00001','00010','00100','01000','11111'),
        '0': ('01110','10001','10011','10101','11001','10001','01110'),
        '4': ('10010','10010','10010','11111','00010','00010','00010'),
        '5': ('11111','10000','10000','11110','00001','00001','11110'),
        '6': ('01110','10000','10000','11110','10001','10001','01110'),
        '7': ('11111','00001','00010','00100','01000','01000','01000'),
        '8': ('01110','10001','10001','01110','10001','10001','01110'),
        '9': ('01110','10001','10001','01111','00001','00001','01110'),
        '3': ('11110','00001','00001','01110','00001','00001','11110'),
        'Q': ('01110','10001','10001','10001','10101','10010','01101'),
        ' ': ('00000',)*7,
    }
    for caption, x, y in labels:
        for i, letter in enumerate(caption):
            for j, row in enumerate(glyphs[letter]):
                for k, pixel in enumerate(row):
                    if pixel == '1':
                        px, py = x + (i*6+k)*4, y+(6-j)*4
                        canvas[py:py+4, px:px+4] = (.10, .24, .08, 1)
    result = bpy.data.images.new(name, width=width, height=height, alpha=True)
    result.pixels.foreach_set(canvas.ravel()); result.filepath_raw = str(ROOT / 'previews' / (name + '.png'))
    result.file_format = 'PNG'; result.save()
    for im in loaded + [result]:
        bpy.data.images.remove(im)


def compose_expression_atlas():
    # Keep the built-in-font captions, but compare expressions under identical
    # studio lighting rather than the different positions of the 3x2 stage.
    atlas = ROOT / 'previews/expressions.png'
    pixel_scale=SCENE.render.resolution_x/1024
    def crop(values):return tuple(round(v*pixel_scale) for v in values)
    items = []
    for i, expression in enumerate(EXPRESSIONS):
        row, col = 1-i//3, i%3
        items.append((ROOT/'previews'/f'expression-{expression}.png', col*341, row*512+64,
                      341, 436, crop((112, 0, 800, 1024))))
    items.extend([(atlas, 0, 0, 1024, 48, crop((0, 36, 1024, 48))),
                  (atlas, 0, 512, 1024, 48, crop((0, 520, 1024, 48)))])
    image_canvas('expressions', items, 1024, 1024, background=(.96, .98, .93, 1))


def render_views(root, row, mounts, quick=False):
    if quick:
        SCENE.cycles.samples = 16
    visibility(row, False)
    render_one('front', (0, -4, .68))
    if not quick:
        render_one('side', (4, 0, .5))
        render_one('back', (0, 4, .5))
    render_one('3q', (1.6, -3.6, 1.10), scale=1.23)
    if not quick:
        # Render each real kit mount without moving it, then make a legible 3x2 atlas.
        for ob in descendants(root):
            if ob not in descendants(row):
                ob.hide_render = True
        for i, mount in enumerate(mounts):
            visibility(mount, True)
            bpy.context.view_layer.update()
            center = mount.matrix_world.translation
            name = 'expression-' + EXPRESSIONS[i]
            render_one(name, (center.x, center.y - 4, .68), (center.x, center.y, .5), 1.17)
            visibility(mount, False)
        # A temporary 3x2 render layout makes the atlas readable; the GLB remains one row.
        saved_locations = [m.location.copy() for m in mounts]
        saved_row = row.location.copy()
        row.location = (0, 0, 0)
        labels = []
        for i, mount in enumerate(mounts):
            visibility(mount, True)
            mount.location = ((i % 3 - 1) * .94, 0, .67 if i < 3 else -.67)
            for ob in descendants(mount):
                if ob.name.startswith('MountLabel_'):
                    ob.hide_render = True
            labels.append(text_geometry('AtlasLabel_' + EXPRESSIONS[i], EXPRESSIONS[i].title(), (0, -.32, -.080), .068, mount))
        render_one('expressions', (0, -6, .5), (0, 0, .5), 2.88)
        for label in labels:
            bpy.data.objects.remove(label, do_unlink=True)
        row.location = saved_row
        for mount, loc in zip(mounts, saved_locations):
            mount.location = loc
        visibility(root, True); visibility(row, False)
        compose_expression_atlas()
    # Private artwork is never read, copied or packed by the generator.
    if not quick:
        baseline = ROOT / 'reports/r3/previews'
        views = ('front', '3q', 'side')
        if all((baseline / (view+'.png')).is_file() for view in views):
            items, labels = [], []
            for row_index, folder in enumerate((ROOT / 'previews', baseline)):
                for col, view in enumerate(views):
                    items.append((folder / (view+'.png'), col*768, row_index*816, 768, 768))
                    labels.append((f'R{4-row_index} {view.upper()}', col*768+24, row_index*816+778))
            image_canvas('compare-r3-r4-colour', items, 2304, 1632, labels=labels)
        else:
            print('OPTIONAL_R3_COMPARISON_SKIPPED baseline renders are absent', flush=True)


def render_imported_clips():
    """Twelve sampled frames per clip, rendered exclusively from delivered GLB."""
    global SCENE
    bpy.ops.wm.read_factory_settings(use_empty=True)
    SCENE=bpy.context.scene;SCENE.render.fps=24
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'exports/pomelo-stem-mascot.glb'))
    setup_studio();apply_compositing()
    SCENE.render.resolution_x=SCENE.render.resolution_y=384
    SCENE.cycles.samples=16
    SCENE.camera.location=(1.0,-4,1.04);aim(SCENE.camera,(.16,0,.50))
    SCENE.camera.data.ortho_scale=1.50
    folder=ROOT/'previews/animation-frames';folder.mkdir(exist_ok=True)
    samples={'Idle':[0,5,11,16,22,27,33,38,44,49,55,60],
             'Wave':[0,3,6,9,12,15,18,21,24,27,30,36],
             'Blink':[0,12,24,28,30,31,33,35,36,38,48,72]}
    report={}
    for clip,frames in samples.items():
        views=[('front',(0,-4,.65))]
        if clip=='Wave':views.append(('3q',(1.6,-3.6,1.10)))
        for view,loc in views:
            SCENE.camera.location=loc;aim(SCENE.camera,(.04,0,.50));SCENE.camera.data.ortho_scale=1.30
            suffix='' if view=='front' else '-'+view
            items,labels=[],[]
            for i,frame in enumerate(frames):
                activate_clip(SCENE,clip,frame)
                path=folder/f'{clip.lower()}{suffix}-{frame:02d}.png'
                SCENE.render.filepath=str(path)
                print('RENDER_IMPORTED_ANIMATION',clip,view,frame,flush=True)
                bpy.ops.render.render(write_still=True)
                x,y=(i%4)*384,(2-i//4)*424
                items.append((path,x,y,384,384));labels.append((f'F{frame:02d}',x+16,y+392))
            image_canvas('anim-'+clip.lower()+suffix+'-strip',items,1536,1272,labels=labels)
            report[clip+suffix]={'frames':frames,'seconds':[v/24 for v in frames],
                               'view':view,'duration_seconds':CLIPS[clip]/24,
                               'source':'fresh import of default exported GLB'}
    (ROOT/'reports/animation-preview-samples.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    global SCENE
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--no-render', action='store_true')
    parser.add_argument('--expression', choices=EXPRESSIONS, default='happy')
    parser.add_argument('--pose', choices=('hero', 'stand'), default='hero')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    SCENE = bpy.context.scene
    SCENE.unit_settings.system = 'METRIC'; SCENE.unit_settings.scale_length = 1
    SCENE.render.fps = 24
    for name in ('exports', 'previews', 'reports'):
        (ROOT / name).mkdir(exist_ok=True)
    materials()
    root = build_character()
    rig = rig_character(root)
    metrics = {'blender_version': bpy.app.version_string, 'blender_build': bpy.app.build_hash.decode(), 'palette': PALETTE}
    metrics['default'] = export_glb(ROOT / 'exports/pomelo-stem-mascot.glb', descendants(root))
    metrics['default']['blender_bounds'] = world_bounds(descendants(root))
    assert metrics['default']['triangles'] < 40000
    assert metrics['default']['bytes'] < 2 * 1024 ** 2
    # Every deliverable has exactly the same requested scene-root name.
    root.name = 'Source_Hero'
    stand = build_character('PomeloStemMascot', 'happy', 'stand')
    rig_character(stand)
    metrics['stand'] = export_glb(ROOT / 'exports/pomelo-stem-mascot-stand.glb', descendants(stand))
    stand.name = 'Alternative_Stand'; visibility(stand, False)
    root.name = 'PomeloStemMascot'
    row, mounts = build_kit(root)
    bpy.context.view_layer.update()
    bind_kit(row, rig)
    metrics['kit'] = export_glb(ROOT / 'exports/pomelo-stem-mascot-kit.glb', descendants(root))
    assert metrics['kit']['bytes'] < 5 * 1024 ** 2
    visibility(row, False)
    if args.expression != 'happy' or args.pose != 'hero':
        root.name = 'Source_Hero'
        custom = build_character('PomeloStemMascot', args.expression, args.pose)
        rig_character(custom)
        metrics['custom'] = export_glb(ROOT / 'exports/pomelo-stem-mascot-custom.glb', descendants(custom))
        custom.name = 'Alternative_Custom'; visibility(custom, False)
        root.name = 'PomeloStemMascot'
    setup_studio(); apply_compositing()
    SCENE['asset_contract'] = 'Native metres; glTF +Y up, front +Z; feet Y=0; real geometry; no textures'
    SCENE['source_notes'] = 'Alternative_Stand and KIT_ExpressionMountRow hidden only for studio; kit exports all mounts visible'
    SCENE['generator'] = 'generate.py'
    SCENE.frame_start=0;SCENE.frame_end=CLIPS['Idle']
    rig.animation_data.action=next(t.strips[0].action for t in rig.animation_data.nla_tracks if t.name=='Idle')
    SCENE.frame_set(0)
    SCENE.camera.location = (1.6, -3.6, 1.1); aim(SCENE.camera, (0, 0, .5))
    bpy.ops.object.select_all(action='DESELECT'); root.select_set(True); bpy.context.view_layer.objects.active = root
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'pomelo-stem-mascot.blend'), compress=True)
    if not args.no_render:
        render_views(root, row, mounts, args.quick)
        if not args.quick: render_imported_clips()
    (ROOT / 'reports/generation.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print('GENERATION_COMPLETE', json.dumps(metrics), flush=True)


if __name__ == '__main__':
    main()
