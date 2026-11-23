"""Combine file, rig, motion and layering evidence without changing any gate."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ITEMS = ('top-hoodie','top-jacket','bottom-shorts','bottom-skirt','shoes-boots')
QA = HERE/'qa'
CLIPS = {'rest','idle','walk','run','wave','jump','nod','dance','sit_down','sit_idle',
         'stand_up','hold_item','hold_box','hold_bag','take_item'}


def read(path):
    return json.loads(path.read_text())


def write(path,payload):
    staging = path.with_suffix(path.suffix+'.tmp')
    staging.write_text(json.dumps(payload,indent=2)+'\n')
    staging.replace(path)


def evaluate(item, number):
    name = f'{item}-r{number}'
    candidate = HERE/f'{name}.glb'
    gate_path = QA/f'{name}.gate.json'
    validator_path = QA/f'{name}.validator.json'
    if not validator_path.exists():
        subprocess.run(['node', 'validate.mjs', candidate, validator_path], cwd=HERE,check=True)
    gate = read(gate_path)
    v = read(validator_path)
    rows = gate['clips']
    peak_inside = max(row['peak_inside'] for row in rows.values())
    peak_pairs = max(row['peak_pairs'] for row in rows.values())
    minimum = min(row['min_signed_m'] for row in rows.values())
    layers = {key:max(row['layer_peaks'][key] for row in rows.values()) for key in gate['layers_sha256']}
    expected_samples = 2915 if item=='top-hoodie' and number==1 and not gate.get('frame_grid') else 3027
    checks = {
        'all_poses': set(rows)==CLIPS and all(row['samples']==len(row['frames']) and row['samples']>0
                                            for row in rows.values()) and gate['samples']==expected_samples,
        'inside': peak_inside==0,
        'pairs': peak_pairs==0,
        'signed_clearance': minimum>=.0005,
        'layering': bool(layers) and not any(layers.values()),
        'triangle_budget': v['triangles']==gate['triangles'] and v['triangles']<=(3500 if item=='shoes-boots' else 6000),
        'file_budget': v['bytes']==gate['bytes'] and v['bytes']<=int(1.5*1024**2),
        'textures': all(max(size)<=1024 for size in v['textures']),
        'khronos': v['errors']==0 and v['warnings']==0,
        'rig': v['joints']==65 and v['sameHierarchy'] and v['bindError']<1.e-5 and gate['max_influences']<=4,
        'export_identity': v['sha256']==gate['sha256']==hashlib.sha256(candidate.read_bytes()).hexdigest(),
    }
    return dict(name=name,number=number,triangles=v['triangles'],mib=v['bytes']/1024**2,
                inside=peak_inside,pairs=peak_pairs,minimum_mm=1000*minimum,layers=layers,
                errors=v['errors'], warnings=v['warnings'], checks=checks, passed=all(checks.values()))


def select(item,number):
    rows = [evaluate(item,n) for n in range(1,number+1)]
    picked = next((row for row in rows if row['passed']),None)
    if not picked and number<3:
        print('CONTINUE',item,rows[-1],flush=True)
        return False
    if picked:
        file = f'{item}.glb'
        staging = HERE/f'.{item}.glb.tmp'
        shutil.copyfile(HERE/f"{picked['name']}.glb",staging)
        staging.replace(HERE/file)
    else:
        picked = min(rows,key=lambda row:(not row['checks']['khronos'],row['inside']+row['pairs'],
                                         sum(row['layers'].values()),-row['minimum_mm']))
        file = f"{picked['name']}.glb"
    gate = read(QA/f"{picked['name']}.gate.json")
    gate.update(summary=picked, selected_file=file, completed_rounds=number)
    write(QA/f'{item}.gate.json', gate)
    write(QA/f'{item}.result.json',dict(file=file,picked=picked,rounds=rows))
    print('SELECT',item,file,picked,flush=True)
    notes()
    return True


def notes():
    lines = ['# Male wardrobe · Body-derived shells','',
             'The source is `../body_male.glb` with the 65-joint bind from `../master_male.blend`. '
             'The geometry comes from clipped body triangles or sampled body cross-sections. '
             'Cut edges interpolate body weights, and a light smoothing pass keeps at most four influences. '
             'The skirt transfers weights at the waist and blends to the pelvis for the shared flare. '
             'The materials are flat PBR and contain no textures. '
             'Each bake samples the 14 clips in `../round2/motion_male_fixed.glb` and rest, '
             'including integer frames, half frames, and endpoints on the 24 and 30 fps grids. '
             'The skirt also clamps its flare against the all-pose thigh sweep in pelvis space. '
             'The bake preserves the largest required per-vertex correction through smoothing, with a '
             '1.8 mm clearance margin. The gate reimports the exported GLB into Blender and evaluates '
             'the full body triangle BVH. It uses nearest-surface triangle normals for signed clearance.',
             '', 'The layering check uses the shipped GLBs from the demo manifest. Tops replace the '
             'T-shirt and pair with jeans and sneakers. Bottoms replace jeans and pair with the T-shirt '
             'and sneakers. Boots replace sneakers and pair with the T-shirt and jeans. '
             'Every sampled pose has separate overlap counts for each companion piece. The first hoodie trial used '
             'the timeline grids (2,915 samples). Later trials add the clip-relative grids (3,027 samples).', '',
             '| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed (mm) | Rounds | Result |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    files,history,rejections = [],[],[]
    for item in ITEMS:
        path = QA/f'{item}.result.json'
        if not path.exists():
            continue
        result = read(path)
        r = result['picked']
        n = len(result['rounds'])
        lines.append(f"| {item} | {r['triangles']} | {r['mib']:.3f} | {r['inside']} | {r['pairs']} | "
                     f"{r['minimum_mm']:.4f} | {n} | {'PASS' if r['passed'] else 'FAIL'} |")
        view = f'renders/{item}/six-views.png'
        views = f' · [Six views]({view})' if (HERE/view).exists() else ''
        files.append(f"- **{item}** · [{'GLB' if r['passed'] else 'Review candidate'}]({result['file']}) "
                     f"· [Full gate](qa/{item}.gate.json) · [Khronos](qa/{r['name']}.validator.json){views}")
        rounds = []
        for attempt in result['rounds']:
            failed = [name for name,ok in attempt['checks'].items() if not ok]
            layer = ', '.join(f'{name} {count}' for name,count in attempt['layers'].items())
            rounds.append(f"[R{attempt['number']}](qa/{attempt['name']}.gate.json) "
                          f"({attempt['inside']} inside, {attempt['pairs']} body pairs, "
                          f"{attempt['minimum_mm']:.4f} mm, layer peaks {layer}, "
                          f"Khronos {attempt['errors']}/{attempt['warnings']}"
                          f"{', missed ' + ', '.join(failed) if failed else ''})")
        history.append(f"- **{item}** · " + ' · '.join(rounds))
        if not r['passed']:
            clips = read(QA/f'{item}.gate.json')['clips']
            clearance_clip = min(clips,key=lambda clip: clips[clip]['min_signed_m'])
            contact_clip = max(clips,key=lambda clip: clips[clip]['peak_pairs'])
            c = clips[clearance_clip]
            layer_clip = max(clips,key=lambda clip: max(clips[clip]['layer_peaks'].values()))
            points = [f"{r['minimum_mm']:.4f} mm in `{clearance_clip}` at frame {c['worst_frame']:.4g}",
                      f"{r['pairs']} body overlap pairs in `{contact_clip}`"]
            if any(r['layers'].values()):
                layer_peak = max(r['layers'].values())
                points.append(f"{layer_peak} outfit overlap pairs in `{layer_clip}`")
            rejections.append(f"- **{item}** · " + ' · '.join(points) + '.')
    lines.extend(['','## Files','',*files,'','## Round evidence','',*history])
    if rejections:
        lines.extend(['','## Failed clearance witnesses','',*rejections])
    if (HERE/'renders/bottom-skirt/six-views.png').exists():
        lines.extend(['','The selected skirt also shows visible buckling at the side panels and hem in the six-view render.'])
    if (HERE/'renders/shoes-boots/six-views.png').exists():
        lines.extend(['','The boots retain visible toe contours and a serrated color boundary at the cuff.'])
    lines.extend(['',
                  'Rebuild a candidate with `./run.sh build_wardrobe.py -- ITEM ROUND`. '
                  'Run `python3 results.py ITEM ROUND` for validation, then '
                  '`./run.sh render_item.py -- FILE ITEM` for the selected GLB. '
                  'Use `python3 results.py notes` to regenerate this table.',''])
    staging = HERE/'NOTES.md.tmp'
    staging.write_text('\n'.join(lines))
    staging.replace(HERE/'NOTES.md')


if __name__=='__main__':
    if sys.argv[1:] == ['notes']:
        notes()
    else:
        item, no = sys.argv[1:]
        sys.exit(0 if select(item,int(no)) else 2)
