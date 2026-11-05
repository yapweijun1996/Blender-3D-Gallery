import fs from "node:fs";
import path from "node:path";
import { LoaderUtils } from "three";

const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
export function textField(value, label) {
  if (typeof value !== "string" || !value.trim()) throw new Error(`Invalid ${label}`);
  return value.trim().replace(/\s+/g, " ");
}
function uniqueSlug(value, seen, label) {
  if (typeof value !== "string" || !slugPattern.test(value) || seen.has(value))
    throw new Error(`Invalid or duplicate ${label}: ${value}`);
  seen.add(value);
  return value;
}
export function tagsField(value, label = "tags") {
  if (value === undefined) return [];
  if (!Array.isArray(value)) throw new Error(`Invalid ${label}`);
  return [...new Set(value.map((tag) => textField(tag, label)))];
}
function assetPath(value, label, extensions) {
  if (typeof value !== "string" || !value.startsWith("models/") ||
      /[\\?#%\x00-\x1f]/.test(value) || value.split("/").some((part) => !part || part === "." || part === "..") ||
      !extensions.includes(path.extname(value).toLowerCase())) throw new Error(`Unsafe ${label}`);
  return value;
}

// Validate the static registry before reading files or handing content to the browser.
export function validateCatalog(input) {
  if (!isObject(input) || !Array.isArray(input.collections) || !input.collections.length)
    throw new Error("Invalid catalog collections");
  const catalog = structuredClone(input);
  const collectionIds = new Set(), collectionSlugs = new Set(), assetIds = new Set(), assetSlugs = new Set();
  for (const collection of catalog.collections) {
    if (!isObject(collection)) throw new Error("Invalid collection");
    uniqueSlug(collection.id, collectionIds, "collection id");
    collection.slug = uniqueSlug(collection.slug === undefined ? collection.id : collection.slug, collectionSlugs, "collection slug");
    collection.name = textField(collection.name, "collection name");
    collection.description = collection.description === undefined ? "" : textField(collection.description, "collection description");
    if (!Array.isArray(collection.assets) || !collection.assets.length) throw new Error(`Invalid assets for ${collection.id}`);
    for (const asset of collection.assets) {
      if (!isObject(asset)) throw new Error("Invalid asset");
      uniqueSlug(asset.id, assetIds, "asset id");
      asset.slug = uniqueSlug(asset.slug === undefined ? asset.id : asset.slug, assetSlugs, "asset slug");
      asset.name = textField(asset.name, "asset name");
      asset.category = textField(asset.category, "asset category");
      asset.tags = tagsField(asset.tags);
      asset.collectionId = collection.id;
      asset.collectionName = collection.name;
      asset.description = asset.description === undefined
        ? `${asset.name}, a Blender-created asset in ${collection.name}.`
        : textField(asset.description, "asset description");
      asset.file = assetPath(asset.file, `file for ${asset.id}`, [".glb"]);
      asset.thumbnail = assetPath(asset.thumbnail, `thumbnail for ${asset.id}`, [".webp", ".png", ".jpg", ".jpeg"]);
      if (asset.metadata !== undefined) asset.metadata = assetPath(asset.metadata, `metadata for ${asset.id}`, [".json"]);
      if (asset.root !== undefined && asset.root !== null) textField(asset.root, "asset root");
      if (asset.downloadable !== undefined && typeof asset.downloadable !== "boolean") throw new Error("Invalid downloadable flag");
      asset.downloadable ??= true;
      if (asset.license !== undefined) asset.license = textField(asset.license, "asset license");
      asset.format = "GLB";
    }
  }
  // IDs are legacy URL aliases, so a different model cannot claim one as its slug.
  for (const collection of catalog.collections) for (const asset of collection.assets) {
    if (asset.slug !== asset.id && assetIds.has(asset.slug)) throw new Error(`Ambiguous asset slug: ${asset.slug}`);
  }
  return catalog;
}
export function validateMetadata(input, expectedId) {
  if (!isObject(input) || input.id !== expectedId) throw new Error("Mismatched model metadata");
  if (!isObject(input.display) || !Number.isFinite(input.display.previewRotationY)) throw new Error("Invalid metadata display");
  textField(input.accuracy_notes, "metadata accuracy notes");
  if (!Array.isArray(input.attribution)) throw new Error("Invalid metadata attribution");
  for (const credit of input.attribution) {
    if (!isObject(credit)) throw new Error("Invalid metadata attribution");
    textField(credit.credit, "metadata credit");
  }
  if (input.rights !== undefined) textField(input.rights, "metadata rights");
  const facts = input.scientific_properties;
  if (facts !== undefined && facts !== null) {
    if (!isObject(facts) || !Number.isFinite(facts.diameter_km) || !Number.isFinite(facts.axial_tilt_degrees))
      throw new Error("Invalid metadata scientific properties");
    for (const field of ["orbital_period_days", "rotation_period_hours", "semi_major_axis_million_km"])
      if (facts[field] !== undefined && facts[field] !== null && !Number.isFinite(facts[field])) throw new Error(`Invalid metadata ${field}`);
  }
  return input;
}
function containedFile(root, relative) {
  const file = path.join(root, relative);
  const modelsRoot = fs.realpathSync(path.join(root, "models"));
  const realFile = fs.realpathSync(file);
  if (!realFile.startsWith(modelsRoot + path.sep) || !fs.statSync(realFile).isFile())
    throw new Error(`Missing or unsafe asset: ${relative}`);
  return realFile;
}
export function loadCatalog(root = process.cwd()) {
  const catalog = validateCatalog(JSON.parse(fs.readFileSync(path.join(root, "models/catalog.json"), "utf8")));
  for (const collection of catalog.collections) {
    for (const asset of collection.assets) {
      if (asset.metadata) {
        asset.details = JSON.parse(fs.readFileSync(containedFile(root, asset.metadata), "utf8"));
        validateMetadata(asset.details, asset.solarId);
      }
      containedFile(root, asset.thumbnail);
      const buffer = fs.readFileSync(containedFile(root, asset.file));
      if (buffer.length < 20 || buffer.toString("ascii", 0, 4) !== "glTF" ||
          buffer.readUInt32LE(4) !== 2 || buffer.readUInt32LE(8) !== buffer.length ||
          buffer.toString("ascii", 16, 20) !== "JSON" || buffer.readUInt32LE(12) > buffer.length - 20)
        throw new Error(`Invalid GLB header: ${asset.file}`);
      const chunkSize = buffer.readUInt32LE(12);
      const data = JSON.parse(
        buffer.subarray(20, 20 + chunkSize).toString("utf8"),
      );
      for (const kind of ["images", "buffers"]) {
        const resources = data[kind];
        if (resources !== undefined && !Array.isArray(resources))
          throw new Error(`Invalid ${kind} list in ${asset.file}`);
        for (const resource of resources ?? []) {
          // A malformed data URI can otherwise be resolved as a relative URL.
          if (
            resource?.uri !== undefined &&
            (typeof resource.uri !== "string" ||
              !/^data:/i.test(resource.uri) ||
              /[\u0000-\u001f\u007f-\u009f\u2028\u2029]/.test(resource.uri) ||
              LoaderUtils.resolveURL(resource.uri, "/catalog-assets/") !== resource.uri)
          )
            throw new Error(`External ${kind} URI in ${asset.file}`);
        }
      }
      const nodes = data.scenes[data.scene ?? 0].nodes.map(
        (i) => data.nodes[i].name,
      );
      if (asset.root && (nodes.length !== 1 || nodes[0] !== asset.root))
        throw new Error(`Wrong root in ${asset.file}: ${nodes}`);
      const triangles = (data.nodes ?? []).reduce((sum, node) => {
        if (node.mesh === undefined) return sum;
        return sum + data.meshes[node.mesh].primitives.reduce((count, primitive) => {
          if ((primitive.mode ?? 4) !== 4) throw new Error(`Unsupported primitive mode in ${asset.file}`);
          const accessor = data.accessors[primitive.indices ?? primitive.attributes.POSITION];
          if (!accessor || accessor.count % 3) throw new Error(`Invalid triangle count in ${asset.file}`);
          return count + accessor.count / 3;
        }, 0);
      }, 0);
      if (!triangles) throw new Error(`No triangles in ${asset.file}`);
      const positions = new Set((data.meshes ?? []).flatMap((mesh) => mesh.primitives.map((primitive) => primitive.attributes.POSITION)));
      asset.bytes = buffer.length;
      asset.triangles = triangles;
      // Count stored geometry once; scene instances do not duplicate vertex storage.
      asset.vertices = [...positions].reduce((sum, index) => sum + data.accessors[index].count, 0);
      asset.materials = (data.materials ?? []).length;
      asset.animations = (data.animations ?? []).length;
      asset.license = asset.license ?? (typeof asset.details?.rights === "string" ? asset.details.rights : "Redistribution terms have not yet been specified.");
    }
  }
  return catalog;
}
