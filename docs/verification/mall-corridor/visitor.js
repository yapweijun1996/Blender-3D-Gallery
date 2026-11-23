import {AnimationMixer,Box3,Group,MathUtils,Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {BODY} from './collision.js';
const ASSET='/models/gjh-mall-visitor/exports/gjh-mall-visitor.glb';
export async function createVisitor({scene,world,camera,controls,canvas,onInspect,onMessage,spawn={x:0,z:3}}){
 const gltf=await new GLTFLoader().loadAsync(ASSET),avatar=gltf.scene,bounds=new Box3().setFromObject(avatar);
 if(Math.abs(bounds.min.y)>.01||Math.abs(bounds.max.y-1.72)>.02)throw Error('Visitor scale/floor contract mismatch');
 const visual=new Group();visual.name='ControlledVisitor';visual.add(avatar);visual.position.set(spawn.x,0,spawn.z);
 if(world.obstruction(visual.position))throw Error('Visitor spawn obstructed');
 const mixer=new AnimationMixer(avatar),actions={};
 for(const name of ['idle','walk']){const clip=gltf.animations.find(c=>c.name===name);if(!clip?.tracks.length)throw Error('Missing visitor '+name);actions[name]=mixer.clipAction(clip).setEffectiveWeight(name==='idle'?1:0).play()}
 const footMeshes=[];
 for(const name of ['LeftFoot','RightFoot']){const foot=avatar.getObjectByName(name);if(!foot)throw Error('Visitor foot missing');foot.traverse(o=>{if(o.isMesh)footMeshes.push(o)})}
 if(!footMeshes.length)throw Error('No editable foot meshes in visitor');
 scene.add(visual);
 let footMinY=0,groundCorrection=0;
 function ground(){
  avatar.position.y=0;visual.updateMatrixWorld(true);let min=Infinity;
  for(const o of footMeshes){const a=o.geometry.attributes.position,m=o.matrixWorld.elements;for(let i=0;i<a.count;i++)min=Math.min(min,m[1]*a.getX(i)+m[5]*a.getY(i)+m[9]*a.getZ(i)+m[13])}
  if(!Number.isFinite(min))throw Error('Invalid visitor foot height');
  groundCorrection=MathUtils.clamp(-min,-.08,.08);avatar.position.y=groundCorrection;visual.updateMatrixWorld(true);footMinY=min+groundCorrection;
 }
 const reduced=matchMedia('(prefers-reduced-motion: reduce)'),keys=new Set();let walking=false,state='idle',pointer=null,stick={x:0,z:0},lastBlocked=null;
 const pad=document.querySelector('#joystick'),thumb=pad.querySelector('span'),toggle=document.querySelector('#walk'),readout=document.querySelector('#walk-state');
 canvas.tabIndex=0;canvas.setAttribute('aria-label','3D corridor. In walking mode use W A S D or arrow keys. Escape returns to inspection.');
 function clearInput(){keys.clear();state='idle';for(const [name,action] of Object.entries(actions))action.setEffectiveWeight(name==='idle'?1:0);stick={x:0,z:0};const id=pointer;pointer=null;thumb.style.transform='';if(id!==null&&pad.hasPointerCapture(id))pad.releasePointerCapture(id)}
 function setWalking(value){walking=value;clearInput();controls.enabled=!value;toggle.textContent=value?'Stop walking':'Walk visitor';toggle.setAttribute('aria-pressed',String(value));pad.hidden=!value;document.querySelector('#walk-help').hidden=!value;if(value){camera.fov=50;camera.updateProjectionMatrix();canvas.focus({preventScroll:true})}else{onInspect();readout.textContent='Inspection mode'} }
 function reset(){clearInput();visual.position.set(spawn.x,0,spawn.z);visual.rotation.y=Math.PI;onMessage('Visitor returned to arrival');if(walking)canvas.focus({preventScroll:true})}
 function keydown(e){
  if(e.key==='Escape'&&walking){setWalking(false);toggle.focus();return}
  if(e.altKey||e.ctrlKey||e.metaKey){clearInput();return}
  if(e.repeat)return;
  if(!walking||document.hidden||(e.target!==canvas&&e.target!==document.body&&e.target!==pad))return;
  if(['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.code)){e.preventDefault();if(pointer!==null)clearInput();keys.add(e.code)}
 }
 addEventListener('keydown',keydown);addEventListener('keyup',e=>keys.delete(e.code));
 addEventListener('blur',clearInput);addEventListener('resize',clearInput);document.addEventListener('visibilitychange',()=>{if(document.hidden)clearInput()});
 document.addEventListener('focusin',e=>{if(e.target!==canvas&&e.target!==document.body&&e.target!==pad)clearInput()});
 function drag(e){if(e.pointerId!==pointer)return;const b=pad.getBoundingClientRect(),dx=e.clientX-b.left-b.width/2,dz=e.clientY-b.top-b.height/2,n=Math.hypot(dx,dz),strength=Math.min(1,Math.max(0,(n-6)/32));stick={x:n?dx/n*strength:0,z:n?dz/n*strength:0};thumb.style.transform=`translate(${stick.x*28}px,${stick.z*28}px)`}
 pad.addEventListener('pointerdown',e=>{if(!walking||pointer!==null||e.button!==0)return;e.preventDefault();clearInput();pointer=e.pointerId;pad.setPointerCapture(e.pointerId);canvas.focus({preventScroll:true});drag(e)});
 pad.addEventListener('pointermove',drag);for(const type of ['pointerup','pointercancel','lostpointercapture'])pad.addEventListener(type,e=>{if(e.pointerId===pointer)clearInput()});
 // Native arrow/button activation supplies an alternative to pointer dragging.
 pad.addEventListener('keydown',e=>{if(e.key.startsWith('Arrow')){canvas.focus();keydown(e)}});
 toggle.onclick=()=>setWalking(!walking);document.querySelector('#reset-visitor').onclick=reset;
 visual.rotation.y=Math.PI;
 function update(dt){
  // Capture release can become observable before the browser emits its loss event.
  if(pointer!==null&&!pad.hasPointerCapture(pointer))clearInput();
  dt=Math.min(Math.max(dt,0),.05);let dx=0,dz=0;
  if(walking&&!document.hidden){dx=stick.x+Number(keys.has('KeyD')||keys.has('ArrowRight'))-Number(keys.has('KeyA')||keys.has('ArrowLeft'));dz=stick.z+Number(keys.has('KeyS')||keys.has('ArrowDown'))-Number(keys.has('KeyW')||keys.has('ArrowUp'));const length=Math.hypot(dx,dz);if(length>1){dx/=length;dz/=length}}
  const before=visual.position.clone();lastBlocked=dx||dz?world.move(visual.position,dx*BODY.speed*dt,dz*BODY.speed*dt):null;visual.position.y=0;
  const moved=visual.position.clone().sub(before);state=moved.lengthSq()>1e-10?'walk':'idle';
  if(state==='walk'){const angle=Math.atan2(moved.x,moved.z);visual.rotation.y+=MathUtils.euclideanModulo(angle-visual.rotation.y+Math.PI,Math.PI*2)-Math.PI}
  for(const [name,action] of Object.entries(actions)){const target=name===state?1:0;action.setEffectiveWeight(reduced.matches?target:MathUtils.lerp(action.getEffectiveWeight(),target,1-Math.exp(-14*dt)));action.paused=reduced.matches}
  mixer.update(reduced.matches?0:dt);ground();
  if(walking){
   const target=visual.position.clone().add(new Vector3(0,1.05,0));const desired=visual.position.clone().add(new Vector3(0,2.35,3.2));camera.position.copy(world.cameraPosition(target,desired));camera.lookAt(target);avatar.visible=camera.position.distanceTo(target)>.6;
   const text=lastBlocked&&Math.hypot(dx,dz)>.01?'Path blocked — choose another direction':state==='walk'?'Walking':'Ready · W A S D / arrows / touch pad';if(readout.textContent!==text)readout.textContent=text;
  }else avatar.visible=true;
 }
 return {visual,clearInput,reset,setWalking,update,get state(){return {footMinY,groundCorrection,walking,animation:state,position:visual.position.toArray(),blocked:lastBlocked,keys:[...keys],pointer,weights:Object.fromEntries(Object.entries(actions).map(([k,a])=>[k,a.getEffectiveWeight()])),times:Object.fromEntries(Object.entries(actions).map(([k,a])=>[k,a.time])),reducedMotion:reduced.matches,asset:ASSET,body:BODY}}};
}
