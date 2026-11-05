// Run on macOS with sips. Rebuild demo-only GLBs from the registered sources;
// original geometry, materials, animations and gallery downloads are retained.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { loadCatalog } from './catalog.mjs';
import { solarSceneAssets } from '../src/solar/assets.js';

const root = 'models/solar-demo';
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
// Only opaque colour/emissive maps are JPEG encoded. Normal maps and
// Saturn's transparent ring remain PNG. Indices refer to source GLB images.
const jpeg = {sun:[0], mercury:[0], venus:[0], earth:[1], mars:[1], jupiter:[0], saturn:[0], uranus:[0], neptune:[0], moon:[0], pluto:[0], 'asteroid-01':[1], 'asteroid-02':[1], 'asteroid-03':[1], 'asteroid-04':[1], 'asteroid-05':[1]};
const assets = solarSceneAssets(loadCatalog().collections.flatMap(c => c.assets));
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'solar-textures-'));
const manifest = [];
try {
  for (const a of assets) {
    const bytes = fs.readFileSync(a.file);
    const jsonLen = bytes.readUInt32LE(12);
    const doc = JSON.parse(bytes.subarray(20, 20 + jsonLen).toString());
    const binOffset = 20 + jsonLen;
    if (bytes.toString('ascii', binOffset + 4, binOffset + 8) !== 'BIN\0' || doc.buffers.length !== 1) throw Error(`Unsupported GLB: ${a.id}`);
    const bin = bytes.subarray(binOffset + 8);
    const jpegImages = new Set(jpeg[a.solarId] ?? []);
    const inspectTextures = (value, material) => {
      if (!value || typeof value !== 'object') return;
      for (const [key, child] of Object.entries(value)) {
        if (key.endsWith('Texture') && child && Number.isInteger(child.index)) {
          const image = doc.textures?.[child.index]?.source;
          if (jpegImages.has(image) &&
              (!['baseColorTexture', 'emissiveTexture'].includes(key) ||
               (key === 'baseColorTexture' && (material.alphaMode ?? 'OPAQUE') !== 'OPAQUE')))
            throw Error(`Unsafe JPEG texture use: ${a.id} ${key}`);
        }
        inspectTextures(child, material);
      }
    };
    for (const material of doc.materials ?? []) inspectTextures(material, material);
    const imageByView = new Map((doc.images ?? []).map((im, i) => [im.bufferView, i]));
    const chunks = []; let length = 0;
    for (let i = 0; i < doc.bufferViews.length; i++) {
      const view = doc.bufferViews[i];
      if ((view.buffer ?? 0) !== 0 || view.extensions) throw Error(`Unsupported buffer view: ${a.id}`);
      let data = bin.subarray(view.byteOffset ?? 0, (view.byteOffset ?? 0) + view.byteLength);
      const imageIndex = imageByView.get(i);
      if (imageIndex !== undefined) {
        const image = doc.images[imageIndex];
        if (image.mimeType !== 'image/png') throw Error(`Unexpected image type: ${a.id}`);
        const input = path.join(temp, 'input.png');
        const useJpeg = (jpeg[a.solarId] ?? []).includes(imageIndex);
        const output = path.join(temp, useJpeg ? 'output.jpg' : 'output.png');
        fs.writeFileSync(input, data);
        const params = ['--resampleHeightWidthMax', '1024', '-s', 'format', useJpeg ? 'jpeg' : 'png'];
        if (useJpeg) params.push('-s', 'formatOptions', '85');
        execFileSync('sips', [...params, input, '--out', output], {stdio:'ignore'});
        data = fs.readFileSync(output);
        image.mimeType = useJpeg ? 'image/jpeg' : 'image/png';
      }
      const padding = (4 - length % 4) % 4;
      if (padding) {chunks.push(Buffer.alloc(padding)); length += padding;}
      view.byteOffset = length; view.byteLength = data.length;
      chunks.push(data); length += data.length;
    }
    const binData = Buffer.concat(chunks);
    doc.buffers[0].byteLength = binData.length;
    let json = Buffer.from(JSON.stringify(doc));
    json = Buffer.concat([json, Buffer.alloc((4 - json.length % 4) % 4, 32)]);
    const binPadding = Buffer.alloc((4 - binData.length % 4) % 4);
    const header = Buffer.alloc(20), binHeader = Buffer.alloc(8);
    header.write('glTF'); header.writeUInt32LE(2, 4); header.writeUInt32LE(20 + json.length + 8 + binData.length + binPadding.length, 8); header.writeUInt32LE(json.length, 12); header.write('JSON',16);
    binHeader.writeUInt32LE(binData.length + binPadding.length, 0); binHeader.write('BIN\0',4);
    const output = Buffer.concat([header,json,binHeader,binData,binPadding]);
    const out = `${root}/${a.id}.glb`; fs.writeFileSync(out, output);
    manifest.push({id:a.id, solarId:a.solarId, source:a.file, sourceSha256:hash(bytes), file:out, sha256:hash(output), originalBytes:bytes.length, bytes:output.length});
    console.log(`${a.id}: ${bytes.length} -> ${output.length}`);
  }
  fs.writeFileSync(`${root}/manifest.json`, JSON.stringify(manifest,null,2)+'\n');
} finally {fs.rmSync(temp,{recursive:true,force:true});}
