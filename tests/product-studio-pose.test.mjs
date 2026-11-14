import test from "node:test";
import assert from "node:assert/strict";
import { Group, AnimationClip, VectorKeyframeTrack } from "three";
import { createPoseController } from "../src/product-studio/pose.js";
function fixture() {
 const scene=new Group();scene.name="ASSET_DemoFoodTin";
 const body=new Group();body.name="BODY_HollowShell";scene.add(body);
 const lid=new Group();lid.name="MOVABLE_Lid";lid.position.y=.11;scene.add(lid);
 const ring=new Group();ring.name="MOVABLE_PullRing";ring.position.y=.003;lid.add(ring);
 const track=(name,start,delta)=>new VectorKeyframeTrack(name+".position",[0,1.5,3],[0,start,0,0,start+delta,0,0,start,0]);
 return { scene,animations:[new AnimationClip("OpenClose",3,[track(lid.name,.11,.045)]),new AnimationClip("Exploded",3,[track(lid.name,.11,.07),track(ring.name,.003,.025)])],lid,ring };
}
test("Product Studio uses authored clips, exact rest and mutually exclusive modes",()=>{
 const f=fixture(),c=createPoseController(f);
 c.apply("open");assert.ok(Math.abs(f.lid.position.y-.155)<1e-7);assert.equal(f.ring.position.y,.003);
 c.apply("exploded");assert.ok(Math.abs(f.lid.position.y-.18)<1e-7);assert.ok(Math.abs(f.ring.position.y-.028)<1e-7);
 c.apply("open");assert.ok(Math.abs(f.lid.position.y-.155)<1e-7);assert.equal(f.ring.position.y,.003);
 c.apply("closed");assert.equal(f.lid.position.y,.11);assert.equal(f.ring.position.y,.003);
 c.dispose();c.dispose();assert.throws(()=>c.apply("open"),/disposed/);
});
test("Product Studio reverses any interrupted pose without accumulating transforms",()=>{
 const f=fixture(),c=createPoseController(f);
 for(let run=0;run<10;run++)for(const mode of ["open","exploded"]){
  for(let i=0;i<=60;i++)c.apply(mode,i/60);
  for(let i=60;i>=0;i--)c.apply(mode,i/60);
  c.apply("closed");assert.equal(f.lid.position.y,.11);assert.equal(f.ring.position.y,.003);
 }
 c.dispose();
});
test("Product Studio refuses missing or noncontract animation instead of faking motion",()=>{
 const f=fixture();f.animations[0].duration=2;assert.throws(()=>createPoseController(f),/Invalid packaging animation/);
 const g=fixture();g.scene.remove(g.lid);assert.throws(()=>createPoseController(g),/Missing packaging node/);
 const h=fixture(),c=createPoseController(h);assert.throws(()=>c.apply("unknown"));assert.throws(()=>c.apply("toString"));assert.throws(()=>c.apply("__proto__"));assert.throws(()=>c.apply("open",NaN));c.dispose();
});
