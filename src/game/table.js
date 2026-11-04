// Measurements from the authored cushion contact faces, in glTF meters (Y up).
// Corner rail ends are shortened in the source asset to provide a ball-width mouth.
export const TABLE = Object.freeze({
  version: "billiards-2026-11-v1",
  radius: 0.028575,
  bedHeight: 0.7785,
  halfLength: 1.10495,
  halfWidth: 0.52096,
  headString: -0.552,
  footSpot: 0.552,
  pocketRadius: 0.047,
  railEnd: 1.025,
  sideGap: 0.085,
  endGap: 0.46,
  maxSpeed: 2.8,
  step: 1 / 120,
});
export const POCKETS = [-1.12, 0, 1.12].flatMap((x, i) =>
  [-0.56, 0.56].map((z, j) => ({ id: `p${i * 2 + j}`, x, z })),
);
export const RAILS = [-1, 1].flatMap((sign) => [
  {
    ax: -TABLE.railEnd,
    az: sign * TABLE.halfWidth,
    bx: -TABLE.sideGap,
    bz: sign * TABLE.halfWidth,
  },
  {
    ax: TABLE.sideGap,
    az: sign * TABLE.halfWidth,
    bx: TABLE.railEnd,
    bz: sign * TABLE.halfWidth,
  },
  {
    ax: sign * TABLE.halfLength,
    az: -TABLE.endGap,
    bx: sign * TABLE.halfLength,
    bz: TABLE.endGap,
  },
]);
// Pocket jaws continue behind each mouth, where the cabinet rim forms the pocket well.
for (const sx of [-1, 1])
  for (const sz of [-1, 1]) {
    RAILS.push({
      ax: sx * TABLE.railEnd,
      az: sz * TABLE.halfWidth,
      bx: sx * 1.1,
      bz: sz * 0.615,
    });
    RAILS.push({
      ax: sx * TABLE.halfLength,
      az: sz * TABLE.endGap,
      bx: sx * 1.19,
      bz: sz * 0.54,
    });
  }
for (const sz of [-1, 1])
  for (const sx of [-1, 1])
    RAILS.push({
      ax: sx * TABLE.sideGap,
      az: sz * TABLE.halfWidth,
      bx: sx * 0.055,
      bz: sz * 0.605,
    });
export function groupOf(id) {
  return id >= 1 && id <= 7 ? "solids" : id >= 9 && id <= 15 ? "stripes" : null;
}
export function legalPlacement(balls, x, z, behindHead = false, ignoreId = 0) {
  const r = TABLE.radius;
  return (
    Number.isFinite(x) &&
    Number.isFinite(z) &&
    Math.abs(x) <= TABLE.halfLength - r &&
    Math.abs(z) <= TABLE.halfWidth - r &&
    (!behindHead || x <= TABLE.headString) &&
    POCKETS.every(
      (p) => Math.hypot(x - p.x, z - p.z) > TABLE.pocketRadius + r,
    ) &&
    balls.every(
      (b) =>
        b.id === ignoreId ||
        b.pocketed ||
        Math.hypot(x - b.x, z - b.z) >= r * 2 - 0.00001,
    )
  );
}
export function makeRack(seed = 1) {
  let value = seed >>> 0;
  const random = () => {
    value = (Math.imul(value, 1664525) + 1013904223) >>> 0;
    return value / 4294967296;
  };
  const ids = [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15];
  for (let i = ids.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [ids[i], ids[j]] = [ids[j], ids[i]];
  }
  const solid = ids.splice(
      ids.findIndex((n) => n < 8),
      1,
    )[0],
    stripe = ids.splice(
      ids.findIndex((n) => n > 8),
      1,
    )[0];
  const balls = [{ id: 0, x: -0.7, z: 0, vx: 0, vz: 0, pocketed: false }];
  const spacing = TABLE.radius * 2 + 0.0003;
  for (let row = 0; row < 5; row++)
    for (let col = 0; col <= row; col++) {
      const id =
        row === 2 && col === 1
          ? 8
          : row === 4 && col === 0
            ? solid
            : row === 4 && col === 4
              ? stripe
              : ids.pop();
      balls.push({
        id,
        x: TABLE.footSpot + (row * spacing * Math.sqrt(3)) / 2,
        z: (col - row / 2) * spacing,
        vx: 0,
        vz: 0,
        pocketed: false,
      });
    }
  for (const b of balls) b.q = [0, 0, Math.SQRT1_2, Math.SQRT1_2];
  return balls.sort((a, b) => a.id - b.id);
}
