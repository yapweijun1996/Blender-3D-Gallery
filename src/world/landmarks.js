// Hand-modelled landmarks standing where the real ones are. Poses (x east, z south, yaw about Y, metres) come from
// scripts/world/fit-landmark.mjs (the mapped outlines) or from the mapped coordinates; the gallery models are in models/sg-*.
// `hide` names the OSM outlines drawn as plain extrusions that the landmark replaces (they stay solid for the physics).
export const LANDMARKS = [
  { id: "marina-bay-sands", models: ["sg-marina-bay-sands-towers", "sg-marina-bay-sands-podium"], pose: { x: 4.3, z: -0.7, yaw: 4.294 }, hide: /Marina Bay Sands Tower|SkyPark/i },
  { id: "esplanade", models: ["sg-esplanade-domes", "sg-esplanade-base"], pose: { x: -539.8, z: -702.4, yaw: 3.456 }, hide: /^Esplanade (Concert Hall|Theatre)/i },
  // Merlion Park (mapped 1.28685 N, 103.85446 E), the statue facing across the bay towards Marina Bay Sands.
  { id: "merlion", models: ["sg-merlion", "sg-merlion-park"], pose: { x: -694.5, z: -381.5, yaw: 1.066 } },
  // ArtScience Museum (1.28625 N, 103.86045 E).
  { id: "artscience", models: ["sg-artscience-museum"], pose: { x: -27.8, z: -315.1, yaw: 0 } },
  // Gardens by the Bay conservatories, fitted onto their mapped outlines.
  { id: "flower-dome", models: ["sg-flower-dome"], pose: { x: 454.8, z: -124.9, yaw: 0.105 }, hide: /^Flower Dome$/i },
  { id: "cloud-forest", models: ["sg-cloud-forest"], pose: { x: 591.7, z: -52, yaw: 2.618 }, hide: /^Cloud Forest$/i },
  // The Float @ Marina Bay is not mapped: placed (approximately) beside its bus stop on the waterfront, out over the bay.
  { id: "float", models: ["sg-the-float"], pose: { x: -170, z: -610, yaw: 0 } },
  // Helix Bridge: centre and direction from the mapped footway.
  { id: "helix", models: ["sg-helix-bridge"], pose: { x: -22.5, z: -453.8, yaw: -1.563 } },
];

export const hiddenOutline = name => LANDMARKS.some(landmark => landmark.hide?.test(name ?? ""));
