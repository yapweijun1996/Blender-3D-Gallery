import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";

const sources = new URL("../output/modular-chibi-parts/", import.meta.url);
const target = new URL("../models/chibi-dressup/", import.meta.url);
const manifestUrl = new URL("manifest.json", target);
const manifest = JSON.parse(await readFile(manifestUrl, "utf8"));

const candidates = [
  {
    id: "hair-bob", slot: "hair",
    label: { en: "Bob haircut", "zh-Hans": "波波头", ms: "Rambut bob" },
    paths: ["hair-fit-astra/round2/hair_bob_v2.glb", "hair-fit-astra/hair_bob_v1.glb"],
  },
  {
    id: "hair-spiky", slot: "hair",
    label: { en: "Spiky hair", "zh-Hans": "尖发", ms: "Rambut tercacak" },
    paths: ["studio-modules/hair-spiky/hair_spiky_v1.glb"],
  },
  {
    id: "shoes-sneakers", slot: "shoes",
    label: { en: "Sneakers", "zh-Hans": "运动鞋", ms: "Kasut sukan" },
    paths: ["shoes-sol/round3/shoes_sneaker_v3.glb"],
  },
  {
    id: "top-tshirt", slot: "top",
    label: { en: "T-shirt", "zh-Hans": "T恤", ms: "Baju-T" },
    paths: ["studio-modules/tshirt/round3/tshirt_v3.glb"],
  },
  {
    id: "bottom-jeans", slot: "bottom",
    label: { en: "Jeans", "zh-Hans": "牛仔裤", ms: "Seluar jean" },
    paths: ["studio-modules/jeans/round3/jeans_v3.glb"],
  },
  // Not shown yet: dress (needs a slot-exclusion rule), cargo pants and bomber jacket (failed review or the motion gate), hoodie.
];

async function findSource(paths) {
  for (const source of paths) {
    try {
      return { source, bytes: await readFile(new URL(source, sources)) };
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
  }
  return null;
}

// Resolve all required inputs before replacing any of the checked-in copies.
const copies = [];
for (const { id, slot, label, paths, optional } of candidates) {
  const previous = manifest.modules.find(module => module.id === id);
  const input = await findSource(paths);
  if (!input) {
    if (optional) continue;
    throw new Error(`Missing module ${id}: ${paths.join(", ")}`);
  }
  const file = `modules/${id}.glb`;
  const sha256 = createHash("sha256").update(input.bytes).digest("hex");
  const status = previous?.sha256 === sha256 ? previous.status : "pending";
  copies.push({
    module: { id, slot, label, file, status, source: input.source, bytes: input.bytes.length, sha256 },
    bytes: input.bytes,
  });
}
const synced = new Map(copies.map(copy => [copy.module.id, copy.module]));
manifest.modules = [
  ...candidates.map(({ id }) => synced.get(id) ?? manifest.modules.find(module => module.id === id)).filter(Boolean),
  ...manifest.modules.filter(module => !candidates.some(({ id }) => id === module.id)),
];
await mkdir(new URL("modules/", target), { recursive: true });
for (const { module, bytes } of copies) {
  await writeFile(new URL(module.file, target), bytes);
  console.log(`${module.id}: ${module.bytes} bytes from ${module.source}`);
}
await writeFile(manifestUrl, JSON.stringify(manifest, null, 2) + "\n");
