import test from 'node:test';
import assert from 'node:assert/strict';
import { pullRatio, shotStrength, aimAngle, strikeOffset, PULL } from '../src/game/interaction.js';
test('pull is relative to origin, clamps and reverses without charging', () => {
 assert.equal(pullRatio(50,50,100),0); assert.equal(pullRatio(50,49,100),0);
 assert.equal(pullRatio(50,100,100),.5); assert.equal(pullRatio(50,500,100),1); assert.equal(pullRatio(0,10,0),0);
});
test('strength curve preserves threshold and monotonic speed', () => {
 assert.equal(shotStrength(0),0); assert.equal(shotStrength(1),1);
 assert.ok(shotStrength(.8)>shotStrength(.3)); assert.equal(shotStrength(.5),.5**1.5);
});
test('cue retraction follows pull and reaches real contact on timeline', () => {
 assert.equal(strikeOffset(.8,0),.8*PULL.distance);
 assert.ok(strikeOffset(.8,.05)>0); assert.equal(strikeOffset(.8,PULL.strikeSeconds),0); assert.equal(strikeOffset(.8,1),0);
});
test('aim points from pointer through cue and retains angle at zero-length', () => {
 assert.equal(aimAngle({x:0,z:0},{x:-1,z:0},1),0);
 assert.equal(aimAngle({x:0,z:0},{x:0,z:-1},1),Math.PI/2);
 assert.equal(aimAngle({x:0,z:0},{x:0,z:0},1),1);
});
