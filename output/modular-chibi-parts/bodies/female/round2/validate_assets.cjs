const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");

const names = ["tshirt", "dress", "jeans"];
const source = path.resolve(__dirname, "..", "validate.cjs");
const validator = new Module(path.join(__dirname, "validate.cjs"), module);
validator.paths = module.paths;
const originalArgs = process.argv;
process.argv = [...originalArgs.slice(0, 2), ...names.map(name => `female-${name}-v2.glb`)];
validator._compile(fs.readFileSync(source, "utf8"), validator.id);

function parse(file) {
  const bytes = fs.readFileSync(file);
  const length = bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.subarray(20, 20 + length));
  return { bytes, doc, data: bytes.subarray(28 + length) };
}

function payload(asset, index) {
  const { byteOffset = 0, byteLength } = asset.doc.bufferViews[index];
  return asset.data.subarray(byteOffset, byteOffset + byteLength);
}

function verifyAssets() {
  process.argv = originalArgs;
  const cards = {};
  const parent = path.resolve(__dirname, "..");
  for (const name of names) {
    const stem = `female-${name}-v2`;
    const asset = parse(path.join(__dirname, stem + ".glb"));
    const prior = parse(path.join(parent, `female-${name}.glb`));
    const report = JSON.parse(fs.readFileSync(path.join(__dirname, stem + ".validator.json")));
    assert.equal(report.sha256, createHash("sha256").update(asset.bytes).digest("hex"));
    assert.equal(report.issues.numWarnings + report.issues.numErrors, 0);
    assert.equal(report.info.hasSkins, true);
    assert(report.info.maxInfluences <= 4);
    for (const key of ["nodes", "skins", "materials", "textures", "samplers", "images"]) {
      assert.deepEqual(asset.doc[key], prior.doc[key]);
    }
    const ibm = asset.doc.skins[0].inverseBindMatrices;
    assert(payload(asset, asset.doc.accessors[ibm].bufferView).equals(payload(prior, prior.doc.accessors[ibm].bufferView)));
    const textures = report.info.resources.filter(entry => entry.image).map(entry => [entry.image.width, entry.image.height]);
    assert(textures.every(size => Math.max(...size) <= 1024));
    for (const { bufferView } of asset.doc.images) assert(payload(asset, bufferView).equals(payload(prior, bufferView)));
    assert(asset.bytes.length <= 1.5 * 2 ** 20);
    assert(report.info.totalTriangleCount <= 6000);
    cards[name] = { bytes: asset.bytes.length, triangles: report.info.totalTriangleCount, textures,
      roundOneBindAndEmbeddedTexturesEqual: true, sha256: report.sha256 };
  }
  fs.writeFileSync(path.join(__dirname, "assets.json"), JSON.stringify(cards, null, 2) + "\n");
}

process.on("beforeExit", verifyAssets);
