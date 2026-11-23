import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { interactionKind } from "../src/model-interaction.js";

test("only the cart, both visitors, and the authored Singapore fish receive interactive badges", () => {
  const readModelData = file => JSON.parse(readFileSync(new URL(`../models/${file}`, import.meta.url), "utf8"));
  const { collections } = readModelData("catalog.json");
  const species = readModelData("singapore-fish/species.json");
  assert.ok(species.length > 0, "the authored fish registry is populated");

  const advertised = Object.fromEntries(collections.flatMap(({ id: collectionId, assets }) => assets
    .map(asset => [asset.id, interactionKind({ ...asset, collectionId })])
    .filter(([, kind]) => kind !== null)));
  assert.deepEqual(advertised, {
    "interactive-shopping-cart": "cart",
    "gjh-mall-visitor-v2": "visitor-v2",
    "gjh-visitor-v3": "visitor-v3",
    ...Object.fromEntries(species.map(([slug]) => [`fish-${slug}`, "fish"])),
  });
});
