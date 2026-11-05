import test from 'node:test';
import assert from 'node:assert/strict';
import { aimContact, shotFeedback } from '../src/game/presentation.js';
import { TABLE, makeRack } from '../src/game/table.js';
const fixture = () => makeRack(42).map(b => ({ ...b, pocketed: b.id !== 0, x: b.id ? b.x : -0.7, z: 0 }));
test('break guide reaches the rack beyond the former artificial range', () => {
  const guide = aimContact(makeRack(42), 0);
  assert.equal(guide.kind, 'ball'); assert.ok(guide.distance > 0.65); assert.ok(Number.isInteger(guide.id));
});
test('guide picks nearest ball and clears a near miss to the actual cushion', () => {
  const balls = fixture();
  Object.assign(balls[1], { pocketed: false, x: 0, z: 0 });
  Object.assign(balls[2], { pocketed: false, x: 0.5, z: 0 });
  let guide = aimContact(balls, 0);
  assert.equal(guide.id, 1); assert.ok(Math.abs(guide.x + TABLE.radius*2) < 1e-9);
  balls[1].z = balls[2].z = TABLE.radius*2 + 0.001;
  guide = aimContact(balls, 0);
  assert.equal(guide.kind, 'cushion'); assert.ok(Math.abs(guide.x - (TABLE.halfLength - TABLE.radius)) < 1e-9);
});
test('guide distinguishes side pocket opening and handles touching cushion', () => {
  const balls = fixture(); balls[0].x = 0;
  let guide = aimContact(balls, Math.PI/2);
  assert.equal(guide.kind, 'pocket'); assert.ok(Math.abs(guide.z - (0.56-TABLE.pocketRadius)) < 1e-9);
  balls[0].x = TABLE.halfLength - TABLE.radius;
  guide = aimContact(balls, 0);
  assert.equal(guide.kind, 'cushion'); assert.ok(guide.distance < 1e-9);
});
test('feedback reports observed pots and authoritative turn/rule result', () => {
  assert.equal(shotFeedback({player:0}, {phase:'placing', player:1, message:'Cue ball scratched. Ball in hand.'}, {pockets:[{id:0},{id:3}]}), "Potted: 3. Player 2's turn. Cue ball scratched. Ball in hand.");
});
test('guide handles legal near-touching placements without claiming separating contact', () => {
  const balls=fixture();
  Object.assign(balls[1],{pocketed:false,x:-0.7+2*TABLE.radius-0.000005,z:0});
  assert.equal(aimContact(balls,0).id,1);
  assert.equal(aimContact(balls,0).distance,0);
  assert.notEqual(aimContact(balls,Math.PI).kind,'ball');
  balls[1].x=-0.7; balls[1].z=2*TABLE.radius;
  assert.notEqual(aimContact(balls,0).kind,'ball','tangent touch with no approaching motion is not first contact');
  balls[1].pocketed=true;
  balls[0].x=TABLE.halfLength-TABLE.radius;
  assert.equal(aimContact(balls,0).distance,0);
  assert.ok(aimContact(balls,Math.PI).distance>1,'moving away from touching cushion has a distant first contact');
});
