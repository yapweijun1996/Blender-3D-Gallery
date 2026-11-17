"""Original deterministic baby grand piano; Blender 5.2.3, metres, no external assets."""
from pathlib import Path
import json
import math
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = "grand-piano"
ROOT = "ASSET_GrandPiano"
TARGET = Vector((0, 0, 0.83))
FOOTPRINT_SHIFT = 0.2975
LID_ANGLE = math.radians(-32)
MATERIAL_NAMES = ("Black lacquer", "Ivory keys", "Warm brass")


def material(name, rgb, metal=0, roughness=0.4):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    color = tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb) + (1,)
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = color
    return mat


def finish(obj, name, mat, root, bevel=0.001, segments=1):
    obj.name = name
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.parent = root
    if bevel:
        modifier = obj.modifiers.new("Soft manufactured edge", "BEVEL")
        modifier.width = min(bevel, min(obj.dimensions) * 0.45)
        modifier.segments = segments
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def box(name, location, dimensions, mat, root, bevel=0.001):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, root, bevel)


def rod(name, a, b, radius, mat, root, vertices=12):
    start, end = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=(end - start).length, location=(start + end) / 2)
    obj = bpy.context.object
    obj.rotation_euler = (end - start).to_track_quat("Z", "Y").to_euler()
    # Thin strings and pins need no bevel rings; smooth only the cylindrical sides.
    if radius < 0.005:
        for face in obj.data.polygons:
            face.use_smooth = len(face.vertices) == 4
    return finish(obj, name, mat, root, 0 if radius < 0.005 else 0.001)


def polygon(name, outline, bottom, top, mat, root, bevel=0.001):
    count = len(outline)
    vertices = [(x, y, z) for z in (bottom, top) for x, y in outline]
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    faces += [(i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return finish(obj, name, mat, root, bevel, segments=1)


def bezier(points, steps=12):
    a, b, c, d = [Vector(p) for p in points]
    return [tuple((1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d)
            for t in [i / steps for i in range(1, steps + 1)]]


def case_outline():
    # Counterclockwise outline: straight bass rim, rounded tail, concave treble bentside.
    outline = [(-0.75, -0.43), (0.75, -0.43), (0.75, -0.28)]
    outline += bezier(((0.75, -0.28), (0.75, 0.02), (0.39, 0.02), (0.33, 0.43)))
    outline += bezier(((0.33, 0.43), (0.29, 0.74), (0.12, 0.875), (-0.12, 0.875)))
    outline += bezier(((-0.12, 0.875), (-0.48, 0.875), (-0.75, 0.77), (-0.75, 0.49)))
    return outline


def rim(name, outline, mat, root):
    inner = [(x * 0.943, -0.39 + (y + 0.43) * 0.935) for x, y in outline]
    n = len(outline)
    vertices = [(x, y, z) for z in (0.78, 0.99) for ring in (outline, inner) for x, y in ring]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces += [(i, j, j+2*n, i+2*n), (i+n, i+3*n, j+3*n, j+n),
                  (i+2*n, j+2*n, j+3*n, i+3*n), (i, i+n, j+n, j)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    finish(obj, name, mat, root, 0.003, segments=2)
    return inner


def tapered_leg(name, top, bottom, width_top, width_bottom, mat, root):
    vertices = [(cx+sx*w/2, cy+sy*w/2, z) for (cx, cy, z), w in
                ((bottom, width_bottom), (top, width_top)) for sx, sy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    faces = [(3,2,1,0), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return finish(obj, name, mat, root, 0.004)


def white_key(name, left, right, left_notch, right_notch, mat, root):
    outline = [(left,-0.853),(right,-0.853),(right,-0.738),
               (right-right_notch,-0.738),(right-right_notch,-0.60),
               (left+left_notch,-0.60),(left+left_notch,-0.738),(left,-0.738)]
    outline = [p for i,p in enumerate(outline) if p != outline[i-1]]
    return polygon(name, outline, 0.735, 0.755, mat, root, 0.0004)


def build(root):
    dark = material(MATERIAL_NAMES[0], (0.055, 0.06, 0.068), roughness=0.16)
    ivory = material(MATERIAL_NAMES[1], (0.94, 0.93, 0.88), roughness=0.25)
    brass = material(MATERIAL_NAMES[2], (0.65, 0.48, 0.23), metal=0.72, roughness=0.26)
    outline = case_outline()
    inner = rim("CASE_CurvedRim", outline, dark, root)
    polygon("CASE_Underbody", outline, 0.756, 0.795, dark, root, 0.004)
    polygon("HARP_RecessedSoundboard", inner, 0.801, 0.82, dark, root, 0.001)
    box("CASE_Keybed", (0,-0.6525,0.704), (1.5,0.445,0.056), dark, root, 0.008)
    box("CASE_FrontRail", (0,-0.866,0.731), (1.34,0.018,0.028), dark, root, 0.003)
    for sign in (-1,1):
        box("CASE_EndCheek_%s" % sign, (sign*0.690,-0.655,0.786), (0.12,0.44,0.125), dark, root, 0.008)
    box("CASE_BlankFallboard", (0,-0.564,0.857), (1.263,0.035,0.216), dark, root, 0.006)
    box("CASE_FoldedFrontLid", (0,-0.48,0.981), (1.49,0.16,0.024), dark, root, 0.004)
    rod("CASE_FallboardHinge", (-0.61,-0.54,0.966), (0.61,-0.54,0.966), 0.003, brass, root)

    # A0-C8 inclusive: 52 notched naturals and 36 raised accidentals.
    naturals = [midi for midi in range(21,109) if midi % 12 in (0,2,4,5,7,9,11)]
    pitch = 0.0235
    for index,midi in enumerate(naturals):
        has_left = index > 0 and midi - naturals[index-1] == 2
        has_right = index < len(naturals)-1 and naturals[index+1]-midi == 2
        left = -0.611 + index*pitch + 0.0004
        obj = white_key("KEY_White_%02d_MIDI_%d" % (index+1,midi), left,left+pitch-0.0008,
                        0.0077 if has_left else 0,0.0077 if has_right else 0,ivory,root)
        obj["midi_note"],obj["key_color"] = midi,"white"
        if has_right:
            obj = box("KEY_Black_MIDI_%d" % (midi+1),(-0.611+(index+1)*pitch,-0.669,0.7525),
                      (0.014,0.138,0.037),dark,root,0.0008)
            obj["midi_note"],obj["key_color"] = midi+1,"black"

    # Open cast-harp members and simplified string courses, all original geometry.
    box("HARP_PinBlock",(0,-0.365,0.869),(1.34,0.065,0.055),brass,root,0.007)
    for i in range(28):
        x = -0.61+i*0.044
        end_y = 0.70 if x < -0.10 else max(-0.10,0.68-(x+0.1)*1.2)
        rod("HARP_StringCourse_%02d" % i,(x,-0.32,0.87),(x*0.78-0.06,end_y,0.87),0.0016,brass,root,8)
        rod("HARP_TuningPin_%02d" % i,(x,-0.365,0.891),(x,-0.365,0.903),0.004,brass,root,8)
    for i,(a,b) in enumerate((((-0.62,-0.28,0.889),(-0.48,0.68,0.889)),
                             ((-0.15,-0.28,0.889),(-0.27,0.73,0.889)),
                             ((0.38,-0.28,0.889),(0.06,0.55,0.889)))):
        rod("HARP_CastBrace_%d" % i,a,b,0.018,brass,root)
    bridge = bezier(((-0.57,0.48),(-0.26,0.61),(0.12,0.20),(0.43,-0.12)),18)
    for i,(a,b) in enumerate(zip(bridge,bridge[1:])):
        rod("HARP_Bridge_%02d" % i,(*a,0.845),(*b,0.845),0.01,brass,root)

    # The saved lid pivot follows the straight bass-side hinge, not the centre.
    lid = bpy.data.objects.new("LID_HingePivot",None)
    bpy.context.scene.collection.objects.link(lid)
    lid.parent = root
    lid.location = (-0.735,0,1.005)
    lid.rotation_euler.y = LID_ANGLE
    local_outline = [(max(x,-0.735)+0.735,y) for x,y in outline]
    polygon("LID_RaisedPanel",local_outline,0,0.026,dark,lid,0.004)
    for i,y in enumerate((-0.23,0.16,0.53)):
        rod("LID_BrassHinge_%d" % i,(-0.735,y-0.045,1.005),(-0.735,y+0.045,1.005),0.008,brass,root)
    bpy.context.view_layer.update()
    contact = lid.matrix_world @ Vector((1.35,-0.20,0))
    prop = rod("LID_PropStick",(0.66,-0.20,0.979),contact,0.012,dark,root)
    prop["contact_local"] = [1.35,-0.20,0]
    box("LID_PropSocket",(0.66,-0.20,0.981),(0.042,0.042,0.018),brass,root,0.003)

    # Low solid music desk, tilted backwards with an open geometric centre.
    desk = bpy.data.objects.new("MUSIC_DeskPivot",None)
    bpy.context.scene.collection.objects.link(desk)
    desk.parent = root
    desk.location = (0,-0.48,0.996)
    desk.rotation_euler.x = math.radians(-15)
    for x in (-0.35,0.35):
        box("MUSIC_FrameSide_%s" % x,(x,0,0.115),(0.032,0.021,0.23),dark,desk,0.004)
    box("MUSIC_FrameTop",(0,0,0.22),(0.72,0.021,0.032),dark,desk,0.004)
    box("MUSIC_FrameBottom",(0,0,0.022),(0.72,0.021,0.044),dark,desk,0.003)
    for x in (-0.18,0,0.18):
        bar = box("MUSIC_OpenStrut_%s" % x,(x,0,0.116),(0.016,0.016,0.18),dark,desk,0.002)
        bar.rotation_euler.y = math.radians(20 if x < 0 else -20)
    box("MUSIC_Tray",(0,-0.032,0.006),(0.74,0.09,0.012),dark,desk,0.003)
    box("MUSIC_RetainingLip",(0,-0.073,0.015),(0.74,0.01,0.03),dark,desk,0.002)

    # Three tapered legs terminate in small brass forks and black rolling casters.
    for i,(x,y,z) in enumerate(((-0.63,-0.69,0.69),(0.63,-0.69,0.69),(-0.30,0.66,0.78))):
        tapered_leg("LEG_Tapered_%d" % i,(x,y,z),(x,y,0.105),0.105,0.058,dark,root)
        box("LEG_Shoulder_%d" % i,(x,y,z-0.025),(0.145,0.145,0.075),dark,root,0.01)
        box("CASTER_Ferrule_%d" % i,(x,y,0.114),(0.067,0.067,0.048),brass,root,0.003)
        for sign in (-1,1):
            box("CASTER_Fork_%d_%s" % (i,sign),(x+sign*0.025,y,0.064),(0.009,0.033,0.06),brass,root,0.002)
        rod("CASTER_Wheel_%d" % i,(x-0.02,y,0.04),(x+0.02,y,0.04),0.04,dark,root,24)
        rod("CASTER_Axle_%d" % i,(x-0.033,y,0.04),(x+0.033,y,0.04),0.009,brass,root)

    # Lyre columns, crossbar, pedal pivots and three discrete foot paddles.
    for sign in (-1,1):
        rod("LYRE_Column_%s" % sign,(sign*0.115,-0.46,0.699),(sign*0.085,-0.55,0.225),0.021,dark,root)
        rod("LYRE_Brace_%s" % sign,(sign*0.08,-0.52,0.24),(sign*0.21,-0.27,0.756),0.008,brass,root)
    box("LYRE_Crossbar",(0,-0.55,0.223),(0.27,0.09,0.067),dark,root,0.014)
    for i,x in enumerate((-0.073,0,0.073)):
        rod("PEDAL_Link_%d" % i,(x,-0.544,0.232),(x,-0.60,0.145),0.007,brass,root)
        pedal = box("PEDAL_Paddle_%d" % i,(x,-0.66,0.139),(0.039,0.134,0.02),brass,root,0.009)
        pedal.rotation_euler.x = math.radians(-6)

    # Matching plain bench; no seams, labels, upholstery textures or lettering.
    box("BENCH_Apron",(0,-1.29,0.445),(0.61,0.31,0.08),dark,root,0.008)
    box("BENCH_Cushion",(0,-1.29,0.515),(0.66,0.36,0.07),dark,root,0.025)
    for x in (-0.26,0.26):
        for y in (-1.41,-1.17):
            tapered_leg("BENCH_Leg_%s_%s" % (x,y),(x,y,0.45),(x,y,0.009),0.047,0.035,dark,root)
            box("BENCH_Foot_%s_%s" % (x,y),(x,y,0.006),(0.037,0.037,0.012),dark,root,0.002)

    # Centre the complete piano-and-bench floor footprint while keeping the root at zero.
    for child in root.children:
        child.location.y += FOOTPRINT_SHIFT
    root["nominal_closed_case_height_m"] = 1.0
    root["lid_angle_degrees"] = 32
    root["scope"] = "Static original baby grand and matching bench; no playable keys or audio"



def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("Slate studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.12, 0.16, 0.2, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45
    for name, location, energy, size in (("Key", (-2, -3, 4), 430, 3), ("Fill", (3, -1, 2.5), 290, 3), ("Rim", (0, 3, 3), 500, 2)):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = "STUDIO_" + name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        aim(light, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = "STUDIO_Camera"
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = 3.12
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 40
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"


def evaluated_vertices(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    evaluated.to_mesh_clear()
    return vertices


def source_measurements(root):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    parts = []
    for obj in sorted(root.children_recursive, key=lambda obj: obj.name):
        if obj.type != "MESH":
            continue
        vertices = evaluated_vertices(obj, depsgraph)
        positions = [[round(v.x, 7), round(v.z, 7), round(-v.y, 7)] for v in vertices]
        part = {"name": obj.name, "material": obj.data.materials[0].name, "positions": positions}
        if "midi_note" in obj:
            part.update(midi=obj["midi_note"], color=obj["key_color"])
        parts.append(part)
    return {"blender_version": bpy.app.version_string, "parts": parts,
            "keys": [part for part in parts if "midi" in part], "editable_meshes": len(parts)}


def export(path):
    """Export merged evaluated copies; keep the saved authoring objects editable."""
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    originals = [obj for obj in root.children_recursive if obj.type == "MESH"]
    try:
        for material_name in MATERIAL_NAMES:
            group = []
            for original in originals:
                if original.data.materials[0].name != material_name:
                    continue
                mesh = bpy.data.meshes.new_from_object(original.evaluated_get(depsgraph), depsgraph=depsgraph)
                copy = bpy.data.objects.new("EXPORT_Part", mesh)
                bpy.context.scene.collection.objects.link(copy)
                copy.matrix_world = original.matrix_world.copy()
                group.append(copy)
            bpy.ops.object.select_all(action="DESELECT")
            for obj in group:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = group[0]
            bpy.ops.object.join()
            merged = bpy.context.object
            merged.name = "MESH_" + material_name.replace(" ", "_").replace("-", "_")
            merged.parent = root
        bpy.ops.object.select_all(action="DESELECT")
        root.select_set(True)
        for obj in root.children:
            if obj.name.startswith("MESH_"):
                obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                                  export_yup=True, export_animations=False, export_extras=True,
                                  export_texcoords=False, export_cameras=False, export_lights=False)
    finally:
        for obj in list(root.children):
            if obj.name.startswith("MESH_"):
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.meshes.remove(mesh)


def render_views():
    scene = bpy.context.scene
    for name, delta in (("hero", (2.3, -3.5, 2.0)), ("front", (0, -4, 0.26)),
                        ("side", (4, 0, 0.38)), ("3q", (-2.8, -3.6, 2.7))):
        scene.camera.location = TARGET + Vector(delta)
        aim(scene.camera, TARGET)
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(HERE / "previews" / (name + ".png"))
        bpy.ops.render.render(write_still=True)
        if name == "hero":
            scene.render.image_settings.file_format = "WEBP"
            scene.render.image_settings.quality = 86
            bpy.data.images["Render Result"].save_render(str(HERE / "previews" / "hero.webp"), scene=scene)


def main():
    for directory in ("sources", "exports", "previews", "metadata", "reports"):
        (HERE / directory).mkdir(exist_ok=True)
    if "--export-source" in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / "sources" / (SLUG + ".blend")))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        scene = bpy.context.scene
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 1
        root = bpy.data.objects.new(ROOT, None)
        scene.collection.objects.link(root)
        root["units"] = "metres"
        root["front_axis"] = "Blender -Y / glTF +Z"
        root["up_axis"] = "Blender +Z / glTF +Y"
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "sources" / (SLUG + ".blend")), compress=True)
    if "--previews-only" in sys.argv:
        render_views()
        return
    measured = source_measurements(bpy.data.objects[ROOT])
    (HERE / "reports" / "source-geometry.json").write_text(json.dumps(measured, indent=2) + "\n")
    export(HERE / "exports" / "optimized.glb")
    if "--skip-render" not in sys.argv:
        render_views()


if __name__ == "__main__":
    main()
