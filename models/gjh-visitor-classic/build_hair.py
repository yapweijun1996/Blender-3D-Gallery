"""Chestnut haircut with a closed underlayer and separately editable sculpted tufts."""

from math import cos, radians, sin, sqrt


RX, RY, RZ = .262, .217, .230
CZ, CY = 1.031, .004

# Fullness through the temple, crown and occipital bone. An ellipse alone
# narrows too early for the character's broad cheek and flattened crown.
PROFILE = (
    (.768,.112,.102),(.787,.159,.148),(.810,.191,.174),
    (.846,.219,.198),(.899,.247,.215),(.964,.264,.222),
    (1.043,.265,.226),(1.123,.255,.215),(1.193,.208,.181),
    (1.236,.140,.125),(1.254,.070,.060),(1.261,0,0),
)


def section_radii(z):
    for (lo,x0,y0),(hi,x1,y1) in zip(PROFILE,PROFILE[1:]):
        if z <= hi:
            t = max(0,(z-lo)/(hi-lo))
            return x0+(x1-x0)*t, y0+(y1-y0)*t
    return 0,0


def surface(lon, lat, lift=0):
    """Longitude zero faces the viewer. Lift follows the ellipsoid normal."""
    a, b = radians(lon), radians(lat)
    dx, dy, dz = sin(a) * cos(b), -cos(a) * cos(b), sin(b)
    normal = (dx / RX, dy / RY, dz / RZ)
    length = sqrt(sum(component * component for component in normal))
    # Behind each ear the skull rounds into a low nape. The upper crown can
    # keep its taller centre without exposing the lower rear of the head.
    posterior = max(0, -cos(a))**.7
    nape_drop = .043 * posterior * max(0, -sin(b))
    z = CZ + RZ * dz - nape_drop
    min_rx, min_ry = section_radii(z)
    temple = .019 * max(0, -sin(b)) * abs(sin(a)) * max(0,-cos(a))**.25
    return (
        (max(RX*cos(b),min_rx)+temple)*sin(a) + lift * normal[0] / length,
        CY - max(RY*cos(b),min_ry)*cos(a) + lift * normal[1] / length,
        z + lift * normal[2] / length,
    )


def underlayer(api):
    # The hem opens above the forehead, skirts the ear and closes into the nape.
    hem = (26, 24, 15, -5, -19, -58, -73, -76,
           -76, -76, -71, -54, -19, -4, 18, 24)
    verts = [(0, CY, CZ + RZ)]
    faces, colors = [], []
    rings = []
    for fraction in (.19, .40, .64, .83, 1.0):
        ring = []
        for i, bottom in enumerate(hem):
            lon = i * 360 / len(hem)
            ring.append(len(verts))
            verts.append(surface(lon, 90 + (bottom - 90) * fraction))
        rings.append(ring)
    for i in range(len(hem)):
        j = (i + 1) % len(hem)
        faces.append((0, rings[0][i], rings[0][j]))
        colors.append("#674138")
        for k, base in enumerate(("#674238", "#624037", "#593a32", "#51352e")):
            faces.append((rings[k][i], rings[k+1][i], rings[k+1][j], rings[k][j]))
            colors.append(base)
    # A shallow inner lip provides a clean contour even with the head hidden.
    centre = len(verts)
    verts.append((0, .035, .995))
    for i in range(len(hem)):
        faces.append((rings[-1][i], centre, rings[-1][(i+1) % len(hem)]))
        colors.append("#3e2927")
    cap = api.mesh("Hair • Nape and underlayer", "Hair", verts, faces, colors,
                   bone="Head", smooth=True)
    # Paint the underlying mass from root to crown so transverse construction
    # rings stay invisible between locks. The tufts still use distinct facets.
    if cap is not None:
        palette = cap.data.color_attributes["Palette"]
        for loop in cap.data.loops:
            z = verts[loop.vertex_index][2]
            t = min(1,max(0,(z-.78)/.48))
            low, high = (68,43,39), (111,72,60)
            palette.data[loop.index].color_srgb = tuple(
                (a+(b-a)*t)/255 for a,b in zip(low,high)) + (1,)


# Directable panels run from crown to tip. Each row sets longitude, elevation,
# half-width in longitude, and thickness. Width is independent of puffiness.
def panel(api, name, sections, tip, tilt, tones):
    verts, faces, colors = [], [], []
    for lon, lat, width, thickness in sections:
        verts.extend((
            surface(lon-width, lat-tilt, .0005),
            surface(lon-width*.18, lat+tilt*.12, thickness),
            surface(lon+width, lat+tilt, .0005),
            surface(lon, lat, -.014),
        ))
    faces.append((0, 3, 2, 1))
    colors.append(tones[2])
    for i in range(len(sections)-1):
        start = i * 4
        for side, color in enumerate((tones[0], tones[1], tones[2], tones[2])):
            nxt = (side+1) % 4
            faces.append((start+side, start+nxt, start+nxt+4, start+side+4))
            colors.append(color)
    end = len(verts)
    verts.append(surface(*tip))
    for side, color in enumerate((tones[0], tones[1], tones[2], tones[2])):
        faces.append((end-4+side, end-4+(side+1) % 4, end))
        colors.append(color)
    # Face winding is reversed because the strips are built crown-to-nape.
    api.mesh("Hair • " + name, "Hair", verts, [tuple(reversed(f)) for f in faces],
             colors, bone="Head", smooth=True)


def tuft(api, name, centreline, widths, depths, tones):
    # The short crown wings lift free of the scalp. Their points lean sideways.
    verts = []
    for (x, y, z), w, d in zip(centreline, widths, depths):
        verts.extend(((x, y-d, z-.003), (x, y-.001, z+w),
                      (x, y+d, z-.002), (x, y, z-w*.65)))
    tip = centreline[-1]
    verts.append(tip)
    faces = [(0, 1, 2, 3)]
    colors = [tones[2]]
    for k in range(len(widths)-1):
        for i in range(4):
            j = (i+1) % 4
            faces.append((4*k+i,4*(k+1)+i,4*(k+1)+j,4*k+j))
            colors.append(tones[i%3])
    offset = 4*(len(widths)-1)
    for i in range(4):
        faces.append((offset+i,len(verts)-1,offset+(i+1)%4))
        colors.append(tones[i%3])
    if tip[0] < centreline[0][0]:
        faces = [tuple(reversed(f)) for f in faces]
    api.mesh("Hair • " + name, "Hair", verts, faces, colors, bone="Head", smooth=True)


def build_hair(api):
    underlayer(api)
    chestnut = ("#795044", "#714638", "#4b302a")
    dark = ("#654034", "#59372e", "#432b25")
    warm = ("#784d41", "#70463b", "#52342c")
    shade = ("#70483d", "#663f34", "#4a2e28")

    # Tiered far-side accents precede the foreground bangs.
    for name, path, tip, tilt, tones in (
        ("Left whisk", [(-54,62,19,.010),(-67,44,20,.015)], (-86,32,.038), 4, warm),
        ("Left ear veil", [(-62,40,17,.010),(-72,19,17,.019),(-71,-1,11,.015)], (-65,-25,.005), 2, dark),
        ("Left wing", [(-70,54,21,.013),(-84,37,18,.018)], (-99,14,.031), 4, shade),
        ("Right whisk", [(55,56,22,.013),(72,37,19,.014)], (92,23,.034), -3, warm),
        ("Right ear veil", [(66,39,20,.009),(73,15,18,.022),(70,-3,12,.014)], (64,-25,.004), -2, dark),
        ("Right wing", [(68,52,19,.011),(90,32,21,.022)], (107,13,.031), -4, shade),
        ("Left fringe", [(-12,68,35,.009),(-30,46,25,.018),(-44,23,18,.021),(-48,9,10,.013)], (-50,0,.007), -2, shade),
        ("Short fringe", [(-5,66,23,.012),(-16,43,20,.020),(-23,28,17,.021)], (-32,10,.015), -4, warm),
        ("Right fringe", [(28,65,25,.010),(40,43,25,.019),(42,22,17,.022),(45,9,11,.015)], (46,1,.009), -2, warm),
        ("Swept forelock", [(30,67,32,.011),(16,47,29,.025),(6,24,21,.029),(-5,8,10,.024)], (-10,-1,.014), -5, chestnut),
        ("Left nape", [(-98,34,16,.013),(-108,15,19,.014),(-108,-5,16,.016)], (-111,-27,.007), 1, shade),
        ("Left shoulder lock", [(-102,66,24,.011),(-111,44,25,.020)], (-126,22,.033), -5, warm),
        ("Back left broad lock", [(-123,65,22,.013),(-139,39,22,.023),(-140,16,19,.020)], (-151,-20,.009), -4, warm),
        ("Back centre lock", [(-162,74,32,.015),(-170,49,26,.025),(-177,25,21,.024),(180,-1,17,.020)], (173,-31,.014), 5, chestnut),
        ("Back right broken lock", [(166,72,23,.013),(153,47,24,.022),(142,18,20,.020)], (132,-12,.013), 2, warm),
        ("Right shoulder lock", [(116,68,24,.012),(112,44,22,.022)], (129,23,.034), -4, shade),
        ("Right nape", [(98,34,16,.013),(108,15,18,.019),(107,-4,16,.012)], (114,-28,.007), -3, dark),
    ):
        panel(api, name, path, tip, tilt, tones)
    tuft(api, "Crown sweep",
         [( .055,-.015,1.245),(.016,-.020,1.265),(-.025,-.008,1.280),(-.060,.003,1.300)],
         [.013,.020,.014],[.028,.037,.023], chestnut)
    tuft(api, "Crown flick",
         [(.031,.010,1.244),(.079,.022,1.258),(.102,.030,1.274)],
         [.012,.010],[.021,.014], shade)
