import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrameGate } from '../src/solar/frame-gate.js';
function setup(){
 const calls=[],sync={},state={result:1,lost:false};
 const gl={TIMEOUT_EXPIRED:1,ALREADY_SIGNALED:2,CONDITION_SATISFIED:3,WAIT_FAILED:4,SYNC_GPU_COMMANDS_COMPLETE:5,
  fenceSync:(...args)=>{calls.push(['fence',...args]);return sync;},flush:()=>calls.push(['flush']),
  clientWaitSync:(...args)=>{calls.push(['wait',...args]);return state.result;},deleteSync:s=>calls.push(['delete',s]),isContextLost:()=>state.lost};
 return{gl,calls,state,sync,gate:createFrameGate(gl)};
}
test('pending frame prevents queue buildup; every wait is nonblocking',()=>{
 const h=setup();assert.equal(h.gate.ready(),true);h.gate.submitted();h.gate.submitted();assert.equal(h.calls.filter(c=>c[0]==='fence').length,1);
 for(let i=0;i<10;i++)assert.equal(h.gate.ready(),false);
 assert.ok(h.calls.filter(c=>c[0]==='wait').every(c=>c[2]===0&&c[3]===0));
 h.state.result=h.gl.CONDITION_SATISFIED;assert.equal(h.gate.ready(),true);assert.equal(h.calls.filter(c=>c[0]==='delete').length,1);
 h.gate.submitted();h.gate.dispose();h.gate.dispose();assert.equal(h.calls.filter(c=>c[0]==='delete').length,2);assert.equal(h.gate.ready(),false);
});
test('context loss releases pending fence once and stops until disposal',()=>{
 const h=setup();h.gate.submitted();h.state.lost=true;assert.equal(h.gate.ready(),false);h.gate.dispose();assert.equal(h.calls.filter(c=>c[0]==='delete').length,1);
});
test('missing APIs, null fence, wait failure and thrown calls gracefully fall back',()=>{
 const bare=createFrameGate({});assert.equal(bare.ready(),true);bare.submitted();bare.dispose();assert.equal(bare.ready(),false);
 for(const kind of ['null','wait','throw']){const h=setup();if(kind==='null')h.gl.fenceSync=()=>null;h.gate.submitted();if(kind==='wait')h.state.result=h.gl.WAIT_FAILED;if(kind==='throw')h.gl.clientWaitSync=()=>{throw new Error('lost');};assert.equal(h.gate.ready(),true);const n=h.calls.length;h.gate.submitted();assert.equal(h.calls.length,n);h.gate.dispose();}
});
