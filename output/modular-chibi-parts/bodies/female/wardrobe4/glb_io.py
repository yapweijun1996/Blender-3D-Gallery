"""Minimal GLB packing for lossless geometry and skeleton preservation."""
from copy import deepcopy
import json
import os
import struct

import numpy as np


class Glb:
    def __init__(self, path=None):
        if path is None:
            self.doc = {"asset": {"version": "2.0"}, "bufferViews": [], "accessors": []}
            self.bin = bytearray()
        else:
            data = path.read_bytes()
            assert data[:4] == b"glTF"
            length = struct.unpack_from("<I", data, 12)[0]
            self.doc = json.loads(data[20:20 + length])
            self.bin = bytearray(data[28 + length:])

    def payload(self, index):
        view = self.doc["bufferViews"][index]
        offset = view.get("byteOffset", 0)
        return self.bin[offset:offset + view["byteLength"]]

    def view(self, payload, **metadata):
        self.bin.extend(b"\0" * (-len(self.bin) % 4))
        index = len(self.doc["bufferViews"])
        self.doc["bufferViews"].append(dict(metadata, buffer=0, byteOffset=len(self.bin),
                                            byteLength=len(payload)))
        self.bin.extend(payload)
        return index

    def floats(self, values, kind):
        data = np.asarray(values, dtype="<f4")
        acc = dict(bufferView=self.view(data.tobytes()), componentType=5126,
                   count=len(data), type=kind)
        if kind == "SCALAR":
            acc.update(min=[float(data.min())], max=[float(data.max())])
        index = len(self.doc["accessors"])
        self.doc["accessors"].append(acc)
        return index

    def accessor(self, index):
        acc = self.doc["accessors"][index]
        view = self.doc["bufferViews"][acc["bufferView"]]
        components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[acc["type"]]
        dtype = np.dtype({5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[acc["componentType"]])
        offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        size = dtype.itemsize * components
        return np.ndarray((acc["count"], components), dtype=dtype, buffer=self.bin, offset=offset,
                          strides=(view.get("byteStride", size), dtype.itemsize))

    def repack_views(self, replacements):
        old_views = self.doc["bufferViews"]
        payloads = [self.payload(i) for i in range(len(old_views))]
        self.bin = bytearray()
        self.doc["bufferViews"] = []
        for index, view in enumerate(old_views):
            fields = {k: v for k, v in view.items() if k not in {"buffer", "byteOffset", "byteLength"}}
            self.view(replacements.get(index, payloads[index]), **fields)

    def skeleton(self):
        out = Glb()
        doc = self.doc
        indices = [i for i, node in enumerate(doc["nodes"]) if "mesh" not in node]
        remap = {i: k for k, i in enumerate(indices)}
        nodes = [deepcopy(doc["nodes"][i]) for i in indices]
        for node in nodes:
            if "children" in node:
                node["children"] = [remap[i] for i in node["children"] if i in remap]
        out.doc.update(nodes=nodes, scene=0, scenes=[{"nodes": [remap[i] for i in doc["scenes"][0]["nodes"]
                                                                if i in remap]}], skins=[], animations=[])
        for skin in doc["skins"]:
            record = {"joints": [remap[i] for i in skin["joints"]]}
            record["inverseBindMatrices"] = out.floats(self.accessor(skin["inverseBindMatrices"]), "MAT4")
            if "skeleton" in skin:
                record["skeleton"] = remap[skin["skeleton"]]
            out.doc["skins"].append(record)
        return out

    def write(self, path):
        self.bin.extend(b"\0" * (-len(self.bin) % 4))
        self.doc["buffers"] = [{"byteLength": len(self.bin)}]
        js = json.dumps(self.doc, separators=(",", ":"), allow_nan=False).encode()
        js += b" " * (-len(js) % 4)
        header = struct.pack("<4sII", b"glTF", 2, 28 + len(js) + len(self.bin))
        temp = path.with_name(f".{path.name}.{os.getpid()}.building")
        temp.write_bytes(header + struct.pack("<I4s", len(js), b"JSON") + js +
                         struct.pack("<I4s", len(self.bin), b"BIN\0") + self.bin)
        temp.replace(path)
