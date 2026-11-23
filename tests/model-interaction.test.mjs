import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { interactionKind } from "../src/model-interaction.js";

test("only allowlisted models and the authored Singapore fish receive interactive badges", () => {
  const readModelData = file => JSON.parse(readFileSync(new URL(`../models/${file}`, import.meta.url), "utf8"));
  const { collections } = readModelData("catalog.json");
  const species = readModelData("singapore-fish/species.json");
  assert.ok(species.length > 0, "the authored fish registry is populated");

  const advertised = Object.fromEntries(collections.flatMap(({ id: collectionId, assets }) => assets
    .map(asset => [asset.id, interactionKind({ ...asset, collectionId })])
    .filter(([, kind]) => kind !== null)));
  assert.deepEqual(advertised, {
    "interactive-shopping-cart": "cart",
    "shophouse-parcel-drop-hatch": "parcel-hatch",
    ...(collections.some(({ assets }) => assets.some(({ id }) => id === "mall-ride-hail-pickup-bay"))
      ? { "mall-ride-hail-pickup-bay": "pickup-bay" } : {}),
    ...(collections.some(({ assets }) => assets.some(({ id }) => id === "loh-hei-yee-sang-platter"))
      ? { "loh-hei-yee-sang-platter": "loh-hei" } : {}),
    ...(collections.some(({ assets }) => assets.some(({ id }) => id === "malaysia-rail-reload-counter"))
      ? { "malaysia-rail-reload-counter": "rail-reload" } : {}),
    ...(collections.some(({ assets }) => assets.some(({ id }) => id === "mall-carpark-help-point"))
      ? { "mall-carpark-help-point": "carpark-help" } : {}),
    ...(collections.some(({ assets }) => assets.some(({ id }) => id === "ramadan-bazaar-air-balang-stall"))
      ? { "ramadan-bazaar-air-balang-stall": "air-balang" } : {}),
    ...(collections.some(({ assets }) => assets.some(({ id }) => id === "wet-market-coconut-scraper"))
      ? { "wet-market-coconut-scraper": "coconut-scraper" } : {}),
    "gjh-mall-visitor-v2": "visitor-v2",
    "gjh-visitor-v3": "visitor-v3",
    ...Object.fromEntries(species.map(([slug]) => [`fish-${slug}`, "fish"])),
  });
});
