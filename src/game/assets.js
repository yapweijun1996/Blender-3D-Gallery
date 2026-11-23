export const GAME_ASSET_IDS = Object.freeze([
  "pool-table",
  "cue-stick-01",
  "cue-ball",
  ...Array.from({ length: 15 }, (_, index) => `ball-${String(index + 1).padStart(2, "0")}`),
]);
