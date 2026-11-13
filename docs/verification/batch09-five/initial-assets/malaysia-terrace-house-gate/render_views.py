from pathlib import Path
import bpy,runpy
HERE=Path(__file__).resolve().parent
h=runpy.run_path(str(HERE/'generate.py'));bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/optimized.glb'));h['studio']()
# Ground belongs only to presentation, never the delivered export.
mat=h['mat']('Studio ground',(.34,.39,.41),0,.95)
h['box']('STUDIO_Ground',(0,0,-.055),(h['SCALE']*3,h['SCALE']*3,.1),mat,None,0)
h['render_views']()
