import passage from "../models/world/tiles/-3_-4.json" with { type: "json" };
import east from "../models/world/tiles/-2_-4.json" with { type: "json" };
import northeast from "../models/world/tiles/-2_-5.json" with { type: "json" };
import { runWorldPassageBrowser } from "./world-passage-browser-utils.mjs";

await runWorldPassageBrowser({
  env: "RAFFLES_LINK_PASSAGE",
  tile: passage,
  continuationTiles: [east, northeast],
  approach: ["684524081:0"],
  covered: ["532351088:0"],
  departure: ["159938518:0", "684524082:0"],
  neighbors: ["710062599:1"],
  excludedServices: ["684523974:0"],
  roof: { soffit: 4.5, top: 9.6, buildingId: 620812487, raised: false },
  fixedDriveClock: true,
  approachLead: 6.5,
  requiredLaneCount: 1,
  requiredWidth: 3.4,
  runoff: 45,
  liveTraffic: { forbidden: ["684523974:0"], step: .1, continuation: "684524082:0" },
});
