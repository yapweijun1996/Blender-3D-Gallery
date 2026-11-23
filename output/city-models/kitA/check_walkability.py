"""Check final GLB triangles against measured, continuous walking corridors."""
import hashlib
import json
import math
import struct
from pathlib import Path

KIT = Path(__file__).resolve().parent
HEIGHT = 1.55
# Route coordinates use X across and Y towards the back, relative to the authored datum.
CHECKS = {
    'hdb_void_deck': {
        'datum_offset': 0, 'floor': (-4, 4, .12),
        'routes': [
            ('front-to-rear between pillars and stairs', .45, 2.85, -4.3, 4.3),
            ('lobby cross-route past mailboxes and notice board', -4.5, 2.85, .15, 1.65),
        ],
    },
    'public_market': {
        'datum_offset': 0, 'floor': (-9.2, 9.2, .24),
        'routes': [
            ('front-to-rear main aisle between the six stalls', -2.90, 2.90, -9.5, 9.5),
            ('cross-aisle between front and middle stalls', -5.40, 5.40, -3.575, -1.925),
            ('cross-aisle between middle and rear stalls', -5.40, 5.40, 1.925, 3.575),
        ],
    },
    'hdb_coffee_shop': {
        'datum_offset': 1.525, 'floor': (-.35, 3.4, .10),
        'routes': [
            ('open frontage to seating bay', 1.05, 2.75, -1.85, 2.95),
        ],
    },
    'provision_shop': {
        'datum_offset': 1.175, 'floor': (-.25, 2.6, .08),
        'routes': [
            ('between door hinge and display to shop interior', .16, 1.58, -1.50, 2.10),
        ],
    },
}


# Centre X/Y and half-width/half-depth of original supports near the approaches.
SUPPORTS = {
    'hdb_void_deck': [(x,y,.225,.225) for x in (-5.6,0,5.6) for y in (-3.6,3.6)],
    'public_market': [(x,y,.125,.125) for x in (-5.8,5.8) for y in (-8.5,8.5)],
    'hdb_coffee_shop': ([(x,0,.10,.15) for x in (-2.9,.9,2.9)]
                        + [(-1,-.02,1.8,.075),(-2.75,.10,.05,.21),(.75,.10,.05,.21)]),
    'provision_shop': ([(x,0,.10,.16) for x in (-1.9,1.9)]
                       + [(x,-.02,.0275,.04) for x in (-1.72,.11,1.72)]),
}


def triangles(path, datum_offset):
    data = path.read_bytes()
    json_length = struct.unpack_from('<I', data, 12)[0]
    doc = json.loads(data[20:20+json_length])
    binary = memoryview(data)[28+json_length:]

    def unpack_accessor(index, components):
        accessor = doc['accessors'][index]
        view = doc['bufferViews'][accessor['bufferView']]
        offset = view.get('byteOffset', 0)+accessor.get('byteOffset', 0)
        code = {5126: 'f', 5123: 'H', 5125: 'I', 5121: 'B'}[accessor['componentType']]
        fmt = '<'+code*components
        stride = view.get('byteStride', struct.calcsize(fmt))
        return [struct.unpack_from(fmt, binary, offset+i*stride) for i in range(accessor['count'])]

    result = []
    for primitive in doc['meshes'][0]['primitives']:
        vertices = [(x, -z+datum_offset, y)
                    for x,y,z in unpack_accessor(primitive['attributes']['POSITION'], 3)]
        indices = [i for (i,) in unpack_accessor(primitive['indices'], 1)]
        result += [tuple(vertices[i] for i in indices[j:j+3]) for j in range(0,len(indices),3)]
    return result, hashlib.sha256(data).hexdigest()


def clip(polygon, distance):
    if not polygon:
        return []
    result = []
    start = polygon[-1]
    d_start = distance(start)
    for end in polygon:
        d_end = distance(end)
        if (d_start >= 0) != (d_end >= 0):
            portion = d_start/(d_start-d_end)
            result.append(tuple(a+(b-a)*portion for a,b in zip(start,end)))
        if d_end >= 0:
            result.append(end)
        start, d_start = end, d_end
    return result


def floor_sections(front, rear, rise):
    run = rise*8
    return [
        (-math.inf, front, 0, 0),
        (front, front+run, 1/8, -front/8),
        (front+run, rear-run, 0, rise),
        (rear-run, rear, -1/8, rear/8),
        (rear, math.inf, 0, 0),
    ]


def assert_clear(mesh, x_min, x_max, y_min, y_max, slope, intercept):
    planes = (
        lambda p: p[0]-x_min, lambda p: x_max-p[0],
        lambda p: p[1]-y_min, lambda p: y_max-p[1],
        lambda p: p[2]-(slope*p[1]+intercept+.005),
        lambda p: slope*p[1]+intercept+HEIGHT-p[2],
    )
    for triangle in mesh:
        intersection = triangle
        for plane in planes:
            intersection = clip(intersection, plane)
            if not intersection:
                break
        if intersection:
            raise ValueError(f'Blocked route at {intersection[0]}')


def floor_height(mesh, x, y, maximum_z):
    heights = []
    for (ax,ay,az), (bx,by,bz), (cx,cy,cz) in mesh:
        determinant = (by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(determinant) < 1e-9:
            continue
        u = ((by-cy)*(x-cx)+(cx-bx)*(y-cy))/determinant
        v = ((cy-ay)*(x-cx)+(ax-cx)*(y-cy))/determinant
        w = 1-u-v
        if min(u,v,w) >= -1e-7 and (height := az*u+bz*v+cz*w) <= maximum_z:
            heights.append(height)
    return max(heights, default=-math.inf)


def assert_supported(mesh, spec, supports):
    profile = floor_sections(*spec['floor'])
    points = {p for triangle in mesh for p in triangle}
    margins = []
    for x,y,dx,dy in supports:
        for x_edge in (x-dx,x+dx):
            for y_edge in (y-dy,y+dy):
                grade = next(slope*y_edge+intercept for low,high,slope,intercept
                             in profile if low <= y_edge <= high)
                elevations = [pz for px,py,pz in points
                              if abs(px-x_edge) < .016 and abs(py-y_edge) < .016]
                margin = grade-min(elevations, default=math.inf)
                if margin < .002:
                    raise ValueError(f'Support is above grade at {(x_edge,y_edge)}')
                margins.append(margin)
    return {'supports': len(supports), 'minimum_corner_embed_metres': round(min(margins),4)}


def verify():
    reports = {}
    for name, spec in CHECKS.items():
        stem = KIT/f'{name}.glb'
        mesh, sha256 = triangles(stem, spec['datum_offset'])
        report = {'sha256': sha256, 'result': 'PASS', 'vertical_clearance_metres': HEIGHT,
                  'floor_approach_slope': '1:8', 'routes': []}
        front,rear,_ = spec['floor']
        for label, x0, x1, y0, y1 in spec['routes']:
            for begin,end,slope,intercept in floor_sections(*spec['floor']):
                low,high = max(y0,begin),min(y1,end)
                if low < high:
                    assert_clear(mesh, x0,x1,low,high,slope,intercept)
                if low < high and front <= low and high <= rear:
                    for i in range(math.ceil((high-low)/.20)+1):
                        y = low+(high-low)*i/max(1,math.ceil((high-low)/.20))
                        z = slope*y+intercept
                        for x in (x0+.002, (x0+x1)/2, x1-.002):
                            actual = floor_height(mesh,x,y,z+.006)
                            if abs(actual-z) > .003:
                                raise ValueError(f'{name} {label}: unsupported floor at {(x,y,z)}')
            report['routes'].append({
                'name': label, 'tested_clear_width_metres': round(min(x1-x0,y1-y0),3),
                'authored_footprint_metres': {'x': [x0,x1], 'back': [y0,y1]},
            })
        report['approach_support_contact'] = assert_supported(mesh, spec, SUPPORTS[name])
        reports[stem.name] = report
        print(stem.name, [(r['name'], r['tested_clear_width_metres']) for r in report['routes']])
    target = KIT/'.work'/'walkability.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(reports,indent=2)+'\n')


if __name__ == '__main__':
    verify()
