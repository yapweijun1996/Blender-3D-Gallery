"""Build in isolation with only generate.py and compare actual GLB bytes."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

p = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='seasonal-cny-rebuild-') as temporary:
    target = Path(temporary)
    (target/'generate.py').write_bytes((p/'generate.py').read_bytes())
    with (p/'reports/rebuild.log').open('w') as log:
        result = subprocess.run(['/opt/homebrew/bin/blender','--background',
            '--python-exit-code','1','--python',str(target/'generate.py'),
            '--','--skip-render'],stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode == 0
    original = (p/'exports/optimized.glb').read_bytes()
    rebuilt = (target/'exports/optimized.glb').read_bytes()
    report = {'result':'PASS' if original == rebuilt else 'FAIL',
        'isolated_generator_only':True,'blender_version':'5.2.3 LTS',
        'original_glb_sha256':hashlib.sha256(original).hexdigest(),
        'rebuilt_glb_sha256':hashlib.sha256(rebuilt).hexdigest(),
        'byte_identical':original == rebuilt,
        'normalization':'Cyclic rotation and sorting of triangle index triples preserves geometry and winding.'}
    (p/'reports/reproducibility.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    assert original == rebuilt
