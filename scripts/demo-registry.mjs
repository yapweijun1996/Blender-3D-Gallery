import fs from "node:fs";
import path from "node:path";
import { loadCatalog, textField, tagsField } from "./catalog.mjs";

// Each launch route must have a corresponding explicit lazy loader in the application.
const routes = new Set(["?page=game", "?page=solar", "?page=product-studio"]);
export function validateDemos(input, catalog) {
  if (!Array.isArray(input) || !input.length) throw new Error("Invalid demos registry");
  const ids = new Set(), slugs = new Set(), launchRoutes = new Set();
  const assets = new Map(catalog.collections.flatMap((collection) => collection.assets).map((asset) => [asset.id, asset]));
  return input.map((value) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid demo");
    const demo = structuredClone(value);
    for (const [field, seen] of [["id", ids], ["slug", slugs]]) {
      if (typeof demo[field] !== "string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(demo[field]) || seen.has(demo[field]))
        throw new Error(`Invalid or duplicate demo ${field}`);
      seen.add(demo[field]);
    }
    for (const field of ["title", "category", "description"]) demo[field] = textField(demo[field], `demo ${field}`);
    demo.tags = tagsField(demo.tags);
    demo.technologies = tagsField(demo.technologies, "demo technologies");
    if (!["available", "unavailable"].includes(demo.status)) throw new Error("Invalid demo status");
    if (!routes.has(demo.route) || launchRoutes.has(demo.route)) throw new Error("Invalid or duplicate demo route");
    launchRoutes.add(demo.route);
    const asset = assets.get(demo.thumbnailAssetId);
    if (!asset) throw new Error("Invalid demo thumbnail asset");
    demo.thumbnail = asset.thumbnail;
    return demo;
  });
}
export function loadDemos(root = process.cwd(), catalog = loadCatalog(root)) {
  return validateDemos(JSON.parse(fs.readFileSync(path.join(root, "data/demos.json"), "utf8")), catalog);
}
