from pathlib import Path
import bpy,importlib.util,hashlib,json,sys
# Usage: blender --background --python this.py -- FIXTURE_DIRECTORY OUTPUT_JSON
args=sys.argv[sys.argv.index('--')+1:];base=Path(args[0]);out=[]
for slug in ['hdb-drop-off-porch','hawker-stall-roller-shutter','hawker-stall-exhaust-hood','hawker-stall-stainless-counter','hawker-stall-queue-sign']:
 p=base/slug;r=json.loads((p/'reports/sources.json').read_text());b=p/'reports/source-edit'/(slug+'-edited.blend');bpy.ops.wm.open_mainfile(filepath=str(b));target=bpy.data.objects[r['edited_mesh']];assert abs(target.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value-.77)<1e-5
 sp=importlib.util.spec_from_file_location('asset_generator',p/'generate.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);dest=p/'reports/source-edit/reopened.glb';m.export(dest)
 assert dest.read_bytes()==(p/'reports/source-edit/edited.glb').read_bytes(),slug
 out.append({'id':slug,'editedBlendReopened':True,'reexportByteIdentical':True,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
Path(args[1]).write_text(json.dumps(out,indent=2)+'\n')
