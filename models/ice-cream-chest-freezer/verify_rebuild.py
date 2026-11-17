"""Compare a fresh procedural build and saved-source export with the delivery."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import bpy

here = Path(__file__).resolve().parent
source = here / 'sources/ice-cream-chest-freezer.blend'
delivery = here / 'exports/optimized.glb'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_hash, expected = sha(source), sha(delivery)
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('freezer_generator', here / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
out = Path(tempfile.mkdtemp(prefix='ice-cream-rebuild-'))
generator.HERE = out
sys.argv.append('--skip-render')
generator.main()
rebuilt = sha(out / 'exports/optimized.glb')
assert rebuilt == expected, 'Fresh procedural build must reproduce delivery bytes'
bpy.ops.wm.open_mainfile(filepath=str(source))
generator.export(out / 'source-replay.glb')
replayed = sha(out / 'source-replay.glb')
assert replayed == expected, 'Saved-source export must reproduce delivery bytes'
assert sha(source) == source_hash and sha(delivery) == expected
report = {
    'result': 'PASS',
    'scope': 'Fresh independent generation and saved-source export reproduce delivery bytes on the same Blender version; no cross-version byte guarantee.',
    'sha256': expected,
    'fresh_generation_sha256': rebuilt,
    'source_export_sha256': replayed,
    'canonical_files_unchanged': True,
    'blender_version': bpy.app.version_string,
    'random_inputs': 'None; analytic geometry, fixed palette and fixed flavor phases',
    'evidence': 'rebuild.log',
}
(here / 'reports/export-replay.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
