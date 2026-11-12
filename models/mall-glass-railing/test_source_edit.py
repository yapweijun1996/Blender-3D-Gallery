"""Copy saved sources to an isolated output directory, change only 1 m glass opacity."""
import bpy,sys,shutil,json
from pathlib import Path
root=Path(__file__).resolve().parent
out=Path(sys.argv[sys.argv.index('--')+1]).resolve()
assert out!=root and not out.exists(), 'Use a fresh isolated output directory'
out.mkdir(parents=True)
shutil.copytree(root/'sources',out/'sources')
shutil.copy(root/'generate.py',out/'generate.py')
path=out/'sources/mall-glass-railing-1m.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
m=next(m for m in bpy.data.materials if m.name.startswith('GLASS '))
m.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.44
m.diffuse_color=(*m.diffuse_color[:3],.44)
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
print('Isolated source changed; run copied generate.py -- --export-source')
