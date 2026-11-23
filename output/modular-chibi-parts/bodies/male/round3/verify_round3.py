"""Run unchanged round-two per-frame predicates on the emitted round-three GLBs."""
import sys
from pathlib import Path

import verify
from asset_io import HERE
from motion_repair import FIXED

OUT = Path(__file__).resolve().parent


def module_path(key):
    if key in ('dress', 'jeans'):
        return OUT / f'male-{key}-v3.glb'
    if key == 'tshirt':
        return FIXED.parent / 'male-tshirt-v2.glb'
    return HERE / f'male-{key}.glb'


if __name__ == '__main__':
    verify.QA = OUT / 'qa'
    verify.module_path = module_path
    args = sys.argv[sys.argv.index('--') + 1:]
    if '--clips' in args:
        i = args.index('--clips')
        verify.module_audit(args[:i] or ['dress', 'jeans'], args[i + 1:])
    else:
        verify.module_audit(args or ['dress', 'jeans'])
