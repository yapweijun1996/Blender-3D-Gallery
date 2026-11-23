import tile from "../models/world/tiles/-1_-4.json" with { type: "json" };
import { runWorldPassageBrowser } from "./world-passage-browser-utils.mjs";

await runWorldPassageBrowser({
  env: "RAFFLES_PASSAGE",
  tile,
  approach: ["649944021:0"],
  covered: ["479745478:0", "479745478:1"],
  departure: ["479745479:0"],
  neighbors: ["479540200:2", "736307188:0", "479745479:1", "1085489730:0"],
  excludedServices: ["429052425:0"],
  roof: { soffit: 4.5, top: 6, buildingId: 393090492, raised: true },
});
