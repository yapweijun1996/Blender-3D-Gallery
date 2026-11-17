"""Compare saved-source export and a clean procedural rebuild with the delivery."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import bpy

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('shelf_generator', HERE / 'generate.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    source = HERE / 'sources/shelf-food-aisle.blend'
    source_hash = digest(source)
    output = Path(tempfile.mkdtemp(prefix='shelf-food-aisle-repro-'))
    bpy.ops.wm.open_mainfile(filepath=str(source))
    generator.export(output / 'source.glb')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1
    generator.build()
    generator.export(output / 'rebuild.glb')
    hashes = {label: digest(path) for label, path in {
        'delivery': HERE / 'exports/optimized.glb',
        'saved_source_export': output / 'source.glb',
        'clean_rebuild': output / 'rebuild.glb'}.items()}
    assert len(set(hashes.values())) == 1, hashes
    assert digest(source) == source_hash
    report = {'result': 'PASS', 'blender_version': bpy.app.version_string,
              'sha256': hashes, 'original_source_unchanged': True}
    (HERE / 'reports/reproducibility.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
