"""Run the fitter on a named delivery input. Reuse complete, hash-matched evidence."""
import hashlib
import json
import sys

from asset_io import HERE, MOTION, PARTS
from fit_module import fit
from modules import MODULES

name,*params = sys.argv[sys.argv.index('--')+1:]
rel,slot = MODULES[name]
destination = HERE/f'male-{name}.glb'
evidence = HERE/'qa'/f'male-{name}.json'
if destination.exists() and evidence.exists() and '--force' not in params:
    record = json.loads(evidence.read_text())
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if (len(record['reimport'])==15 and record['sha256']==sha(destination)
            and record['motion_sha256']==sha(MOTION)):
        print('Already audited',destination.name,flush=True)
        sys.exit(0)
digits = next((x for x in params if x.isdigit()),'6')
fit(PARTS/rel,destination,slot,int(digits))
