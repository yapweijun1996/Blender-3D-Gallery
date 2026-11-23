"""Render the emitted assets and matched before/after action comparisons in Cycles."""
import sys

from asset_io import *
from body_audit import load_body_motion, set_frame, use_action
from fit_module import read_module
from fitting_geometry import arrays, tree
from body_audit import posed
from motion_repair import OUT, FIXED
from render_modules import VIEWS, baked, contact_sheet, crop_views, hash_file, studio
import render_modules
from verify import append_actions, module_path

RENDERS = OUT/'renders'
render_modules.HERE = OUT
FRAMES = {
    'walk': (18,42),
    'wave': (19,33),
    'run': (1,9.5),
    'sit_idle': (17.6,56.8),
    'hold_box': (12,36),
    'take_item': (4.8,12),
}


def module_views(scene,arm,body,actions,requested):
    modules = {key:read_module(module_path(key),arm) for key in requested}
    use_action(arm,actions['idle'])
    set_frame(scene,24)
    dg = bpy.context.evaluated_depsgraph_get()
    poses = {key:baked(obj,dg) for key,obj in [('body',body),*modules.items()]}
    for obj in [body,*modules.values()]:
        obj.hide_render = True
    ink = studio(scene)
    manifest = {'renderer':'Cycles CPU','clip':'idle','blender_frame':24,
                'motion_sha256':hash_file(FIXED),'modules':{}}
    record=RENDERS/'manifest.json'
    if record.exists():
        old=json.loads(record.read_text())
        if old.get('motion_sha256')==manifest['motion_sha256'] and old.get('blender_frame')==24:
            manifest['modules'].update(old['modules'])
    for key in requested:
        saved=manifest['modules'].get(key,{})
        if saved.get('sha256')==hash_file(module_path(key)) and all((OUT/p).is_file() for p in [saved['sheet'],*saved['views']]):
            continue
        folder = RENDERS/key
        folder.mkdir(exist_ok=True)
        sheet = folder/'six-views.png'
        contact_sheet(scene,ink,[(name.replace('-',' ').title(),angle,[poses['body'],poses[key]])
                                 for name,angle in VIEWS],sheet)
        files = crop_views(sheet,[name for name,_ in VIEWS],folder)
        manifest['modules'][key] = {'sha256':hash_file(module_path(key)),'views':files,
                                    'sheet':str(sheet.relative_to(OUT))}
        write_json(RENDERS/'manifest.json',manifest)
    outfits = [
        ('Spiky / T-shirt + jeans',('hair-spiky','tshirt','jeans','sneakers')),
        ('Bob / T-shirt + jeans',('hair-bob','tshirt','jeans','sneakers')),
        ('Side part / dress',('hair-sidepart','dress','sneakers')),
    ]
    if all(k in poses for _,parts in outfits for k in parts):
        def outfit_pairs():
            bvh = {}
            for key in ('tshirt','jeans','dress','sneakers'):
                obj = modules[key]
                bvh[key] = tree(posed(obj),arrays(obj)[1].tolist())
            return {a+'/'+b:len(bvh[a].overlap(bvh[b]))
                    for a,b in (('tshirt','jeans'),('jeans','sneakers'),('dress','sneakers'))}
        manifest['outfit_pairs'] = {'idle_f24':outfit_pairs()}
        use_action(arm,None)
        set_frame(scene,0)
        manifest['outfit_pairs']['rest'] = outfit_pairs()
        sheet = RENDERS/'outfits.png'
        contact_sheet(scene,ink,[(title,angle,[poses['body'],*(poses[k] for k in parts)])
                                 for angle in (20,155) for title,parts in outfits],sheet)
        manifest['outfits'] = str(sheet.relative_to(OUT))
        write_json(RENDERS/'manifest.json',manifest)


def pose_views(scene,arm,body,after):
    before = append_actions(MOTION)
    with bpy.data.libraries.load(str(NEUTRAL),link=False) as (src,dst):
        dst.objects = ['Armature','Base_Body']
    neutral_arm,neutral_body = dst.objects
    scene.collection.objects.link(neutral_arm)
    scene.collection.objects.link(neutral_body)
    neutral_arm.animation_data_create().use_nla = False
    neutral = {}
    for bank in BANKS:
        neutral.update(append_actions(bank))
    folder = RENDERS/'motion'
    folder.mkdir(exist_ok=True)
    ink = studio(scene)
    body.hide_render = neutral_body.hide_render = True
    manifest = {'renderer':'Cycles CPU','bank_before':hash_file(MOTION),'bank_after':hash_file(FIXED),
                'neutral_banks':{p.name:hash_file(p) for p in BANKS},'clips':{}}
    for clip,frames in FRAMES.items():
        tiles = []
        for frame in frames:
            for title,rig,obj,action in (('Neutral reference',neutral_arm,neutral_body,neutral[clip]),
                                         ('Male before',arm,body,before[clip]),
                                         ('Male fixed',arm,body,after[clip])):
                use_action(rig,action)
                nf,nl = action.frame_range
                af,al = after[clip].frame_range
                f = nf+(nl-nf)*(frame-af)/(al-af)
                set_frame(scene,f)
                rendered,matrix = baked(obj,bpy.context.evaluated_depsgraph_get())
                hip = rig.pose.bones['mixamorig:Hips'].head
                matrix.translation.x -= hip.x
                matrix.translation.y -= hip.y
                angle = {'walk':45,'wave':15,'run':58,'sit_idle':53,'hold_box':22,'take_item':37}[clip]
                tiles.append((f'{title} / f{frame:g}',angle,[(rendered,matrix)]))
        path = folder/f'{clip}-before-after.png'
        contact_sheet(scene,ink,tiles,path)
        manifest['clips'][clip] = dict(frames=frames,file=str(path.relative_to(OUT)))
        write_json(folder/'manifest.json',manifest)
        for _,_,items in tiles:
            for mesh,_ in items:
                bpy.data.meshes.remove(mesh)


if __name__=='__main__':
    scene,arm,body,actions = load_body_motion(FIXED)
    args = sys.argv[sys.argv.index('--')+1:]
    if args[0]=='poses':
        pose_views(scene,arm,body,actions)
    else:
        module_views(scene,arm,body,actions,args[1:] or
                     ['tshirt','dress','jeans','sneakers','hair-bob','hair-sidepart','hair-spiky'])
