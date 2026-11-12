"""Run with Blender. Creates an isolated copy, edits real text, and re-exports it."""
from pathlib import Path
import shutil
import sys
import runpy
import bpy
here=Path(__file__).resolve().parent
out=Path(sys.argv[sys.argv.index('--')+1]).resolve()
assert out != here and not out.exists(), 'Choose a new isolated output directory'
for name in ('sources','exports','previews'):
    (out/name).mkdir(parents=True)
shutil.copy2(here/'generate.py',out/'generate.py')
bpy.ops.wm.open_mainfile(filepath=str(here/'sources/mall-waste-sorting-station.blend'))
bpy.context.preferences.filepaths.save_version=0
bpy.data.objects['Recycle editable stream label'].data.body='PLASTIC'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'sources/mall-waste-sorting-station.blend'),compress=True)
sys.argv=['generate.py','--','--export-source']
runpy.run_path(str(out/'generate.py'),run_name='__main__')
