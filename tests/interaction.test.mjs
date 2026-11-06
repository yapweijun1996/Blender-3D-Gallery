import test from 'node:test';
import assert from 'node:assert/strict';
import { pullRatio, shotStrength, aimAngle, dragAngle, hitsCue, strikeOffset, PULL } from '../src/game/interaction.js';
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
test('aim points from the white ball toward the pointer and retains angle at zero-length', () => {
 assert.equal(aimAngle({x:0,z:0},{x:-1,z:0},1),Math.PI);
 assert.equal(aimAngle({x:0,z:0},{x:0,z:1},1),Math.PI/2);
 assert.equal(aimAngle({x:0,z:0},{x:0,z:0},1),1);
});
test('dragging the cue butt aims away from the pointer', () => {
 assert.equal(dragAngle({x:0,z:0},{x:-1,z:0},1),0);
 assert.equal(dragAngle({x:0,z:0},{x:0,z:-1},1),Math.PI/2);
 assert.equal(dragAngle({x:0,z:0},{x:0,z:0},1),1);
});
test('cue hit test covers the shaft behind the ball only', () => {
 const c={x:0,z:0}, r=.02857;
 assert.ok(hitsCue(c,0,{x:-.5,z:0},r));
 assert.ok(hitsCue(c,0,{x:-1.2,z:.03},r));
 assert.ok(!hitsCue(c,0,{x:.5,z:0},r));
 assert.ok(!hitsCue(c,0,{x:-.5,z:.2},r));
 assert.ok(!hitsCue(c,0,{x:-2,z:0},r));
});
import { postContact } from '../src/game/presentation.js';
test('post-contact estimate: head-on sends the object ball straight and leaves no cue tangent', () => {
 const balls=[{id:0,x:0,z:0},{id:3,x:1,z:0}];
 const r=postContact(balls,0,{kind:'ball',id:3,x:1-.0571,z:0});
 assert.ok(Math.abs(r.object.x-1)<1e-9 && Math.abs(r.object.z)<1e-9); assert.equal(r.cue,null);
 assert.equal(postContact(balls,0,{kind:'cushion'}),null);
});
test('post-contact estimate: cut shot splits object and cue directions at right angles', () => {
 const balls=[{id:0,x:0,z:0},{id:3,x:1,z:.03}];
 const r=postContact(balls,0,{kind:'ball',id:3,x:.95,z:0});
 assert.ok(Math.abs(r.object.x*r.cue.x+r.object.z*r.cue.z)<1e-9); assert.ok(r.cue.scale>0);
});
