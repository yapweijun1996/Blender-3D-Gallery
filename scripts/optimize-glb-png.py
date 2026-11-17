"""Recompress embedded PNGs losslessly; keep the smaller original when it wins."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import struct

from PIL import Image

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('files', nargs='+', type=Path)
parser.add_argument('--report', required=True, type=Path)
args = parser.parse_args()
reports = []
for file in args.files:
    original = file.read_bytes()
    assert original[:4] == b'glTF' and struct.unpack_from('<I', original, 4)[0] == 2
    size = struct.unpack_from('<I', original, 12)[0]
    source = json.loads(original[20:20 + size])
    assert original[24 + size:28 + size] == b'BIN\0' and len(source['buffers']) == 1
    assert all(not b.get('uri') for b in source['buffers'])
    data = original[28 + size:]
    document = copy.deepcopy(source)
    images = {image['bufferView'] for image in source.get('images', []) if image.get('mimeType') == 'image/png'}
    blocks = []
    length = 0
    changed = []
    for index, view in enumerate(document['bufferViews']):
        assert view['buffer'] == 0 and not view.get('extensions')
        raw = data[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']]
        payload = raw
        if index in images:
            with Image.open(io.BytesIO(raw)) as image:
                # This path handles the existing single-frame PNG maps without palette changes.
                assert image.format == 'PNG' and image.mode in ('RGB', 'RGBA') and image.n_frames == 1
                assert raw[24] == 8 and not image.info, 'Review PNG colour metadata before recompression'
                output = io.BytesIO()
                image.save(output, format='PNG', optimize=True, compress_level=9)
                candidate = output.getvalue()
                with Image.open(io.BytesIO(candidate)) as decoded:
                    assert image.mode == decoded.mode and image.size == decoded.size
                    assert image.tobytes() == decoded.tobytes()
                if len(candidate) < len(raw):
                    payload = candidate
                    changed.append({'bufferView': index, 'dimensions': list(image.size),
                                    'original_bytes': len(raw), 'bytes': len(payload),
                                    'pixel_sha256': hashlib.sha256(image.tobytes()).hexdigest()})
        padding = (-length) % 4
        blocks.append(b'\0' * padding)
        length += padding
        view['byteOffset'] = length
        view['byteLength'] = len(payload)
        blocks.append(payload)
        length += len(payload)
    if not changed:
        print(file, 'original PNGs retained', flush=True)
        continue
    binary = b''.join(blocks)
    document['buffers'][0]['byteLength'] = len(binary)
    text = json.dumps(document, separators=(',', ':')).encode()
    text += b' ' * ((-len(text)) % 4)
    binary += b'\0' * ((-len(binary)) % 4)
    result = (struct.pack('<4sIIII', b'glTF', 2, 28 + len(text) + len(binary), len(text), 0x4e4f534a)
              + text + struct.pack('<II', len(binary), 0x004e4942) + binary)
    assert len(result) < len(original)
    # Every non-image byte range retains its original payload, including animation and skin buffers.
    for index, (before, after) in enumerate(zip(source['bufferViews'], document['bufferViews'])):
        a = data[before.get('byteOffset', 0):before.get('byteOffset', 0) + before['byteLength']]
        b = binary[after['byteOffset']:after['byteOffset'] + after['byteLength']]
        if index not in images:
            assert a == b
    reports.append({'file': str(file), 'original_bytes': len(original), 'bytes': len(result),
                    'original_sha256': hashlib.sha256(original).hexdigest(),
                    'sha256': hashlib.sha256(result).hexdigest(), 'pngs': changed})
    file.write_bytes(result)
    print(file, len(original), '->', len(result), flush=True)
args.report.parent.mkdir(parents=True, exist_ok=True)
args.report.write_text(json.dumps(reports, indent=2) + '\n')
