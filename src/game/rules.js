import { groupOf, legalPlacement, TABLE } from "./table.js";
export const RULES_VERSION = "casual-8ball-v1";
export function adjudicate(before, balls, shot) {
  if (before.phase === "finished" || !shot.id || shot.id === before.lastShotId)
    throw new Error("Shot was already resolved");
  const next = structuredClone(before);
  next.balls = structuredClone(balls);
  next.revision++;
  next.break = false;
  next.ballInHand = false;
  next.phase = "aiming";
  next.lastShotId = shot.id;
  const shooter = before.player,
    opponent = 1 - shooter;
  const own = before.groups[shooter];
  // A rare open table with every group ball gone must still have a winning path.
  const eligible = own
    ? !before.balls.some((b) => !b.pocketed && groupOf(b.id) === own)
    : !before.balls.some((b) => !b.pocketed && groupOf(b.id));
  const scratch = shot.pockets.some((p) => p.id === 0),
    eight = shot.pockets.some((p) => p.id === 8);
  const wrong =
    shot.firstContact === null ||
    (!before.break &&
      (eligible
        ? shot.firstContact !== 8
        : own
          ? groupOf(shot.firstContact) !== own
          : shot.firstContact === 8));
  const foul = scratch || wrong;
  if (shot.invalid)
    return { ...before, phase: "recovery", message: shot.invalid };
  if (eight && !before.break) {
    next.winner = eligible && !foul ? shooter : opponent;
    next.phase = "finished";
    next.message =
      next.winner === shooter
        ? "Eight ball pocketed legally."
        : "Early eight or foul on the eight.";
    return next;
  }
  if (eight && before.break) {
    const b = next.balls.find((b) => b.id === 8);
    b.pocketed = true;
    let spot = null;
    for (
      let x = TABLE.footSpot;
      x >= -TABLE.halfLength + TABLE.radius;
      x -= TABLE.radius / 3
    )
      if (legalPlacement(next.balls, x, 0, false, 8)) {
        spot = { x, z: 0 };
        break;
      }
    if (!spot)
      return {
        ...before,
        phase: "recovery",
        message: "No safe spot for the eight. Restore or restart.",
      };
    Object.assign(b, spot, { pocketed: false, vx: 0, vz: 0 });
  }
  const objectPots = shot.pockets
    .filter((p) => groupOf(p.id))
    .toSorted(
      (a, b) =>
        (a.tick ?? 0) - (b.tick ?? 0) ||
        (a.sub ?? 0) - (b.sub ?? 0) ||
        (a.time ?? 1) - (b.time ?? 1) ||
        a.id - b.id,
    );
  if (!foul && !before.break && !own && objectPots.length) {
    const group = groupOf(objectPots[0].id);
    next.groups[shooter] = group;
    next.groups[opponent] = group === "solids" ? "stripes" : "solids";
  }
  const earnsTurn = before.break
    ? objectPots.length > 0
    : objectPots.some((p) => groupOf(p.id) === next.groups[shooter]);
  if (foul || !earnsTurn) next.player = opponent;
  if (foul) {
    const cue = next.balls.find((b) => b.id === 0);
    cue.pocketed = true;
    cue.vx = cue.vz = 0;
    next.ballInHand = true;
    next.phase = "placing";
  }
  next.message = foul
    ? scratch
      ? "Cue ball scratched. Ball in hand."
      : "Wrong first contact or no contact. Ball in hand."
    : before.break && eight
      ? "Eight re-spotted after the break."
      : earnsTurn
        ? "Legal pot — shoot again."
        : "Turn passes to the other player.";
  return next;
}
