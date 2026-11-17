"""Prove a source-only rebuild without repository helpers or external inputs."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
canonical = sha(HERE/'exports/optimized.glb')
with tempfile.TemporaryDirectory(prefix='elevator-interior-rebuild-') as temp:
    target = Path(temp)
    shutil.copy2(HERE/'generate.py', target/'generate.py')
    result = subprocess.run(['/opt/homebrew/bin/blender', '--background', '--python-exit-code', '1',
                             '--python', str(target/'generate.py'), '--', '--skip-render'],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (HERE/'reports/rebuild.log').write_text(result.stdout)
    assert result.returncode == 0
    rebuilt = sha(target/'exports/optimized.glb')
    assert canonical == rebuilt, (canonical, rebuilt)
reexport = sha(HERE/'reports/source-reexport.glb')
assert canonical == reexport, (canonical, reexport)
report = {'result':'PASS','generator_sha256':sha(HERE/'generate.py'),
          'canonical_glb_sha256':canonical,'independent_rebuild_sha256':rebuilt,
          'saved_source_reexport_sha256':reexport,
          'inputs':'Only generate.py copied to an empty temporary folder; no random inputs or external assets'}
(HERE/'reports/reproducibility.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
