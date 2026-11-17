"""Independently rebuild in a temporary folder and compare delivered GLB bytes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('bottle_generator', HERE / 'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
with tempfile.TemporaryDirectory(prefix='condiment-bottle-jar-set-rebuild-') as folder:
    generator.HERE = Path(folder)
    sys.argv.append('--skip-render')
    generator.main()
    expected = hashlib.sha256((HERE / 'exports/optimized.glb').read_bytes()).hexdigest()
    actual = hashlib.sha256((generator.HERE / 'exports/optimized.glb').read_bytes()).hexdigest()
    assert actual == expected, (actual, expected)
report = {
    'result': 'PASS',
    'method': 'Independent deterministic geometry rebuild in a temporary folder; no delivered source overwritten',
    'delivered_glb_sha256': expected, 'rebuilt_glb_sha256': actual,
    'byte_identical_glb': True,
}
(HERE / 'reports/reproducibility.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
