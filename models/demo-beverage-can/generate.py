"""Reproducible Blender 4.0.2 source for the original DEMO beverage can."""
import bpy, bmesh, math
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT_NAME = "ASSET_DemoBeverageCan"
SEGMENTS = 96

def material(name, color, metallic=0.0, roughness=0.4):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*color, 1)
    node.inputs["Metallic"].default_value = metallic; node.inputs["Roughness"].default_value = roughness
    return mat

def mesh(name, vertices, faces, mat, parent):
    data = bpy.data.meshes.new(name); data.from_pydata(vertices, [], faces); data.update()
    bm = bmesh.new(); bm.from_mesh(data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(data); bm.free()
    obj = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(obj); obj.parent = parent; data.materials.append(mat)
    return obj

def lathe(name, profile, mat, parent, segments=SEGMENTS):
    vertices, rings = [], []
    for radius, z in profile:
        if radius == 0: rings.append([len(vertices)]); vertices.append((0, 0, z))
        else:
            rings.append(list(range(len(vertices), len(vertices) + segments)))
            vertices.extend((radius * math.cos(2 * math.pi * i / segments), radius * math.sin(2 * math.pi * i / segments), z) for i in range(segments))
    faces = []
    for a, b in zip(rings, rings[1:]):
        if len(a) == len(b) == 1: continue
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((a[0], b[i], b[j]) if len(a) == 1 else (a[i], b[0], a[j]) if len(b) == 1 else (a[i], b[i], b[j], a[j]))
    obj = mesh(name, vertices, faces, mat, parent)
    for face in obj.data.polygons: face.use_smooth = True
    return obj

def annulus(name, outer_radius, inner_x, inner_y, z, mat, parent, segments=SEGMENTS):
    vertices = []
    for i in range(segments):
        a = 2 * math.pi * i / segments; vertices.append((outer_radius * math.cos(a), outer_radius * math.sin(a), z))
    for i in range(segments):
        a = 2 * math.pi * i / segments; vertices.append((inner_x * math.cos(a), inner_y * math.sin(a), z))
    faces = [(i, (i + 1) % segments, segments + (i + 1) % segments, segments + i) for i in range(segments)]
    return mesh(name, vertices, faces, mat, parent)

def oval_wall(name, outer_x, outer_y, inner_x, inner_y, z0, z1, mat, parent, segments=48):
    vertices = []
    for z, rx, ry in ((z0, outer_x, outer_y), (z1, outer_x, outer_y), (z0, inner_x, inner_y), (z1, inner_x, inner_y)):
        vertices += [(rx * math.cos(2 * math.pi * i / segments), ry * math.sin(2 * math.pi * i / segments), z) for i in range(segments)]
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces += [(i, j, segments + j, segments + i), (2*segments+i, 3*segments+i, 3*segments+j, 2*segments+j), (segments+i, segments+j, 3*segments+j, 3*segments+i), (i, 2*segments+i, 2*segments+j, j)]
    return mesh(name, vertices, faces, mat, parent)

def oval_plate(name, rx, ry, z, thickness, mat, parent, segments=48):
    vertices = []
    for zz in (z, z + thickness): vertices += [(rx * math.cos(2 * math.pi * i / segments), ry * math.sin(2 * math.pi * i / segments), zz) for i in range(segments)]
    faces = []
    for i in range(1, segments - 1): faces += [(0, i + 1, i), (segments, segments + i, segments + i + 1)]
    for i in range(segments):
        j = (i + 1) % segments; faces.append((i, segments + i, segments + j, j))
    return mesh(name, vertices, faces, mat, parent)

def torus(name, major, minor, z, mat, parent, n=SEGMENTS, m=12):
    vertices, faces = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        for j in range(m):
            b = 2 * math.pi * j / m; vertices.append(((major + minor * math.cos(b)) * math.cos(a), (major + minor * math.cos(b)) * math.sin(a), z + minor * math.sin(b)))
    for i in range(n):
        for j in range(m): faces.append((i*m+j, ((i+1)%n)*m+j, ((i+1)%n)*m+(j+1)%m, i*m+(j+1)%m))
    obj = mesh(name, vertices, faces, mat, parent)
    for face in obj.data.polygons: face.use_smooth = True
    return obj

def cylindrical_label(name, radius, z0, z1, mat, parent, segments=SEGMENTS):
    vertices = [(radius * math.cos(2 * math.pi * i / segments), radius * math.sin(2 * math.pi * i / segments), z) for z in (z0, z1) for i in range(segments)]
    faces = [(i, (i + 1) % segments, segments + (i + 1) % segments, segments + i) for i in range(segments)]
    obj = mesh(name, vertices, faces, mat, parent); uv = obj.data.uv_layers.new(name="CylindricalSeamUV")
    # Put the centre of the artwork at Blender -Y, the Product Studio front.
    # The quarter-turn keeps the seam at the least-visible +X side.
    for i, poly in enumerate(obj.data.polygons):
        u0 = ((i - segments // 4) % segments) / segments
        u1 = u0 + 1.0 / segments
        for loop in poly.loop_indices:
            vi = obj.data.loops[loop].vertex_index; uv.data[loop].uv = ((u0 if vi % segments == i else u1), 0.0 if vi < segments else 1.0)
    return obj

def empty(name, parent, location):
    obj = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(obj); obj.parent = parent; obj.location = location; return obj

def key_action(obj, clip, path, frames):
    action = bpy.data.actions.new(f"{clip}_{obj.name}"); obj.animation_data_create(); obj.animation_data.action = action
    for frame, value in frames: setattr(obj, path, value); obj.keyframe_insert(path, frame=frame)
    for curve in action.fcurves:
        for key in curve.keyframe_points: key.interpolation = "LINEAR"
    obj.animation_data.action = None; track = obj.animation_data.nla_tracks.new(); track.name = clip; strip = track.strips.new(clip, 0, action); strip.extrapolation = "NOTHING"; track.mute = True
    return track

def aim(obj, target): obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

def export_glb(path):
    bpy.ops.object.select_all(action="DESELECT"); root = bpy.data.objects[ROOT_NAME]; root.select_set(True)
    for child in root.children_recursive: child.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True, export_apply=True, export_animations=True, export_nla_strips=True, export_frame_range=True, export_force_sampling=True, export_extras=True)

def build():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    for folder in ("sources", "exports", "previews", "reports", "textures"): HERE.joinpath(folder).mkdir(exist_ok=True)
    scene = bpy.context.scene; scene.unit_settings.system = "METRIC"; scene.unit_settings.scale_length = 1; scene.render.fps = 24; scene.frame_start = 0; scene.frame_end = 72
    root = bpy.data.objects.new(ROOT_NAME, None); bpy.context.collection.objects.link(root); root["units"] = "metres"; root["dimensions_m"] = "0.0665 x 0.115"; root["originality"] = "Original unbranded DEMO concept"; root["clip_contract"] = "OpenClose / Exploded; 0s rest, 1.5s open, 3s rest"
    teal = material("Can satin teal", (.03, .38, .42), .72, .28); aluminium = material("Brushed aluminium", (.62, .68, .70), .9, .22)
    lathe("BODY_HollowShell", [(0,.001),(.031,.001),(.033,.003),(.033,.110),(.0325,.114),(.0295,.114),(.0295,.010),(.0275,.006),(0,.006)], teal, root)
    torus("BASE_ConcaveFoot", .031, .0012, .002, aluminium, root); torus("RIM_NeckedUpper", .0322, .0011, .114, aluminium, root); torus("RIM_BaseBead", .032, .0008, .004, aluminium, root)
    top = empty("MOVABLE_Top", root, (0, 0, .114)); annulus("TOP_AperturePlate", .0302, .011, .016, 0, aluminium, top); torus("TOP_ApertureBead", .0134, .0010, .0012, aluminium, top, 64, 10); oval_wall("TOP_InnerApertureWall", .011, .016, .0098, .0148, -.0001, -.005, aluminium, top)
    # Both parts hinge at their rear edge and fold down into the aperture.
    flap = empty("MOVABLE_ScoreFlap", top, (0, .016, .001)); flap_plate = oval_plate("SCORE_Flap", .0105, .0155, -.00035, .0007, aluminium, flap, 48); flap_plate.location.y = -.016
    tab = empty("MOVABLE_Tab", top, (0, .016, .003)); ring = torus("TAB_PullRing", .006, .00055, 0, aluminium, tab, 64, 10); ring.location.y = -.010
    label = material("Original DEMO citrus label", (1,1,1), 0, .5); image = bpy.data.images.load(str(HERE / "textures" / "beverage-label.png")); image.pack(); tex = label.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = image; label.node_tree.links.new(tex.outputs["Color"], label.node_tree.nodes["Principled BSDF"].inputs["Base Color"]); cylindrical_label("LABEL_OriginalCitrusBand", .03325, .012, .103, label, root)
    openclose = [key_action(flap, "OpenClose", "rotation_euler", [(0,(0,0,0)),(36,(.95,0,0)),(72,(0,0,0))]), key_action(tab, "OpenClose", "rotation_euler", [(0,(0,0,0)),(36,(-1.05,0,0)),(72,(0,0,0))])]
    exploded = [key_action(top, "Exploded", "location", [(0,(0,0,.114)),(36,(0,0,.184)),(72,(0,0,.114))])]
    for track in openclose + exploded: track.mute = False
    scene.frame_set(0); bpy.context.view_layer.update(); export_glb(HERE / "exports" / "demo-beverage-can.glb")
    for track in openclose + exploded: track.mute = True
    scene.world.use_nodes = True; scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.19,.22,.27,1); scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .7
    for name, loc, power in [("Key",(-.15,-.2,.25),12),("Fill",(.18,-.05,.16),8),("Rim",(0,.15,.23),16)]: bpy.ops.object.light_add(type="AREA", location=loc); light=bpy.context.object; light.name="STUDIO_"+name; light.data.energy=power*.14; light.data.size=.12; aim(light,(0,0,.06))
    bpy.ops.object.camera_add(); scene.camera=bpy.context.object; scene.camera.name="STUDIO_Camera"; scene.camera.data.type="ORTHO"; scene.render.engine="BLENDER_EEVEE"; scene.render.resolution_x=640; scene.render.resolution_y=640; scene.render.resolution_percentage=100; scene.render.image_settings.file_format="PNG"
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "sources" / "demo-beverage-can.blend"))
    for name, loc, target, scale, clip, frame in [("hero",(.13,-.23,.17),(0,0,.06),.16,None,0),("rear",(.12,.23,.15),(0,0,.06),.16,None,0),("top",(.05,-.08,.28),(0,0,.08),.15,None,0),("opened",(.14,-.23,.22),(0,0,.09),.21,"OpenClose",36),("exploded",(.14,-.25,.24),(0,0,.11),.25,"Exploded",36)]:
        for track in openclose + exploded: track.mute = track.name != clip
        top.location=(0,0,.114); flap.rotation_euler=(0,0,0); tab.rotation_euler=(0,0,0)
        scene.frame_set(frame); bpy.context.view_layer.update(); scene.camera.location=loc; scene.camera.data.ortho_scale=scale; aim(scene.camera,target); scene.render.filepath=str(HERE / "previews" / (name+'.png')); bpy.ops.render.render(write_still=True)
    # Preview evaluation must never become the saved rest pose or source proof.
    for track in openclose + exploded: track.mute = True
    top.location=(0,0,.114); flap.rotation_euler=(0,0,0); tab.rotation_euler=(0,0,0)
    scene.frame_set(0); bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "sources" / "demo-beverage-can.blend"))

if __name__ == "__main__": build()
