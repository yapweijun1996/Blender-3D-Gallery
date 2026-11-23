"""Run the original round-one checker drivers against the round-two motion."""
import runpy
import sys

from asset_io import HERE, MASTER
from motion_repair import FIXED, OUT
from verify import module_path


def check(key):
    script = HERE/'qa/checkers'
    original = list(sys.argv)
    for bank in ('shared','act','act2'):
        output = OUT/'qa/supplied'/key/bank
        output.mkdir(exist_ok=True,parents=True)
        for checker in ('motion_check_dense.py' if bank=='shared' else 'motion_check.py','motion_check_tri.py'):
            sys.argv = [checker,'--',str(MASTER),str(FIXED),str(module_path(key)),str(output)]
            if bank!='shared':
                sys.argv.append(str(FIXED))
            sys.path.insert(0,str(script/bank))
            sys.modules.pop('chibi',None)
            sys.modules.pop('motion_check',None)
            runpy.run_path(str(script/bank/checker),run_name='__main__')
            sys.path.pop(0)
    sys.argv = original


if __name__=='__main__':
    check(sys.argv[sys.argv.index('--')+1])
