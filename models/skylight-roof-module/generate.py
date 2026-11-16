"""Original deterministic skylight, Blender 5.2.3. No external assets.

Native source: metres, +Z up, -Y front. Export: +Y up, +Z front.
The source preserves separate frame components; export joins by material.
"""
from pathlib import Path
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'skylight-roof-module'
ROOT = 'ASSET_SkylightRoofModule'
TARGET = Vector((0, 0, .10))
GRID = (-2, -1, 0, 1, 2)


def material(name, rgb, metallic=0, roughness=.4, alpha=1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb)
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Alpha'].default_value = alpha
    m.diffuse_color = (*color, alpha)
    if alpha < 1:
        # Alpha glazing avoids a screen-space transmission pass in the mall.
        m.surface_render_method = 'BLENDED'
        m.use_backface_culling = False
    return m


def empty(name, parent=None, location=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = location
    return o


def finish(o, name, mat, root, bevel=0):
    o.name = name
    o.data.materials.append(mat)
    bpy.context.view_layer.objects.active = o
    if bevel:
        mod = o.modifiers.new('Small manufactured edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    # Clip the finished lattice at exact repeat planes. Adjacent half members
    # form one full member; no bevel groove or doubled cap at the tile seam.
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for axis, sign in (((0, 1), (0, -1), (1, 1), (1, -1)) if root else ()):
        plane = [0., 0., 0.]
        normal = [0., 0., 0.]
        plane[axis] = sign * 2
        normal[axis] = sign
        result = bmesh.ops.bisect_plane(
            bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
            dist=1e-7, plane_co=plane, plane_no=normal,
            clear_outer=True, clear_inner=False)
        edges = [e for e in result['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    o.parent = root
    return o


def box(name, location, dimensions, mat, root, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    o = bpy.context.object
    o.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, mat, root, bevel)


def lattice(prefix, width, bottom, top, mat, root, bevel):
    for y in GRID:
        box(f'{prefix}_Cross_{y:+d}', (0, y, (bottom + top) / 2),
            (4 + width, width, top - bottom), mat, root, bevel)
    for x in GRID:
        for y in (-1.5, -.5, .5, 1.5):
            box(f'{prefix}_Long_{x:+d}_{y:+.1f}', (x, y, (bottom + top) / 2),
                (width, 1 - width, top - bottom), mat, root, bevel)


def build(root):
    steel = material('Satin steel', (.53, .61, .65), .65, .29)
    seal = material('Graphite glazing seals', (.10, .14, .16), 0, .74)
    glass = material('Pale aqua glass', (.64, .84, .87), .08, .14, .30)
    lattice('FRAME', .070, 0, .180, steel, root, .002)
    lattice('SEAL', .120, .180, .200, seal, root, .001)
    lattice('CAP', .090, .204, .220, steel, root, .002)
    for x in (-1.5, -.5, .5, 1.5):
        for y in (-1.5, -.5, .5, 1.5):
            box(f'GLASS_Pane_{x:+.1f}_{y:+.1f}', (x, y, .196),
                (.900, .900, .012), glass, root)
    for x in (-1.5, -.5, .5, 1.5):
        for y in GRID:
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=.009,
                depth=.004, location=(x, y, .222))
            finish(bpy.context.object, f'FIXING_{x:+.1f}_{y:+d}', steel, root, .0006)
    for name, position in (
        ('X_NEG', (-2, 0, 0)), ('X_POS', (2, 0, 0)),
        ('Z_POS', (0, -2, 0)), ('Z_NEG', (0, 2, 0))):
        c = empty('CONNECTOR_' + name, root, position)
        c['repeat_pitch_metres'] = 4.0
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['origin'] = 'floor centre; roof frame underside at local height zero'
    root['repeat_pitch_metres'] = 4.0
    root['placement'] = 'Translate root by 4 m in glTF X/Z; set Y to roof underside height'


def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Cool neutral studio')
    s.world.use_nodes = True
    bg = s.world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (.27, .33, .39, 1)
    bg.inputs['Strength'].default_value = .65
    floor = material('STUDIO warm stone', (.77, .78, .77), 0, .86)
    box('STUDIO_Floor', (0, 0, -.33), (200, 200, .06), floor, None)
    for name, position, power, size in (
        ('Key', (-3, -4, 7), 1900, 5),
        ('Fill', (4, -1, 5), 1100, 4),
        ('Rim', (1, 5, 6), 2200, 3)):
        bpy.ops.object.light_add(type='AREA', location=position)
        o = bpy.context.object
        o.name = 'STUDIO_' + name
        o.data.energy = power
        o.data.shape = 'DISK'
        o.data.size = size
        aim(o, TARGET)
    bpy.ops.object.camera_add(location=(6, -8, 7))
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 6.45
    aim(s.camera, TARGET)
    s.render.engine = 'CYCLES'
    s.cycles.samples = 24
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 768
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'


def render_views():
    s = bpy.context.scene
    requested = next((arg.split('=', 1)[1].split(',') for arg in sys.argv if arg.startswith('--views=')), None)
    for name, position in (
        ('hero', (6, -8, 8)), ('front', (0, -12, 3.3)),
        ('side', (12, 0, 3.3)), ('3q', (-6, -8, 5))):
        if requested and name not in requested:
            continue
        s.camera.location = position
        s.camera.data.ortho_scale = 6.45 if name in ('hero', '3q') else 4.65
        aim(s.camera, TARGET)
        s.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def export(path):
    root = bpy.data.objects[ROOT]
    copies = []
    # Separate editable source parts become exactly three runtime meshes.
    for material_name, mesh_name in (
        ('Satin steel', 'FRAME_Steel'), ('Graphite glazing seals', 'SEAL_Graphite'),
        ('Pale aqua glass', 'GLASS_Panes')):
        bpy.ops.object.select_all(action='DESELECT')
        group = []
        for o in root.children_recursive:
            if o.type == 'MESH' and o.data.materials[0].name == material_name:
                copy = o.copy()
                copy.data = o.data.copy()
                bpy.context.scene.collection.objects.link(copy)
                group.append(copy)
                copy.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        bpy.ops.object.join()
        o = bpy.context.object
        o.name = 'EXPORT_' + mesh_name
        o.data.name = mesh_name
        o.parent = root
        copies.append(o)
    try:
        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        for o in copies:
            o.select_set(True)
        for o in root.children:
            if o.type == 'EMPTY':
                o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB',
            use_selection=True, export_apply=True, export_yup=True,
            export_animations=False, export_texcoords=False, export_extras=True,
            export_cameras=False, export_lights=False)
    finally:
        for o in copies:
            mesh = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(mesh)


def main():
    for d in ('sources', 'exports', 'previews', 'reports', 'metadata'):
        (HERE / d).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system = 'METRIC'
        s.unit_settings.scale_length = 1
        root = empty(ROOT)
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    if '--render-only' not in sys.argv:
        export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
