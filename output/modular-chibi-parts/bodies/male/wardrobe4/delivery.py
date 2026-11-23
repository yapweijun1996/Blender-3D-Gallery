"""Bind each selected export to its gate, validator, and inspected renders."""
import argparse
import hashlib
import json
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parent
ITEMS = ('top-hoodie','bottom-skirt','top-jacket','bottom-shorts')


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(item, attempt, visual, observation, choose):
    name = f'{item}-r{attempt}'
    gate_path = ROOT/'qa'/f'{name}.gate.json'
    validation_path = ROOT/'qa'/f'{name}.validator.json'
    manifest_path = ROOT/'renders'/name/'manifest.json'
    gate, validation, manifest = map(read,(gate_path,validation_path,manifest_path))
    export = ROOT/f'{name}.glb'
    sha = digest(export)
    assert sha == gate['sha256'] == validation['sha256'] == manifest['sha256']
    for file, expected in manifest.get('views_sha256',{}).items():
        assert digest(ROOT/file) == expected, file
    clips = list(gate['clips'].values())
    inside = max(x['peak_inside'] for x in clips)
    pairs = max(x['peak_pairs'] for x in clips)
    clearance = 1000*min(x['min_signed_m'] for x in clips)
    layers = {key:max(x['layer_peaks'][key] for x in clips) for key in gate['layers_sha256']}
    fit = {'samples':gate['samples']==3027 and len(clips)==15,
           'inside':inside==0,'pairs':pairs==0,'signed_clearance':clearance>=.5,
           'triangle_budget':gate['triangles']==validation['triangles'] and gate['triangles']<=6000,
           'file_budget':gate['bytes']==validation['bytes']<=1.5*1024**2,
           'textures':not validation['textures'],
           'validator':validation['errors']==validation['warnings']==0,
           'rig':validation['sameHierarchy'] and validation['bindError']<=1e-5
                 and gate['max_influences']<=4,
           'layering':not any(layers.values())}
    if item=='top-hoodie':
        fit['hood_head_clearance'] = gate.get('cowl_min_head_distance_m',0)>=.0015
    if item=='bottom-shorts':
        fit['leg_clearance'] = 1000*gate.get('leg_min_signed_m',clearance/1000)>=1.5
    report = dict(item=item, round=attempt, sha256=sha, triangles=gate['triangles'], bytes=gate['bytes'],
                  peak_inside=inside, peak_pairs=pairs, min_mm=clearance, layers=layers,
                  checks=fit, visual_review=visual, observation=observation,
                  result='PASS' if all(fit.values()) and visual=='PASS' else 'FAIL')
    write(ROOT/'qa'/f'{name}.review.json',report)
    if choose:
        for source, target in ((export,ROOT/f'{item}.glb'),(gate_path,ROOT/'qa'/f'{item}.gate.json'),
                               (validation_path,ROOT/'qa'/f'{item}.validator.json')):
            copy2(source,target)
        write(ROOT/'qa'/f'{item}.review.json',report)
        notes()
    print(report)


def notes():
    rows = ['# Male wardrobe round 4','',
            'Each selected GLB is linked to its reimport gate and render manifest by SHA-256. '
            'The gate checks Blender deformation at rest and across 14 clips on 24 and 30 fps '
            'integer and half-frame timeline and clip-relative grids. Layering uses shipped male '
            'modules. The visual column is the author’s self-review of the exported GLB.','',
            '| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed (mm) | Rounds | Result | Render observation |',
            '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |']
    files = []
    for item in ITEMS:
        path = ROOT/'qa'/f'{item}.review.json'
        if not path.exists():
            continue
        result = read(path)
        n = f"{item}-r{result['round']}"
        rounds = len(list((ROOT/'qa').glob(f'{item}-r*.review.json')))
        rows.append(f"| {item} | {result['triangles']} | {result['bytes']/1024**2:.3f} | "
                    f"{result['peak_inside']} | {result['peak_pairs']} | {result['min_mm']:.3f} | "
                    f"{rounds} | {result['result']} | {result['observation']} |")
        missed = [name.replace('_',' ') for name, passed in result['checks'].items() if not passed]
        suffix = f" · Open gates: {', '.join(missed)}." if missed else ''
        files.append(f'- **{item}** · [GLB]({item}.glb) · [Gate](qa/{item}.gate.json) · '
                     f'[Khronos](qa/{item}.validator.json) · [Six views](renders/{n}/six-views.png) · '
                     f'[Motion views](renders/{n}/motion-views.png) · '
                     f'[Render manifest](renders/{n}/manifest.json){suffix}')
    rows.extend(['','## Files','',*files,''])
    (ROOT/'NOTES.md').write_text('\n'.join(rows))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('item',choices=ITEMS)
    parser.add_argument('attempt',type=int,choices=(1,2,3))
    parser.add_argument('visual',choices=('PASS','FAIL'))
    parser.add_argument('observation')
    parser.add_argument('--choose',action='store_true')
    args = parser.parse_args()
    record(args.item,args.attempt,args.visual,args.observation,args.choose)
