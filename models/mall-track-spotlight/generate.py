"""Build the original gallery spotlight in metres with Blender 5.1.2."""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = "ASSET_MallTrackSpotlight"
TAU = math.tau


def finish(obj, name, parent, mat=None):
    obj.name = name
    obj.parent = parent
    if mat:
        obj.data.name = name
        obj.data.materials.append(mat)
    return obj


def empty(name, parent=None, xyz=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = xyz
    obj.empty_display_size = .009
    return finish(obj, name, parent)


def swatch(name, hex_rgb, metal, roughness, emission=0):
    rgb = [int(hex_rgb[i:i+2], 16) / 255 for i in (0, 2, 4)]
    rgba = tuple(v / 12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb) + (1,)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = rgba
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = rgba
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = roughness
    if emission:
        p.inputs["Emission Color"].default_value = rgba
        p.inputs["Emission Strength"].default_value = emission
    return mat


def bevel(obj, width):
    mod = obj.modifiers.new("Machined edges", "BEVEL")
    mod.width = width
    mod.segments = 2 if width > .0009 else 1
    mod = obj.modifiers.new("Face-weighted normals", "WEIGHTED_NORMAL")
    mod.keep_sharp = True


def box(name, parent, mat, xyz, size, edge=.0007):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = finish(bpy.context.object, name, parent, mat)
    for v in obj.data.vertices:
        v.co = [a*b for a, b in zip(v.co, size)]
    obj.location = xyz
    bevel(obj, edge)
    return obj


def mesh(name, parent, mat, verts, faces):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, parent, mat)


def turned(name, parent, mat, profile, sides=40, smooth=True, flutes=None, stagger=0):
    """Revolve an ordered (radius, axial depth) perimeter, supporting true centre poles."""
    verts, rings, faces = [], [], []
    for row, (radius, z) in enumerate(profile):
        ring = []
        for j in range(sides if radius else 1):
            a = TAU * (j + (stagger if row % 2 else 0)) / sides
            r = radius + (flutes[row][j % len(flutes[row])] if flutes else 0)
            ring.append(len(verts))
            verts.append((r*math.cos(a), r*math.sin(a), z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for j in range(sides):
            k = (j+1) % sides
            if len(a) == 1 and len(b) > 1:
                faces.append((a[0], b[k], b[j]))
            elif len(b) == 1 and len(a) > 1:
                faces.append((a[j], a[k], b[0]))
            elif len(a) > 1 and len(b) > 1:
                faces.append((a[j], a[k], b[k], b[j]))
    obj = mesh(name, parent, mat, verts, faces)
    if smooth:
        obj.data.polygons.foreach_set("use_smooth", [True]*len(faces))
        obj.data.set_sharp_from_angle(angle=math.radians(38))
    return obj


def disc(name, parent, mat, radius, low, high, edge=.0006, sides=28):
    return turned(name, parent, mat, [(0,low), (radius-edge,low), (radius,low+edge),
        (radius,high-edge), (radius-edge,high), (0,high)], sides)


def rounded_yoke(parent, mat):
    # Single bent 9 mm bracket across the top. Both legs terminate on the tilt axle.
    path = [(-.0615, -.003), (-.0615, .080)]
    for i in range(1, 11):
        a = math.pi - math.pi*i/20
        path.append((-.0485+.013*math.cos(a), .080+.013*math.sin(a)))
    path.append((.0485, .093))
    for i in range(1, 11):
        a = math.pi/2 - math.pi*i/20
        path.append((.0485+.013*math.cos(a), .080+.013*math.sin(a)))
    path.append((.0615, -.003))
    vertices = []
    for i, (x, z) in enumerate(path):
        dx, dz = (Vector(path[min(i+1,len(path)-1)]) - Vector(path[max(i-1,0)])).normalized()
        # The four samples run around a section ordered counterclockwise along the path.
        for half, y in [(-.0035,-.010), (-.0035,.010), (.0035,.010), (.0035,-.010)]:
            vertices.append((x-dz*half, y, z+dx*half))
    faces = [(3,2,1,0)]
    for i in range(len(path)-1):
        for j in range(4):
            k = (j+1)%4
            faces.append((4*i+j,4*i+k,4*i+4+k,4*i+4+j))
    end = 4*(len(path)-1)
    faces.append((end,end+1,end+2,end+3))
    obj = mesh("Yoke_BentStrap", parent, mat, vertices, faces)
    bevel(obj, .0014)


def build():
    root = empty(ROOT)
    root["mount"] = "Rail top centre, Blender z=0; metres"
    root["front"] = "Toward Blender -Y and down"
    frame = swatch("Storm graphite powdercoat", "465054", .32, .34)
    black = swatch("Carbon black anodising", "242B2C", .42, .36)
    brass = swatch("Satin champagne brass", "CC9F61", .75, .30)
    mirror = swatch("Spun aluminium", "C4CCCA", .83, .22)
    lens = swatch("Warm opal emitter", "FFDA93", .02, .24, 1.0)

    rail = empty("Ceiling_Track", root)
    box("Track_Crown", rail, frame, (0,0,-.0025), (.353,.037,.005), .0008)
    for side, tag in [(-1,"Front"), (1,"Back")]:
        box("Track_Side_"+tag, rail, frame, (0,side*.0177,-.013), (.353,.0048,.022), .0008)
        box("Track_Return_"+tag, rail, frame, (0,side*.0137,-.0225), (.353,.010,.003), .0006)
        box("Insulator_"+tag, rail, black, (0,side*.012,-.009), (.347,.005,.009))
        box("Busbar_"+tag, rail, brass, (0,side*.010,-.010), (.347,.0024,.0032), .0004)
    for side, tag in [(-1,"Left"), (1,"Right")]:
        box("Rail_EndCap_"+tag, rail, black, (side*.1778,0,-.012), (.0044,.040,.024), .0012)
    adapter = empty("Adapter_Carriage", root)
    box("Adapter_ContactFoot", adapter, black, (0,0,-.018), (.085,.016,.019), .0015)
    box("Adapter_Casing", adapter, frame, (0,0,-.0365), (.104,.042,.026), .0055)
    box("Adapter_LatchPad", adapter, black, (-.021,-.021,-.036), (.027,.003,.014), .0013)
    box("Adapter_SlidingLatch", adapter, brass, (-.027,-.023,-.036), (.011,.003,.010), .0014)
    for i in range(3):
        obj = box(f"Adapter_Grip_{i+1}", adapter, black, (.026+i*.005,-.0212,-.036), (.002,.0014,.011), .0005)
        obj["omit_lod1"] = True

    swivel = empty("Swivel_Yoke", root, (0,0,-.165))
    disc("Swivel_Socket", swivel, black, .016, .104, .119, .0015)
    disc("Swivel_IndexRing", swivel, brass, .015, .101, .105)
    disc("Swivel_Coupling", swivel, frame, .013, .0925, .102, .001)
    rounded_yoke(swivel, black)
    head = empty("Tilt_Axle", swivel)
    head.rotation_euler.x = math.radians(126)
    head["axis"] = "Optical axis is local +Z; rotation around local X controls tilt."
    # A closed fluted casting, rotating with the head. Leave actual air channels between ribs.
    wave = [0, .0055, .0055, 0]
    zero = [0]*4
    turned("Head_FinnedCasting", head, frame,
        [(.039,-.080),(.047,-.077),(.049,-.071),(.049,.006),(.050,.013),(.050,.015),(.034,.015),(.034,-.080)],
        24*4, True, [zero,zero,wave,wave,wave,zero,zero,zero])
    # The annular shell is genuinely open at the front and surrounds the recessed optics.
    turned("Head_FrontHousing", head, frame,
        [(.0495,.013),(.053,.014),(.0547,.017),(.0547,.026),(.0542,.030),
         (.0527,.088),(.0532,.094),(.0532,.101),(.0525,.103),(.047,.103),
         (.0465,.098),(.045,.02),(.046,.013)], 48)
    turned("Head_BodySeam", head, black,
        [(.051,.0131),(.0534,.0131),(.0534,.0142),(.051,.0142)])
    turned("Head_FrontIndexBand", head, brass,
        [(.0525,.093),(.05325,.093),(.05345,.0933),(.05345,.0956),(.0532,.096),(.0525,.096)], 48)
    turned("Optic_BlackBezel", head, black,
        [(.047,.101),(.052,.101),(.0529,.103),(.0529,.106),(.0521,.1073),(.0478,.1073),
         (.0453,.105),(.044,.101),(.044,.098),(.046,.098)], 48)
    # Staggered facets model a peened reflector. The optic at its throat is a separate solid.
    turned("Optic_FacetedReflector", head, mirror,
        [(.046,.1012),(.0448,.1012),(.0416,.0987),(.036,.092),(.029,.0857),
         (.0214,.0805),(.016,.0787),(.014,.0774),(.014,.075),(.046,.096)], 32, False, stagger=.5)
    turned("Optic_RetainingRing", head, brass,
        [(.0138,.0770),(.0162,.0770),(.0162,.0780),(.0158,.0787),(.0136,.0787)], 32)
    turned("Optic_OpalLens", head, lens,
        [(0,.0764),(.014,.0764),(.014,.078),(.012,.079),(.007,.0801),(0,.0804)], 36)
    # Back cap with concentric raised service cover and three recessed hex fasteners.
    disc("Head_RearCover", head, black, .044, -.082, -.077, .0012)
    disc("Head_RearServicePlate", head, frame, .033, -.0835, -.081, .00055)
    for i in range(3):
        a = TAU*i/3
        fastener = disc(f"Rear_Fastener_{i+1}", head, black, .0034, -.08425, -.083, .00025, 12)
        fastener.location = (.026*math.cos(a), .026*math.sin(a), 0)
        fastener["omit_lod1"] = True
    for side, tag in [(-1,"Left"), (1,"Right")]:
        rotary = empty("Hinge_"+tag, swivel)
        rotary.rotation_euler.y = side*math.pi/2
        disc("Hinge_Spacer_"+tag, rotary, black, .014, .049, .0595)
        disc("Hinge_Hub_"+tag, rotary, black, .0175, .058, .0655, .0013)
        disc("Hinge_Bearing_"+tag, rotary, brass, .016, .0653, .067, .00045)
        disc("Hinge_LockDial_"+tag, rotary, frame, .0144, .0665, .0705, .0011, 32)
        # Recess walls and hexagonal floor are visible as real geometry from either side.
        socket = turned("Hinge_HexSocket_"+tag, rotary, black,
            [(0,.0702),(.0062,.0702),(.0062,.0716),(.0034,.0716),
             (.0032,.0708),(0,.0708)], 6, False)
        for j in range(8):
            angle = math.radians(-70+j*20)
            obj = box(f"Hinge_{tag}_Index_{j+1}", rotary, brass,
                (.0105*math.cos(angle), .0105*math.sin(angle), .07045),
                (.002 if j in (0,7) else .0013,.00055,.00040), .00013)
            obj.rotation_euler.z = angle
            obj["omit_lod1"] = True
    return root


def export_lod(root, path, low):
    """Batch evaluated copies into one mesh; preserve the native pivot hierarchy."""
    objects = [o for o in root.children_recursive if o.type == "MESH"]
    copies = []
    for source in objects:
        if low and source.get("omit_lod1"):
            continue
        temp = source.copy()
        temp.name = "Export_" + source.name
        bpy.context.collection.objects.link(temp)
        if low:
            for mod in temp.modifiers:
                if mod.type == "BEVEL":
                    mod.segments = 1
            if len(source.data.polygons) > 75:
                simplify = temp.modifiers.new("Reduced curved surfaces", "DECIMATE")
                # The thin front band needs more facets to retain distinct inner and outer walls.
                simplify.ratio = .33 if source.name == "Head_FrontIndexBand" else .24
        graph = bpy.context.evaluated_depsgraph_get()
        baked = bpy.data.meshes.new_from_object(temp.evaluated_get(graph), depsgraph=graph)
        baked.transform(root.matrix_world.inverted_safe() @ source.matrix_world)
        bpy.data.objects.remove(temp, do_unlink=True)
        part = bpy.data.objects.new("Baked_" + source.name, baked)
        bpy.context.collection.objects.link(part)
        copies.append(part)
    bpy.ops.object.select_all(action="DESELECT")
    for o in copies:
        o.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    batch = bpy.context.object
    batch.name = "Spotlight_L1" if low else "Spotlight_L0"
    batch.data.name = batch.name
    batch.parent = root
    root.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
        export_yup=True, export_animations=False, export_texcoords=False, export_extras=True,
        export_cameras=False, export_lights=False, export_attributes=False)
    bpy.data.objects.remove(batch, do_unlink=True)


def point(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z","Y").to_euler()


def render_export(path, previews):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    scene = bpy.context.scene
    target = Vector((0,-.015,-.120))
    view = Vector((.98,-1.50,-.46)).normalized()
    scene.world = bpy.data.worlds.new("Cool studio fill")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (.64,.71,.76,1)
    bg.inputs["Strength"].default_value = .45
    # A distant matte card gives the isolated luminaire a continuous studio background.
    bpy.ops.mesh.primitive_plane_add(size=3, location=target-view*.38)
    card = bpy.context.object
    card.rotation_euler = view.to_track_quat("Z","Y").to_euler()
    card.data.materials.append(swatch("Studio backdrop", "9EAEA9", 0, .93))
    for name, xyz, power, size, tint in [
        ("Large softbox", (-.30,-.42,.55), 10.0,.49,(1,.91,.77)),
        ("Face fill", (.30,-.48,-.23), 5.0,.29,(.83,.91,1)),
        ("Edge strip", (.17,.32,.17), 6.5,.28,(1,.96,.87)),
        ("Lower bounce", (-.30,-.10,-.48), 3.0,.27,(1,.86,.68)),
    ]:
        bpy.ops.object.light_add(type="AREA",location=xyz)
        lamp = bpy.context.object
        lamp.name = name
        lamp.data.energy = power
        lamp.data.size = size
        lamp.data.color = tint
        point(lamp,target)
    bpy.ops.object.camera_add(location=target+view*.90)
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = .397
    camera.data.clip_start = .005
    point(camera,target)
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "AgX"
    scene.render.resolution_x, scene.render.resolution_y = 960,800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(previews/"hero.png")
    bpy.ops.render.render(write_still=True)
    scene.render.resolution_percentage = 50
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = 90
    scene.render.filepath = str(previews/"thumbnail.webp")
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--export-source", action="store_true", help="Re-export the saved editable source.")
    parser.add_argument("--source", type=Path, default=HERE/"sources"/"mall-track-spotlight.blend")
    parser.add_argument("--output", type=Path, default=HERE/"exports", help="GLB output directory.")
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.source.resolve()
    if args.export_source:
        bpy.ops.wm.open_mainfile(filepath=str(source))
        root = bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
        root = build()
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == "VIEW_3D":
                    space = area.spaces.active
                    space.region_3d.view_rotation = Vector((.98,-1.50,-.46)).to_track_quat("Z","Y")
                    space.region_3d.view_location = (0, -.015, -.12)
                    space.region_3d.view_distance = .55
                    space.shading.color_type = "MATERIAL"
                    space.overlay.show_extras = False
                    space.overlay.show_floor = False
        bpy.ops.object.select_all(action="DESELECT")
        source.parent.mkdir(parents=True, exist_ok=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    bpy.context.view_layer.update()
    for name, low in [("optimized.glb",False), ("lod1.glb",True)]:
        export_lod(root,(args.output/name).resolve(),low)
    if not args.skip_render:
        previews = HERE/"previews"
        previews.mkdir(parents=True, exist_ok=True)
        render_export((args.output/"optimized.glb").resolve(), previews)


if __name__ == "__main__":
    main()
