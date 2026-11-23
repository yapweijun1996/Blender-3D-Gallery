import tile from "../models/world/tiles/-1_-6.json" with { type: "json" };
import { runWorldPassageBrowser } from "./world-passage-browser-utils.mjs";

const common = {
  env: "TEMASEK_PASSAGE",
  tile,
  requiredLaneCount: 2,
  requiredWidth: 6.8,
  neighbors: ["753843011:0"],
  excludedServices: [],
  roof: { soffit: 5, top: 20, buildingId: 393210509, raised: true },
};

await runWorldPassageBrowser({
  ...common,
  direction: "northeast",
  approach: ["21702431:4"],
  covered: ["395443687:0"],
  departure: ["750875319:0"],
  approachLead: 14,
  liveTraffic: { forbidden: ["753843011:0"] },
});

await runWorldPassageBrowser({
  ...common,
  direction: "southwest",
  approach: ["21701084:0"],
  covered: ["395443688:0"],
  departure: ["750875316:0"],
  approachLead: 7,
  liveTraffic: { forbidden: [] },
});
