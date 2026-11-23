"""Run the supplied dense and triangle checkers on one exported module.

Local copies keep each measurement kernel and argument contract. Sampling
includes endpoints and half frames; Cycles renders are produced separately.
"""
import runpy
import sys
from asset_io import HERE, MASTER, MOTION

original = list(sys.argv)
args = original[original.index('--')+1:]
module = (HERE/args[0]).resolve()
assert module.parent==HERE and module.suffix=='.glb'
directory = HERE/'qa/checkers'
for bank in args[1:] or ('shared','act','act2'):
    out = HERE/'qa/gates'/module.stem/bank
    out.mkdir(parents=True,exist_ok=True)
    for checker in ('motion_check_dense.py' if bank=='shared' else 'motion_check.py','motion_check_tri.py'):
        cli = [str(MASTER),str(MOTION),str(module),str(out)]
        if bank!='shared':
            cli.append(str(MOTION))
        sys.argv = [checker,'--',*cli]
        sys.path.insert(0,str(directory/bank))
        sys.modules.pop('chibi', None)
        sys.modules.pop('motion_check', None)
        runpy.run_path(str(directory/bank/checker),run_name='__main__')
        sys.path.pop(0)
sys.argv = original
