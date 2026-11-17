"""Regenerate in a temporary directory and compare actual delivery bytes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('asset_generator', HERE/'generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
expected = hashlib.sha256((HERE/'exports/optimized.glb').read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='escalator-detail-rebuild-') as temp:
    generator.HERE = Path(temp)
    sys.argv = ['generate.py','--skip-render']
    generator.main()
    actual = hashlib.sha256((Path(temp)/'exports/optimized.glb').read_bytes()).hexdigest()
    assert expected == actual, (expected,actual)
report = {'result':'PASS','method':'Fresh deterministic procedural rebuild in a disposable directory',
          'canonical_glb_sha256':expected,'rebuilt_glb_sha256':actual,
          'byte_identical':True,'canonical_source_unchanged':True,'random_inputs':False}
(HERE/'reports/reproducibility.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
