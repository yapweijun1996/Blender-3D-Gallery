import fs from "node:fs";
import path from "node:path";
import { LoaderUtils } from "three";

const root = process.cwd();
export function loadCatalog() {
  const catalog = JSON.parse(
    fs.readFileSync(path.join(root, "models/catalog.json"), "utf8"),
  );
  const seen = new Set();
  for (const collection of catalog.collections) {
    for (const asset of collection.assets) {
      if (!/^[a-z0-9-]+$/.test(asset.id) || seen.has(asset.id))
        throw new Error(`Invalid or duplicate asset id: ${asset.id}`);
      seen.add(asset.id);
      if (asset.metadata) {
        if (
          !asset.metadata.startsWith("models/") ||
          asset.metadata.includes("..")
        )
          throw new Error(`Unsafe metadata for ${asset.id}`);
        asset.details = JSON.parse(
          fs.readFileSync(path.join(root, asset.metadata), "utf8"),
        );
        if (asset.details.id !== asset.solarId)
          throw new Error(`Mismatched metadata for ${asset.id}`);
      }
      for (const field of ["file", "thumbnail"]) {
        if (!asset[field].startsWith("models/") || asset[field].includes(".."))
          throw new Error(`Unsafe ${field} for ${asset.id}`);
        if (!fs.statSync(path.join(root, asset[field])).isFile())
          throw new Error(`Missing ${field} for ${asset.id}`);
      }
      const buffer = fs.readFileSync(path.join(root, asset.file));
      if (
        buffer.toString("ascii", 0, 4) !== "glTF" ||
        buffer.readUInt32LE(4) !== 2 ||
        buffer.readUInt32LE(8) !== buffer.length
      )
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
        return (
          sum +
          data.meshes[node.mesh].primitives.reduce((count, primitive) => {
            if ((primitive.mode ?? 4) !== 4)
              throw new Error(`Unsupported primitive mode in ${asset.file}`);
            const accessor =
              data.accessors[
                primitive.indices ?? primitive.attributes.POSITION
              ];
            if (!accessor || accessor.count % 3)
              throw new Error(`Invalid triangle count in ${asset.file}`);
            return count + accessor.count / 3;
          }, 0)
        );
      }, 0);
      if (!triangles) throw new Error(`No triangles in ${asset.file}`);
      asset.bytes = buffer.length;
      asset.triangles = triangles;
    }
  }
  return catalog;
}
