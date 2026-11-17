"""Compare an isolated procedural rebuild with the delivered GLB and measurements."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


with tempfile.TemporaryDirectory(prefix='lounge-rebuild-') as directory:
    isolated = Path(directory)
    generator_hash = digest(HERE / 'generate.py')
    shutil.copy2(HERE / 'generate.py', isolated / 'generate.py')
    assert digest(isolated / 'generate.py') == generator_hash
    with (HERE / 'reports/rebuild.log').open('w') as log:
        process = subprocess.run([
            '/opt/homebrew/bin/blender', '--background', '--python-exit-code', '1',
            '--python', str(isolated / 'generate.py'), '--', '--skip-render'],
            stdout=log, stderr=subprocess.STDOUT)
    assert process.returncode == 0, 'Isolated rebuild failed; see reports/rebuild.log'
    canonical_hash = digest(HERE / 'exports/optimized.glb')
    rebuilt_hash = digest(isolated / 'exports/optimized.glb')
    canonical_measurements = json.loads((HERE / 'reports/sources.json').read_text())
    rebuilt_measurements = json.loads((isolated / 'reports/sources.json').read_text())
    assert canonical_hash == rebuilt_hash, 'GLB rebuild differs from delivery'
    assert canonical_measurements == rebuilt_measurements, 'Source measurements differ'
    assert digest(HERE / 'generate.py') == generator_hash, 'Generator changed during rebuild'
    report = {
        'result': 'PASS', 'blender_version': rebuilt_measurements['blender_version'],
        'generator_sha256': generator_hash,
        'canonical_glb_sha256': canonical_hash,
        'isolated_procedural_rebuild_sha256': rebuilt_hash,
        'identical_glb_bytes': True, 'identical_source_measurements': True,
        'rebuild_exit_code': process.returncode,
        'scope': 'Full procedural rebuild and source save in a temporary directory; canonical files untouched'}
    (HERE / 'reports/reproducibility.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
