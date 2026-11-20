// The heartland district: a ring road around a plaza with HDB blocks, a hawker centre, shops, a playground and a bus stop.
// x runs east, z runs south (as in the drive demo). A model's front (+Z) faces the way its yaw points.
export const RING = { halfX: 125, halfZ: 100, radius: 26 };
export const ROAD_HALF = 5.5;

/** The ring road centre line as points, counter-clockwise on the map when viewed from above. */
export function ringPoints(step = 4) {
  const { halfX: a, halfZ: b, radius: r } = RING;
  const points = [];
  const corner = (cx, cz, from, to) => {
    const count = Math.max(2, Math.ceil(r * Math.abs(to - from) / step));
    for (let i = 0; i <= count; i++) { const t = from + (to - from) * i / count; points.push([cx + r * Math.cos(t), cz + r * Math.sin(t)]); }
  };
  const line = (x0, z0, x1, z1) => {
    const count = Math.max(1, Math.ceil(Math.hypot(x1 - x0, z1 - z0) / step));
    for (let i = 1; i < count; i++) points.push([x0 + (x1 - x0) * i / count, z0 + (z1 - z0) * i / count]);
  };
  // Start on the north side heading east, then clockwise on the map (east, south, west, north).
  corner(a - r, -b + r, -Math.PI / 2, 0);
  line(a, -b + r, a, b - r);
  corner(a - r, b - r, 0, Math.PI / 2);
  line(a - r, b, -a + r, b);
  corner(-a + r, b - r, Math.PI / 2, Math.PI);
  line(-a, b - r, -a, -b + r);
  corner(-a + r, -b + r, Math.PI, Math.PI * 1.5);
  line(-a + r, -b, a - r, -b);
  points.push(points[0]);
  return points;
}

const down = Math.PI, east = Math.PI / 2, west = -Math.PI / 2;
/** Solid buildings block the player; open ones (shops, markets, stalls) can be walked into. */
export const BUILDINGS = [
  { model: "hdb_block", x: -52, z: -62, yaw: 0, sx: 2.6, sy: 1.1, sz: 2.0, solid: true },
  { model: "hdb_block", x: 52, z: -62, yaw: 0, sx: 2.6, sy: 1.1, sz: 2.0, solid: true },
  { model: "hdb_block", x: -52, z: 62, yaw: down, sx: 2.6, sy: 1.1, sz: 2.0, solid: true },
  { model: "hdb_block", x: 52, z: 62, yaw: down, sx: 2.6, sy: 1.1, sz: 2.0, solid: true },
  { model: "public_market", x: 0, z: 0, yaw: 0, sx: 1.4, sy: 1.3, sz: 1.4, solid: false },
  { model: "hdb_coffee_shop", x: -26, z: 47, yaw: down, sx: 1.7, sy: 1.5, sz: 1.7, solid: false },
  { model: "provision_shop", x: 26, z: 47, yaw: down, sx: 1.7, sy: 1.5, sz: 1.7, solid: false },
  { model: "hdb_void_deck", x: 0, z: -48, yaw: 0, sx: 2.2, sy: 1.2, sz: 2.2, solid: false },
  { model: "shoplot", x: -92, z: -8, yaw: east, sx: 1.6, sy: 1.0, sz: 1.6, solid: true },
  { model: "shoplot", x: 92, z: 8, yaw: west, sx: 1.6, sy: 1.0, sz: 1.6, solid: true },
  { model: "mrt_entrance", x: 70, z: -88, yaw: 0, sx: 1.8, sy: 1.5, sz: 1.8, solid: true },
];

/** Smaller things: stalls, playground, benches, shelters, signs. */
export const PROPS = [
  { model: "chicken_rice_stall", x: -14, z: 14, yaw: west, s: 1.4 },
  { model: "hawker_stall", x: 14, z: 14, yaw: east, s: 1.4 },
  { model: "hawker_stall", x: -14, z: -16, yaw: west, s: 1.4 },
  { model: "chicken_rice_stall", x: 14, z: -16, yaw: east, s: 1.4 },
  { model: "playground_slide", x: 78, z: 22, yaw: down, s: 1.8 },
  { model: "playground_slide", x: 86, z: 30, yaw: west, s: 1.8 },
  { model: "playground_swing", x: 70, z: 34, yaw: 0, s: 1.8 },
  { model: "playground_swing", x: 78, z: 40, yaw: east, s: 1.8 },
  { model: "bench", x: -8, z: 30, yaw: 0, s: 1.4 }, { model: "bench", x: 8, z: 30, yaw: 0, s: 1.4 },
  { model: "bench", x: -8, z: -32, yaw: down, s: 1.4 }, { model: "bench", x: 8, z: -32, yaw: down, s: 1.4 },
  { model: "bench", x: 62, z: 28, yaw: down, s: 1.4 }, { model: "bench", x: -62, z: 10, yaw: east, s: 1.4 },
  { model: "bus_shelter", x: -40, z: -91, yaw: 0, s: 1.6 }, { model: "bus_shelter", x: 40, z: 91, yaw: down, s: 1.6 },
  { model: "block_sign", x: -52, z: -50, yaw: 0, s: 2.2 }, { model: "block_sign", x: 52, z: -50, yaw: 0, s: 2.2 },
  { model: "block_sign", x: -52, z: 50, yaw: down, s: 2.2 }, { model: "block_sign", x: 52, z: 50, yaw: down, s: 2.2 },
  { model: "street_sign", x: 119, z: -94, yaw: down, s: 1.6 }, { model: "street_sign", x: -119, z: 94, yaw: 0, s: 1.6 },
];

/** Zebra crossings across the ring road (east and west sides) with a signal pole by each. */
export const CROSSINGS = [
  { x: 125, z: 0, across: "x" }, { x: -125, z: 0, across: "x" }, { x: 0, z: -100, across: "z" }, { x: 0, z: 100, across: "z" },
];

/** The slip road to the Causeway: drive the Saga through it and press E to head for Johor Bahru. */
export const GATE = { x: 60, z: -100, r: 8 };

/** Where the Proton Saga waits at the kerb (phase 4: get in and drive). */
export const CAR_SPOT = { x: -116.5, z: 40, yaw: 0 };
