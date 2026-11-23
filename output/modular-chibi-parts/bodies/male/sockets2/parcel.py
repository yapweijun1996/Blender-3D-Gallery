"""Replay the parcel socket against each shipped body and action bank."""
from geometry import *
from geometry import record as record_pose

BODY_NAME = HERE.parent.name
BANK = HERE.parent / ('motion_female.glb' if BODY_NAME == 'female' else 'round2/motion_male_fixed.glb')
BODY_FILE = HERE.parent / f'body_{BODY_NAME}.glb'
SOCKET_FILE = HERE / f'sockets_{BODY_NAME}.json'
CLIP = 'hold_box'


class ParcelReplay(Replay):
    def __init__(self, config=None):
        super().__init__(BODY_FILE, BANK)
        self.scene.render.fps = 120
        self.select(CLIP)
        self.bind_asset = GLB(BODY_FILE)
        self.deltas = {}
        self.delta_gltf = {}
        self.bridges = {}
        self.delta_tracks = {}
        if config:
            socket = config['sockets'][CLIP]
            for key, value in socket.get('fingerRotationDeltas', {}).items():
                self.delta_gltf[key.removeprefix(N)] = Quaternion((value[3], *value[:3])).normalized()
            track = socket.get('fingerRotationTracks')
            if track:
                self.delta_rate = track['sampleRateHz']
                for key, values in track['jointQuaternions'].items():
                    self.delta_tracks[key.removeprefix(N)] = [Quaternion((q[3],*q[:3])).normalized() for q in values]
            self.bridges = {name:self.bridge(name) for name in self.delta_gltf.keys() | self.delta_tracks.keys()}

    def sample_delta(self, name, time):
        if name in self.delta_gltf:
            return self.delta_gltf[name]
        values = self.delta_tracks[name]
        tick = min(len(values)-1,max(0.,time*self.delta_rate))
        lo = math.floor(tick)
        return values[lo].slerp(values[min(lo+1,len(values)-1)],tick-lo)

    def get_pads(self):
        if BODY_NAME == 'male':
            return super().get_pads()
        from female_geometry import pads
        from types import SimpleNamespace
        stage = SimpleNamespace(rest=transform(self.rest, self.body.matrix_world),
                                faces=self.body_faces, arm=self.arm,
                                labels=np.char.add(N, self.labels))
        return {(side, digit): patch for side in SIDES for digit, patch in pads(stage, side).items()}

    def bridge(self, name):
        rig_rest = self.arm.matrix_world @ self.arm.data.bones[N+name].matrix_local
        joint_rest = C @ gltf_world(self.bind_asset, name)
        return (rig_rest.inverted() @ joint_rest).to_quaternion()

    def time(self, time):
        # Explicitly restore the last unmodified values before evaluating the action.
        for name, rotation in getattr(self, 'last_base', {}).items():
            self.arm.pose.bones[N+name].rotation_quaternion = rotation
        frames = time*self.scene.render.fps
        self.scene.frame_set(math.floor(frames), subframe=frames%1)
        self.last_base = {}
        self.deltas = {}
        for name, bridge in self.bridges.items():
            local = self.sample_delta(name,time)
            delta = self.deltas[name] = bridge @ local @ bridge.inverted()
            bone = self.arm.pose.bones[N+name]
            assert bone.rotation_mode == 'QUATERNION'
            self.last_base[name] = bone.rotation_quaternion.copy()
            bone.rotation_quaternion = bone.rotation_quaternion @ delta
        bpy.context.view_layer.update()
        points = transform(vertices(self.body, posed=True), self.body.matrix_world)
        return points, self.joint('RightHand', time)

    def joint(self, name, time):
        return C @ gltf_world(self.motion, name, self.tracks, time) @ C.inverted()

    def replay_error(self, time):
        probes = ((0,0,0),(.06,0,0),(0,.06,0),(0,0,.06))
        errors = []
        for name in ('RightHand','LeftHand',*self.deltas):
            bridge = self.bridges.get(name) or self.bridge(name)
            actual = self.arm.matrix_world @ self.arm.pose.bones[N+name].matrix @ bridge.to_matrix().to_4x4()
            expected = self.joint(name,time) @ C
            if name in self.bridges:
                expected @= self.sample_delta(name,time).to_matrix().to_4x4()
            errors.extend((actual@Vector(p)-expected@Vector(p)).length*1000 for p in probes)
        return max(errors)

    def times(self):
        from fractions import Fraction
        from itertools import chain
        grids = (48, 120 if BODY_NAME == 'female' else 192, 480)
        clocks = (Fraction(i, rate) for rate in grids for i in range(round(self.end_time*rate)+1))
        return sorted(set(map(float, clocks)) | {self.end_time})


def original_socket():
    source = HERE.parent / 'sockets' / SOCKET_FILE.name
    socket = json.loads(source.read_text())['sockets'][CLIP]
    if BODY_NAME == 'female':
        local = socket['gltf_joint_local']
        return dict(translation=local['translation_m'], rotation=local['quaternion_xyzw'])
    return dict(translation=socket['translation'], rotation=socket['rotation'])
