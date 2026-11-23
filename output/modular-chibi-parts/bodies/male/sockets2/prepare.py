"""Record how to replay the finalized socket and left-hand support."""
from parcel import *

cfg = json.loads(SOCKET_FILE.read_text())
row = cfg['sockets'][CLIP]
row.update(clip=CLIP, prop='actions-hold2/props/box.glb', node='Parcel',
           bone=N+'RightHand', sourceFps=24,
           fingerRotationComposition='animated joint-local quaternion * delta quaternion')
row['fingerRotationDeltas'] = {
    N+name.removeprefix(N): value for name,value in row.get('fingerRotationDeltas',{}).items()
}
r = ParcelReplay(cfg)
prop, _ = r.prop(CLIP)
p,h = r.time(0.)
box = h @ bpy_pose(row)
q = transform(prop.points,box)
surface = tree(q,prop.faces)
left = r.joint('LeftHand',0.)
ref = row['leftHandSupport']
ref.update(mode='animated finger support', referenceTimeS=0.,
           referenceParcelTRSInLeftJoint={**json_pose(left.inverted()@box), 'scale':row['scale']},
           padTargetParcelLocal={})
for digit in DIGITS:
    vertices_ = p[np.unique(r.pads['Left',digit])]
    witness = min((surface.find_nearest(x) for x in vertices_), key=lambda h:h[3])[0]
    ref['padTargetParcelLocal'][digit] = list(C.inverted() @ box.inverted() @ witness)
cfg['composition'] = 'right joint world matrix * socket local TRS; replace the Parcel node TRS'
SOCKET_FILE.write_text(json.dumps(cfg,indent=2)+'\n')
