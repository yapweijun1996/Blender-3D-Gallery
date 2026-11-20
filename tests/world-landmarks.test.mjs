import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { LANDMARKS, hiddenOutline } from "../src/world/landmarks.js";

test("every landmark uses models that exist in the gallery catalog", () => {
  const catalog = JSON.parse(fs.readFileSync("models/catalog.json", "utf8"));
  const ids = new Set(catalog.collections.flatMap(collection => collection.assets.map(asset => asset.id)));
  for (const landmark of LANDMARKS) {
    for (const model of landmark.models) {
      assert.ok(ids.has(model), `${model} is in the catalog`);
      assert.ok(fs.existsSync(`models/${model}/${model}.glb`), `${model}.glb exists`);
    }
    assert.ok(Number.isFinite(landmark.pose.x) && Number.isFinite(landmark.pose.z) && Number.isFinite(landmark.pose.yaw));
  }
});

test("landmarks replace only their own outlines", () => {
  assert.equal(hiddenOutline("Marina Bay Sands Tower 2"), true);
  assert.equal(hiddenOutline("SkyPark"), true);
  assert.equal(hiddenOutline("Esplanade Concert Hall"), true);
  assert.equal(hiddenOutline("Esplanade Annexe"), false);
  assert.equal(hiddenOutline("Apple Marina Bay Sands"), false);
  assert.equal(hiddenOutline(undefined), false);
});
