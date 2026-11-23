import tile from "../models/world/tiles/-2_-4.json" with { type: "json" };
import { runWorldPassageBrowser } from "./world-passage-browser-utils.mjs";

await runWorldPassageBrowser({
  env: "MARINA_SQUARE_PASSAGE",
  tile,
  approach: ["173791997:0", "723073393:0"],
  covered: ["545362402:0", "545362402:1", "545362402:2", "545362403:0"],
  departure: ["635373148:0", "635373148:1"],
  neighbors: ["172373834:0", "736307183:0", "1424403063:0"],
  excludedServices: ["1314801325:0", "1314801304:0"],
  roof: { soffit: 4.5, top: 9.6, buildingId: 303311927 },
});
