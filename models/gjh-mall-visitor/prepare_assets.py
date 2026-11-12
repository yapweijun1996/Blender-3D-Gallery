"""Produce lightweight previews and metadata only from verified current source/export receipts."""
from pathlib import Path
import hashlib
import json
from PIL import Image
root=Path(__file__).resolve().parent
metrics=json.loads((root/'reports/assets.json').read_text())
source=json.loads((root/'reports/sources.json').read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert metrics['sha256']==digest(root/'exports/gjh-mall-visitor.glb')
assert source['source_sha256']==digest(root/'sources/gjh-mall-visitor.blend')
assert source['generator_sha256']==digest(root/'generate.py')
assert metrics['validation']['errors']==metrics['validation']['warnings']==0
for name in ('front','side','back','walk','sprint','portrait'):
 image=Image.open(root/'previews'/f'{name}.png').convert('RGB')
 image.save(root/'previews'/f'{name}.webp',quality=84,method=6)
metadata={
 'id':'gjh-mall-visitor','name':'GJH Mall Visitor','category':'Characters','status':'validated','created':'2026-11-12',
 'author':'Yap Wei Jun project / agent-assisted procedural modeling',
 'blender_version':source['blender_version'],
 'creation_method':'Original deterministic Blender geometry, native PBR materials and articulated in-place NLA animation; private visual reference not embedded or redistributed.',
 'generator':'generate.py',
 'paths':{'glb':'exports/gjh-mall-visitor.glb','source':'sources/gjh-mall-visitor.blend','preview':'previews/front.webp'},
 'display':{'previewRotationY':0,'units':'metres','up_axis':'Blender +Z / glTF +Y','origin':'floor centre','front_axis':'Blender -Y / glTF +Z'},
 'accuracy_notes':'Original rounded mascot concept with open glasses and GJH concept polo wordmark, not an official spokesperson or endorsed trademark asset. Simplified rigid articulated joints, not cloth simulation. Native 1.72 m; idle/walk/sprint stay horizontally in place.',
 'attribution':[{'credit':'Original procedural geometry and animation created for Blender-3D-Gallery; owner-project reuse in Webpage-Design-Gallery GJH V11.'},{'credit':'Blender bundled font converted to geometry for the small concept wordmark; no font file redistributed.'}],
 'rights':"Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified.",
 'metrics':metrics,'source_verification':source,
 'budget_note':'The reference suggests 2,000–5,000 triangles. This model retains modeled glasses, face, hair and articulated limbs within an explicitly reviewed 15,000-triangle / 25-primitive ceiling; actual counts are recorded in metrics.'
}
(root/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps({'metadata':'metadata.json','previews':6,'sha256':metrics['sha256']}))
