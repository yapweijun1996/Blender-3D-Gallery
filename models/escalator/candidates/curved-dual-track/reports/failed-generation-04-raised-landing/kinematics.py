import math,bisect
ANGLE=math.pi/6;TRANS_R=1.5;H=.2;GAP=.004;DEPTH=.396
def make_track(turn_r, rotation_sign):
    rise = 3.0
    straight = (rise - 2 * TRANS_R * (1 - math.cos(ANGLE))) / math.sin(ANGLE)
    flat = 1.2
    estimated = 2 * (2 * flat + 2 * TRANS_R * ANGLE + straight) + 2 * math.pi * turn_r
    count = math.ceil(estimated / 0.4)
    flat += (count * 0.4 - estimated) / 4
    upper = []
    for i in range(121):
        upper.append((flat * i / 120, 0.0, 0.0, 'lower_flat'))
    y, z = upper[-1][:2]
    for i in range(1, 181):
        a = ANGLE * i / 180
        upper.append((y + TRANS_R * math.sin(a), z + TRANS_R * (1 - math.cos(a)), 0.0, 'lower_transition'))
    y, z = upper[-1][:2]
    for i in range(1, 601):
        upper.append((y + straight * i / 600 * math.cos(ANGLE), z + straight * i / 600 * math.sin(ANGLE), 0.0, 'incline'))
    y, z = upper[-1][:2]
    for i in range(1, 181):
        a = ANGLE * (1 - i / 180)
        upper.append((y + TRANS_R * (math.sin(ANGLE) - math.sin(a)), z + TRANS_R * (math.cos(a) - math.cos(ANGLE)), 0.0, 'upper_transition'))
    y, z = upper[-1][:2]
    for i in range(1, 121):
        upper.append((y + flat * i / 120, z, 0.0, 'upper_flat'))
    path = list(upper)
    y, z = upper[-1][:2]
    for i in range(1, 361):
        a = math.pi * i / 360
        path.append((y + turn_r * math.sin(a), z - turn_r + turn_r * math.cos(a), rotation_sign * math.pi * (3 * (a / math.pi) ** 2 - 2 * (a / math.pi) ** 3), 'upper_turn'))
    for y, z, _, reg in reversed(upper[:-1]):
        path.append((y, z - 2 * turn_r, rotation_sign * math.pi, 'return_' + reg))
    y, z = upper[0][:2]
    for i in range(1, 361):
        a = math.pi + math.pi * i / 360
        path.append((y + turn_r * math.sin(a), z - turn_r + turn_r * math.cos(a), rotation_sign * math.pi * (1 + 3 * ((a - math.pi) / math.pi) ** 2 - 2 * ((a - math.pi) / math.pi) ** 3), 'lower_turn'))
    lens = [0.0]
    for a, b in zip(path, path[1:]):
        lens.append(lens[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    L = lens[-1]
    pitch = L / count

    def pose(s):
        s %= L
        i = min(len(path) - 2, bisect.bisect_right(lens, s) - 1)
        t = (s - lens[i]) / (lens[i + 1] - lens[i])
        a, b = path[i:i + 2]
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2]), a[3])
    return (pose, L, count, pitch, flat)

def profile(pitch):
    arc = []
    for i in range(17):
        z = -H + H * i / 16
        arc.append((pitch - math.sqrt(pitch * pitch - z * z) + GAP, z))
    return [(GAP, 0), (DEPTH, 0), (DEPTH, -H)] + arc[:-1]
