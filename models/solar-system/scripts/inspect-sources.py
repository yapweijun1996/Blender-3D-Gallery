"""Reopen each independent .blend with auto-execution disabled and inspect packed inputs."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rows=[]
for p in sorted((ROOT/'sources').glob('*.blend')):
 bpy.ops.wm.open_mainfile(filepath=str(p),load_ui=False,use_scripts=False)
 roots=[o for o in bpy.context.scene.objects if o.name.startswith('ASSET_')]
 missing=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).is_file()]
 row=dict(id=p.stem,source_reopen='PASS' if len(roots)==1 and not missing else 'FAIL',root_names=[o.name for o in roots],meshes=sum(o.type=='MESH' for o in bpy.context.scene.objects),packed_images=sum(bool(im.packed_file) for im in bpy.data.images),missing=missing)
 rows.append(row)
(ROOT/'reports'/'source-validation.json').write_text(json.dumps(rows,indent=2)+'\n')
assert len(rows)==17 and all(r['source_reopen']=='PASS' for r in rows)
