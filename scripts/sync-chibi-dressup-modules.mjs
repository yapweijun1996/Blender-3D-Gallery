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
    id: "hair-ponytail", slot: "hair",
    label: { en: "High ponytail", "zh-Hans": "高马尾", ms: "Ekor kuda tinggi" },
    paths: ["studio-modules/hair-ponytail/round1/hair_ponytail_v1.glb"],
  },
  {
    id: "shoes-boots", slot: "shoes",
    label: { en: "Boots", "zh-Hans": "靴子", ms: "But" },
    paths: ["studio-modules/shoes-boots/round3/shoes_boots_v3.glb"],
  },
  {
    id: "bottom-skirt", slot: "bottom",
    label: { en: "Pleated skirt", "zh-Hans": "百褶裙", ms: "Skirt berlipat" },
    paths: ["studio-modules/skirt/round1/skirt_v1.glb"],
  },
  {
    id: "bottom-shorts", slot: "bottom",
    label: { en: "Shorts", "zh-Hans": "短裤", ms: "Seluar pendek" },
    paths: ["studio-modules/shorts/round1/shorts_v1.glb"],
  },
  {
    id: "shoes-hightop", slot: "shoes",
    label: { en: "High-tops", "zh-Hans": "高帮鞋", ms: "Kasut tinggi" },
    paths: ["studio-modules/shoes-hightop/round2/shoes_hightop_v2.glb"],
  },
  {
    id: "shoes-sandals", slot: "shoes",
    label: { en: "Sandals", "zh-Hans": "凉鞋", ms: "Sandal" },
    paths: ["studio-modules/shoes-sandals/round2/shoes_sandals_v2.glb"],
  },
  {
    id: "shoes-slipons", slot: "shoes",
    label: { en: "Slip-ons", "zh-Hans": "懒人鞋", ms: "Kasut tanpa tali" },
    paths: ["studio-modules/shoes-slipons/round2/shoes_slipons_v2.glb"],
  },
  {
    id: "hair-sidepart", slot: "hair",
    label: { en: "Side-part hair", "zh-Hans": "偏分发", ms: "Rambut belah tepi" },
    paths: ["studio-modules/hair-sidepart/round3/hair_sidepart_v3.glb"],
  },
  {
    id: "shoes-sneakers", slot: "shoes",
    label: { en: "Sneakers", "zh-Hans": "运动鞋", ms: "Kasut sukan" },
    paths: ["shoes-sol/round3/shoes_sneaker_v3.glb"],
  },
  {
    id: "top-tshirt", slot: "top",
    label: { en: "T-shirt", "zh-Hans": "T恤", ms: "Baju-T" },
    paths: ["studio-modules/tshirt/round5/tshirt_v5.glb"],
  },
  {
    id: "bottom-jeans", slot: "bottom",
    label: { en: "Jeans", "zh-Hans": "牛仔裤", ms: "Seluar jean" },
    paths: ["studio-modules/jeans/round5/jeans_v5.glb"],
  },
  {
    id: "top-dress", slot: "top", excludesSlots: ["bottom"],
    label: { en: "A-line dress", "zh-Hans": "连衣裙", ms: "Gaun A-line" },
    paths: ["studio-modules/dress/round5/dress_v5.glb"],
  },
  {
    id: "female-hair-bob", slot: "hair", family: "hair-bob", bodyIds: ["female"],
    label: { en: "Bob haircut", "zh-Hans": "波波头", ms: "Rambut bob" },
    paths: ["bodies/female/female-hair-bob.glb"],
  },
  {
    id: "female-hair-spiky", slot: "hair", family: "hair-spiky", bodyIds: ["female"],
    label: { en: "Spiky hair", "zh-Hans": "尖发", ms: "Rambut tercacak" },
    paths: ["bodies/female/female-hair-spiky.glb"],
  },
  {
    id: "female-hair-sidepart", slot: "hair", family: "hair-sidepart", bodyIds: ["female"],
    label: { en: "Side-part hair", "zh-Hans": "偏分发", ms: "Rambut belah tepi" },
    paths: ["bodies/female/female-hair-sidepart.glb"],
  },
  {
    id: "female-shoes-sneakers", slot: "shoes", family: "shoes-sneakers", bodyIds: ["female"],
    label: { en: "Sneakers", "zh-Hans": "运动鞋", ms: "Kasut sukan" },
    paths: ["bodies/female/female-sneakers.glb"],
  },
  {
    id: "female-top-tshirt", slot: "top", family: "top-tshirt", bodyIds: ["female"],
    label: { en: "T-shirt", "zh-Hans": "T恤", ms: "Baju-T" },
    paths: ["bodies/female/round2/female-tshirt-v2.glb"],
  },
  {
    id: "female-top-dress", slot: "top", family: "top-dress", bodyIds: ["female"], excludesSlots: ["bottom"],
    label: { en: "A-line dress", "zh-Hans": "连衣裙", ms: "Gaun A-line" },
    paths: ["bodies/female/round2/female-dress-v2.glb"],
  },
  {
    id: "female-bottom-jeans", slot: "bottom", family: "bottom-jeans", bodyIds: ["female"],
    label: { en: "Jeans", "zh-Hans": "牛仔裤", ms: "Seluar jean" },
    paths: ["bodies/female/round3/female-jeans-v3.glb"],
  },
  {
    id: "male-hair-bob", slot: "hair", family: "hair-bob", bodyIds: ["male"],
    label: { en: "Bob haircut", "zh-Hans": "波波头", ms: "Rambut bob" },
    paths: ["bodies/male/male-hair-bob.glb"],
  },
  {
    id: "male-hair-spiky", slot: "hair", family: "hair-spiky", bodyIds: ["male"],
    label: { en: "Spiky hair", "zh-Hans": "尖发", ms: "Rambut tercacak" },
    paths: ["bodies/male/male-hair-spiky.glb"],
  },
  {
    id: "male-hair-sidepart", slot: "hair", family: "hair-sidepart", bodyIds: ["male"],
    label: { en: "Side-part hair", "zh-Hans": "偏分发", ms: "Rambut belah tepi" },
    paths: ["bodies/male/male-hair-sidepart.glb"],
  },
  {
    id: "male-shoes-sneakers", slot: "shoes", family: "shoes-sneakers", bodyIds: ["male"],
    label: { en: "Sneakers", "zh-Hans": "运动鞋", ms: "Kasut sukan" },
    paths: ["bodies/male/male-sneakers.glb"],
  },
  {
    id: "male-top-tshirt", slot: "top", family: "top-tshirt", bodyIds: ["male"],
    label: { en: "T-shirt", "zh-Hans": "T恤", ms: "Baju-T" },
    paths: ["bodies/male/round2/male-tshirt-v2.glb"],
  },
  {
    id: "male-top-dress", slot: "top", family: "top-dress", bodyIds: ["male"], excludesSlots: ["bottom"],
    label: { en: "A-line dress", "zh-Hans": "连衣裙", ms: "Gaun A-line" },
    paths: ["bodies/male/round3/male-dress-v3.glb"],
  },
  {
    id: "male-bottom-jeans", slot: "bottom", family: "bottom-jeans", bodyIds: ["male"],
    label: { en: "Jeans", "zh-Hans": "牛仔裤", ms: "Seluar jean" },
    paths: ["bodies/male/round3/male-jeans-v3.glb"],
  },
  {
    id: "female-hair-ponytail", slot: "hair", family: "hair-ponytail", bodyIds: ["female"],
    label: { en: "High ponytail", "zh-Hans": "高马尾", ms: "Ekor kuda tinggi" },
    paths: ["bodies/female/wardrobe2/hair-ponytail.glb"],
  },
  {
    id: "male-shoes-sandals", slot: "shoes", family: "shoes-sandals", bodyIds: ["male"],
    label: { en: "Sandals", "zh-Hans": "凉鞋", ms: "Sandal" },
    paths: ["bodies/male/wardrobe2/shoes-sandals.glb"],
  },
  // Not shown yet: cargo pants and bomber jacket (failed review or the motion gate), hoodie.
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
for (const { id, slot, label, paths, optional, excludesSlots, family, bodyIds } of candidates) {
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
    // bodyIds and family are hand-authored manifest fields; keep them across syncs.
    module: { id, slot, ...(excludesSlots ? { excludesSlots } : {}), ...((bodyIds ?? previous?.bodyIds) ? { bodyIds: bodyIds ?? previous.bodyIds } : {}), ...((family ?? previous?.family) ? { family: family ?? previous.family } : {}), label, file, status, source: input.source, bytes: input.bytes.length, sha256 },
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
