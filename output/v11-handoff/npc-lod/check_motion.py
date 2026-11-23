"""Execute the supplied motion checkers with only the Workbench previews removed."""
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType

import bpy

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARTS = ROOT / 'output/modular-chibi-parts'
MASTER = PARTS / 'master/GJH_Chibi_Master_rigged.blend'
MOTION = PARTS / 'body-fix/motion_fixed.glb'
ACTIONS = PARTS / 'actions-fix/actions_fixed.glb'
ACT_CHECK = PARTS / 'body-fix/act'
LEGACY_CHECK = Path(os.environ['NPC_LEGACY_CHECKERS'])
LEGACY = ('rest', 'walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance')
ALL = LEGACY + ('sit_down', 'sit_idle', 'stand_up', 'hold_item')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def before_marker(path, marker):
    source = path.read_text()
    if source.count(marker) != 1:
        raise ValueError(f'Preview boundary changed in {path}')
    return source.split(marker)[0]


def main():
    family, metric, garment_arg, dest_arg = sys.argv[sys.argv.index('--') + 1:]
    garment, dest = Path(garment_arg).resolve(), Path(dest_arg).resolve()
    if not dest.is_relative_to(HERE):
        raise ValueError(dest)
    dest.mkdir(parents=True, exist_ok=True)
    triangles = metric == 'triangles'
    if family == 'legacy':
        checker = LEGACY_CHECK / ('motion_check_tri.py' if triangles else 'motion_check_dense.py')
        sys.argv = [str(checker), '--', *map(str, (MASTER, MOTION, garment, dest))]
        source = before_marker(checker, "sc.render.engine='BLENDER_WORKBENCH'")
        scope = {'__name__': '__main__', '__file__': str(checker)}
        exec(compile(source, str(checker), 'exec'), scope)
        results, frames = scope['res'], None
        assert tuple(results) == LEGACY
        scripts = [checker]
    else:
        entry = ACT_CHECK / ('motion_check_tri.py' if triangles else 'motion_check.py')
        core = ACT_CHECK / 'motion_check.py'
        sys.argv = [str(entry), '--', *map(str, (MASTER, MOTION, garment, dest, ACTIONS))]
        module = ModuleType('motion_check' if triangles else '__main__')
        module.__file__ = str(core)
        source = before_marker(core, '    # Retain the original checker previews')
        source += "\nif __name__=='__main__':\n    garment_check()\n"
        exec(compile(source, str(core), 'exec'), module.__dict__)
        if triangles:
            sys.modules['motion_check'] = module
            exec(compile(entry.read_text(), str(entry), 'exec'),
                 {'__name__': '__main__', '__file__': str(entry)})
        stem = 'motion_check_tri' if triangles else 'motion_check'
        results = json.loads((dest / (stem + '.json')).read_text())
        frames = json.loads((dest / (stem + '_frames.json')).read_text())
        assert tuple(results) == ALL and tuple(frames) == ALL[1:]
        scripts = [entry, core, ACT_CHECK / 'chibi.py'] if triangles else [entry, ACT_CHECK / 'chibi.py']
    report = dict(blender=bpy.app.version_string, family=family, metric=metric,
                  glb_sha256=sha(garment), master_sha256=sha(MASTER),
                  motion_sha256=sha(MOTION),
                  actions_sha256=sha(ACTIONS) if family == 'actions' else None,
                  scripts={str(path): sha(path) for path in scripts}, results=results)
    if frames is not None:
        report['frames'] = frames
    (dest / f'{family}-{metric}.json').write_text(json.dumps(report, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
