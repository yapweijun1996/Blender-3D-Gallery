"""Keep only the skeleton nodes and animations of a motion GLB (no mesh, skin, material or image)."""
import json, struct, sys

def read(path):
    data = open(path, "rb").read()
    length = struct.unpack("<I", data[12:16])[0]
    doc = json.loads(data[20:20 + length])
    start = 20 + length
    bin_length = struct.unpack("<I", data[start:start + 4])[0]
    return doc, data[start + 8:start + 8 + bin_length]

def main(source, target):
    doc, blob = read(source)
    used = sorted({s[key] for a in doc["animations"] for s in a["samplers"] for key in ("input", "output")})
    remap, views, accessors, out = {}, [], [], bytearray()
    for old in used:
        acc = dict(doc["accessors"][old])
        view = doc["bufferViews"][acc["bufferView"]]
        begin = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        size = view["byteLength"] - acc.get("byteOffset", 0)
        while len(out) % 4: out.append(0)
        views.append({"buffer": 0, "byteOffset": len(out), "byteLength": size})
        out += blob[begin:begin + size]
        acc["bufferView"] = len(views) - 1
        acc.pop("byteOffset", None)
        remap[old] = len(accessors)
        accessors.append(acc)
    animations = []
    for a in doc["animations"]:
        animations.append({**a, "samplers": [{**s, "input": remap[s["input"]], "output": remap[s["output"]]} for s in a["samplers"]]})
    nodes = []
    last = len(doc["nodes"]) - 1
    if "mesh" in doc["nodes"][last] and not any(last in n.get("children", []) for n in doc["nodes"]):
        for scene in doc["scenes"]: scene["nodes"] = [n for n in scene["nodes"] if n != last]
        doc["nodes"] = doc["nodes"][:last]  # the skinned mesh node is the last one and nothing animates it
    for node in doc["nodes"]:
        node = {k: v for k, v in node.items() if k not in ("mesh", "skin")}
        nodes.append(node)
    result = {"asset": doc["asset"], "scene": doc.get("scene", 0), "scenes": doc["scenes"], "nodes": nodes,
              "animations": animations, "accessors": accessors, "bufferViews": views,
              "buffers": [{"byteLength": len(out)}]}
    while len(out) % 4: out.append(0)
    result["buffers"][0]["byteLength"] = len(out)
    text = json.dumps(result, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    total = 12 + 8 + len(text) + 8 + len(out)
    with open(target, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(text), 0x4E4F534A) + text)
        f.write(struct.pack("<II", len(out), 0x004E4942) + bytes(out))
    print(target, total, "bytes,", len(nodes), "nodes,", len(animations), "clips")

main(sys.argv[1], sys.argv[2])
