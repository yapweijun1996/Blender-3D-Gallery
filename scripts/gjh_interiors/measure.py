"""Inspect active-scene geometry directly from the final, identity-transform anchor GLBs."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import dist
from pathlib import Path
import struct
import zlib


def require(value, message):
    if not value:
        raise ValueError(message)


def check_swatches(png, palette):
    """The baked colour atlas uses original RGB8 PNG rows with filter type 0."""
    require(struct.unpack_from(">IIBBBBB",png,16)==(256,256,8,2,0,0,0),"Unexpected baked colour format")
    pos = 8
    compressed = bytearray()
    while pos<len(png):
        size,tag = struct.unpack_from(">I4s",png,pos)
        if tag==b"IDAT":
            compressed.extend(png[pos+8:pos+8+size])
        pos += size+12
    pixels = zlib.decompress(compressed)
    stride = 1+3*256
    row = 224*stride
    require(len(pixels)==256*stride and pixels[row]==0,"Unexpected colour scanline")
    for i,swatch in enumerate(palette):
        start = row+1+3*(16+64*i)
        require(pixels[start:start+3]==bytes.fromhex(swatch["hex"][1:]),"Exported swatch mismatch")


def inspect(path, spec, tier):
    raw = Path(path).read_bytes()
    magic,version,size,jsize,tag = struct.unpack_from("<4sIII4s",raw)
    require((magic,version,size,tag)==(b"glTF",2,len(raw),b"JSON"),"Invalid GLB header")
    g = json.loads(raw[20:20+jsize])
    n,tag = struct.unpack_from("<I4s",raw,20+jsize)
    blob = memoryview(raw)[28+jsize:]
    require(tag==b"BIN\0" and len(blob)==n,"Missing embedded buffer")
    require(all(not g.get(k) for k in ("skins","animations","cameras","extensionsUsed")),
            "Expected static core glTF")
    groups,coords,meshes,materials = [],[],set(),set()
    tris = vertices = draws = 0

    def accessor(index):
        a = g["accessors"][index]
        view = g["bufferViews"][a["bufferView"]]
        fmt = struct.Struct("<"+{"SCALAR":"","VEC3":"3"}[a["type"]]
                            +{5121:"B",5123:"H",5125:"I",5126:"f"}[a["componentType"]])
        base = view.get("byteOffset",0)+a.get("byteOffset",0)
        return [fmt.unpack_from(blob,base+i*view.get("byteStride",fmt.size)) for i in range(a["count"])]

    def visit(index):
        nonlocal tris,vertices,draws
        node = g["nodes"][index]
        require(not set(node)&{"matrix","translation","scale","rotation","skin"},"Non-identity node")
        if "mesh" in node:
            groups.append(node["name"])
            meshes.add(node["mesh"])
            for prim in g["meshes"][node["mesh"]]["primitives"]:
                require(prim.get("mode",4)==4,"Non-triangle primitive")
                pts = accessor(prim["attributes"]["POSITION"])
                inds = [i for (i,) in accessor(prim["indices"])]
                require(len(inds)%3==0,"Partial triangle")
                edges = Counter()
                neighbors = defaultdict(set)
                volumes = defaultdict(float)
                for i,j,k in zip(inds[::3],inds[1::3],inds[2::3]):
                    a,b,c = pts[i],pts[j],pts[k]
                    u = [q-p for p,q in zip(a,b)]
                    v = [q-p for p,q in zip(a,c)]
                    cross = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                    require(sum(q*q for q in cross)>1e-25,f"Zero-area triangle in {node['name']}")
                    for start,end in ((a,b),(b,c),(c,a)):
                        edges[(start,end)] += 1
                        neighbors[start].add(end)
                        neighbors[end].add(start)
                    volumes[a] += sum(q*r for q,r in zip(a,cross))
                unseen = set(neighbors)
                while unseen:
                    first = unseen.pop()
                    stack = [first]
                    volume = 0.
                    while stack:
                        pt = stack.pop()
                        volume += volumes[pt]
                        new = neighbors[pt] & unseen
                        unseen.difference_update(new)
                        stack.extend(new)
                    require(volume>1e-15,f"Inverted shell in {node['name']}")
                require(all(count==edges[end,start] for (start,end),count in edges.items()),
                        f"Open or inconsistently oriented triangle shell in {node['name']}")
                sockets = {"S04":("Sample ledge",1.15),"S10":("Hinge and level gift shelf",1.15),
                           "S12":("Level sample shelf",1.15),"S17":("Floating handset shelf",1.09)}
                socket = sockets.get(spec["slot"])
                if socket and socket[0]==node["name"]:
                    height = max(p[1] for p in pts)+spec["anchor"]["position_m"][1]
                    require(abs(height-socket[1])<=.0011,"Sample shelf outside 1.1 mm tolerance")
                materials.add(prim["material"])
                coords.extend(pts[i] for i in set(inds))
                tris += len(inds)//3
                vertices += len(pts)
                draws += 1
        for child in node.get("children",[]):
            visit(child)

    root, = g["scenes"][g["scene"]]["nodes"]
    require(g["nodes"][root]["name"]=="ASSET_"+spec["slug"].replace("-","_"),"Wrong root")
    visit(root)
    require(meshes==set(range(len(g["meshes"]))) and len(groups)>1,"Detached or ungrouped fixture")
    require(materials=={0} and len(g["materials"])==1,"Expected one swatch material")
    mat = g["materials"][0]
    require(mat.get("alphaMode","OPAQUE")=="OPAQUE" and not mat.get("extensions"),"Non-opaque finish")
    require({"metallicRoughnessTexture","baseColorTexture"}<=mat["pbrMetallicRoughness"].keys(),"Missing PBR maps")
    textures = []
    base_index = mat["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    for index,image in enumerate(g["images"]):
        view = g["bufferViews"][image["bufferView"]]
        offset = view.get("byteOffset",0)
        require(blob[offset:offset+8]==b"\x89PNG\r\n\x1a\n","Expected embedded PNG")
        w,h = struct.unpack_from(">II",blob,offset+16)
        if index==g["textures"][base_index]["source"]:
            check_swatches(blob[offset:offset+view["byteLength"]],spec["palette"])
        textures.append(dict(name=image["name"],width=w,height=h))
    lo = list(map(min,zip(*coords)))
    hi = list(map(max,zip(*coords)))
    extent = [b-a for a,b in zip(lo,hi)]
    envelope = spec["anchor"]["envelope_whd_m"]
    require(all(s<=e+.0001 for s,e in zip(extent,envelope)),"Exceeds installation envelope")
    require(abs(lo[1])<1e-4,"Anchor does not touch its mounting datum")
    if "order" in spec:
        require(dist(extent,envelope)<.0001,"Master differs from authored envelope")
    require(tris<=spec["anchor"]["triangles_per_instance"][tier],"Over triangle allowance")
    return dict(triangles=tris,bytes=len(raw),vertices=vertices,materials=[mat["name"]],
                primitives=draws,groups=groups,bounds_m={"min":[round(v,6) for v in lo],
                "max":[round(v,6) for v in hi]},textures=textures,sha256=sha256(raw).hexdigest())
