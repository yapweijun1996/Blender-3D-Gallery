const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

const root = __dirname;
const source = path.resolve(root, '../round3/jacket_v3.glb');
const filename = path.join(root, 'jacket_v6.glb');
const bytes = fs.readFileSync(filename);
const sha = buffer => crypto.createHash('sha256').update(buffer).digest('hex');
const digest = sha(bytes);

function save(name, data) {
    const stage = path.join(root, name + '.stage');
    fs.writeFileSync(stage, typeof data === 'string' ? data : JSON.stringify(data, null, 2) + '\n');
    fs.renameSync(stage, path.join(root, name));
}

function glb(buffer) {
    assert.equal(buffer.toString('ascii', 0, 4), 'glTF');
    assert.equal(buffer.readUInt32LE(4), 2);
    assert.equal(buffer.readUInt32LE(8), buffer.length);
    const size = buffer.readUInt32LE(12);
    return [JSON.parse(buffer.toString('utf8', 20, 20 + size)), buffer.subarray(28 + size)];
}

function imageDimensions(bytes, mimeType) {
    if (mimeType === 'image/png') return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
    assert.equal(mimeType, 'image/jpeg');
    assert.equal(bytes.readUInt16BE(0), 0xffd8);
    let offset = 2;
    while (offset + 8 < bytes.length) {
        assert.equal(bytes[offset], 0xff);
        if ([0xc0, 0xc1, 0xc2, 0xc3].includes(bytes[offset + 1])) {
            return [bytes.readUInt16BE(offset + 7), bytes.readUInt16BE(offset + 5)];
        }
        offset += 2 + bytes.readUInt16BE(offset + 2);
    }
    throw new Error('JPEG dimension marker missing');
}

function accessorRows(document, payload, index) {
    const acc = document.accessors[index];
    const width = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[acc.type];
    const read = {
        5121: [1, 'readUInt8', 255], 5123: [2, 'readUInt16LE', 65535],
        5125: [4, 'readUInt32LE', 4294967295], 5126: [4, 'readFloatLE', 1],
    }[acc.componentType];
    const view = document.bufferViews[acc.bufferView];
    const [stride, method, scale] = read;
    const step = view.byteStride ?? stride * width;
    const start = (view.byteOffset || 0) + (acc.byteOffset || 0);
    return Array.from({length: acc.count}, (_, row) => Array.from({length: width}, (_, col) =>
        payload[method](start + row * step + col * stride) / (acc.normalized ? scale : 1)));
}

async function exportCheck() {
    const validator = require('gltf-validator');
    const validatorReport = await validator.validateBytes(new Uint8Array(bytes), {
        uri: 'jacket_v6.glb', maxIssues: 0,
    });
    save('gltf_validator.json', validatorReport);
    const [doc, payload] = glb(bytes);
    const [seedDoc, seedPayload] = glb(fs.readFileSync(source));
    const primitives = doc.meshes.flatMap(mesh => mesh.primitives);
    let triangles = 0;
    let vertices = 0;
    let maximumInfluences = 0;
    let maximumWeightSumError = 0;
    let invalidJointCount = 0;
    let unweightedCount = 0;
    const texcoords = new Set();
    const uvKey = row => row.map(value => Math.round(value * 1000000)).join(',');
    for (const primitive of primitives) {
        assert.equal(primitive.mode ?? 4, 4);
        assert.equal(primitive.attributes.WEIGHTS_1, undefined);
        assert.equal(primitive.attributes.JOINTS_1, undefined);
        const skin = accessorRows(doc, payload, primitive.attributes.WEIGHTS_0);
        const joints = accessorRows(doc, payload, primitive.attributes.JOINTS_0);
        const uv = accessorRows(doc, payload, primitive.attributes.TEXCOORD_0);
        triangles += doc.accessors[primitive.indices].count / 3;
        vertices += skin.length;
        skin.forEach((row, i) => {
            const count = row.filter(weight => weight > 0).length;
            maximumInfluences = Math.max(maximumInfluences, count);
            maximumWeightSumError = Math.max(maximumWeightSumError, Math.abs(1 - row.reduce((a,b) => a+b, 0)));
            unweightedCount += Number(!count);
            invalidJointCount += joints[i].filter((joint, k) => row[k] > 0 && joint >= 65).length;
        });
        uv.forEach(row => texcoords.add(uvKey(row)));
    }
    const seedUV = new Set(seedDoc.meshes.flatMap(mesh => mesh.primitives).flatMap(primitive =>
        accessorRows(seedDoc, seedPayload, primitive.attributes.TEXCOORD_0).map(uvKey)));
    const images = doc.images.map(image => {
        const view = doc.bufferViews[image.bufferView];
        const start = view.byteOffset || 0;
        const imageBytes = payload.subarray(start, start + view.byteLength);
        return {name: image.name, mime: image.mimeType, bytes: imageBytes.length,
            dimensions: imageDimensions(imageBytes, image.mimeType)};
    });
    const jointNames = doc.skins[0].joints.map(i => doc.nodes[i].name);
    const seedNames = seedDoc.skins[0].joints.map(i => seedDoc.nodes[i].name);
    const materialDefinitionsMatch = JSON.stringify(doc.materials) === JSON.stringify(seedDoc.materials);
    const data = {
        garment_sha256: digest, bytes: bytes.length, limit_bytes: 1572864, triangles, vertices,
        meshes: doc.meshes.length, skins: doc.skins.length, joints: jointNames.length,
        joint_names_match: JSON.stringify(jointNames) === JSON.stringify(seedNames),
        cameras: doc.cameras?.length || 0, animations: doc.animations?.length || 0,
        mesh_nodes: doc.nodes.filter(node => node.mesh !== undefined).length,
        maximum_influences: maximumInfluences, unweighted_vertices: unweightedCount,
        maximum_weight_sum_error: maximumWeightSumError, invalid_joint_references: invalidJointCount,
        images, material_definitions_match_round3: materialDefinitionsMatch,
        uv: {original_unique: seedUV.size, retained: [...seedUV].filter(uv => texcoords.has(uv)).length,
            exported_unique: texcoords.size, precision_digits: 6},
        khronos_errors: validatorReport.issues.numErrors,
        khronos_warnings: validatorReport.issues.numWarnings,
    };
    data.pass = data.bytes <= data.limit_bytes && data.triangles <= 6000 && data.meshes === 1 &&
        data.skins === 1 && data.mesh_nodes === 1 && data.joints === 65 && data.joint_names_match &&
        !data.cameras && !data.animations && maximumInfluences <= 4 && !unweightedCount &&
        !invalidJointCount && maximumWeightSumError < .00001 && images.length === 3 &&
        images.every(image => image.dimensions.every(size => size <= 1024)) &&
        data.khronos_errors === 0 && data.khronos_warnings === 0;
    save('export_check.json', data);
    console.log(data);
    return data.pass;
}

const groups = {
    shared: ['walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance'],
    sit_hold: ['sit_down', 'sit_idle', 'stand_up', 'hold_item'],
    carry: ['hold_box', 'hold_bag', 'take_item'],
};

function checkMotion() {
    const clips = {};
    const sources = {};
    const text = {vertex: [], triangle: []};
    const rest = { vertex: [], triangle: [] };
    for (const [group, names] of Object.entries(groups)) {
        const load = metric => {
            const file = 'checker_' + group + '_' + metric + '.json';
            const report = JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
            assert.equal(report.garment_sha256, digest);
            assert(report.entry_sha256 && report.implementation_sha256);
            sources[file] = sha(fs.readFileSync(path.join(root,file)));
            rest[metric].push({count:report.results.rest[0], min_signed_m:report.results.rest[1],frame:1});
            return report;
        };
        const vertex = load('vertex');
        const triangle = load('triangle');
        for (const name of names) {
            const v = vertex.frames[name];
            const t = triangle.frames[name];
            assert(v.length > 0);
            assert.deepEqual(v.map(sample => sample.frame), t.map(sample => sample.frame));
            assert(v.every((sample, i) => Number.isFinite(sample.min_signed_m) &&
                (!i || sample.frame > v[i - 1].frame && sample.frame - v[i - 1].frame <= .50001)));
            assert(t.every(sample => Number.isFinite(sample.min_signed_m)));
            const vMax = Math.max(...v.map(sample => sample.count));
            const tMax = Math.max(...t.map(sample => sample.count));
            const deepest = v.concat(t).reduce((a,b) => a.min_signed_m <= b.min_signed_m ? a : b);
            clips[name] = {
                samples: v.length, integer: v.filter(sample => Number.isInteger(sample.frame)).length,
                half: v.filter(sample => sample.frame % 1 === .5).length,
                first: v[0].frame, last: v.at(-1).frame,
                max_vertices_inside: vMax, max_triangle_pairs: tMax,
                minimum_signed_m: deepest.min_signed_m, deepest_frame: deepest.frame,
                pass: vMax === 0 && tMax === 0 && deepest.min_signed_m >= .0005,
            };
        }
    }
    const neutral = [...rest.vertex,...rest.triangle];
    const restVertex = Math.max(...rest.vertex.map(sample => sample.count));
    const restTriangle = Math.max(...rest.triangle.map(sample => sample.count));
    const restMin = Math.min(...neutral.map(sample => sample.min_signed_m));
    const results = {rest:{samples:1,integer:1,half:0,first:1,last:1,max_vertices_inside:restVertex,
        max_triangle_pairs:restTriangle,minimum_signed_m:restMin,deepest_frame:1,
        pass:restVertex===0 && restTriangle===0 && restMin>=.0005},...clips};
    assert.equal(Object.keys(clips).length, 14);
    for(const [clip,row] of Object.entries(results)) {
        for(const metric of ['vertex','triangle']) {
            const count = metric === 'vertex' ? row.max_vertices_inside : row.max_triangle_pairs;
            text[metric].push(`RESULT ${clip} ${count} ${row.minimum_signed_m.toFixed(9)} ${row.deepest_frame}`);
        }
    }
    const pass = Object.values(results).every(row => row.pass);
    save('motion_check.json',{garment_sha256:digest,criterion_m:.0005,pass,sources,clips:results});
    save('motion_check.txt','RESULT clip max_vertices_inside min_signed_m deepest_frame\n'+text.vertex.join('\n')+'\n');
    save('motion_check_tri.txt','RESULT clip max_triangle_pairs min_signed_m deepest_frame\n'+text.triangle.join('\n')+'\n');
    console.table(results);
    return pass;
}

async function main() {
    const stages = process.argv.slice(2);
    let pass = true;
    if (stages.includes('export')) pass = await exportCheck() && pass;
    if (stages.includes('motion')) pass = checkMotion() && pass;
    process.exitCode = pass ? 0 : 1;
}

main().catch(error => { console.error(error); process.exitCode = 1; });
