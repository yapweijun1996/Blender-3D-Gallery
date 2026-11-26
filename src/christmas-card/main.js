import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import modelUrl from '../../models/christmas-envelope/envelope.glb?url';
import { greeting } from './config.js';
import { frameEnvelope, poseOpeningCamera, setCameraPose } from './framing.js';
import { createEntranceFlight, entranceBudgetMs, entranceDuration, frameDelta, poseEntrance, poseIdle, poseRecedingEnvelope } from './motion.js';
import { createAddress, createEntranceTrail, trailLifetime } from './accents.js';
import { warmWithinBudget } from './warmup.js';

const $ = id => document.getElementById(id);
const words = {
  en:{title:'A Christmas Greeting',subtitle:'A little wish, wrapped with love.',eyebrow:'✦  A LITTLE CHRISTMAS MAGIC  ✦',loading:'Loading your greeting…',open:'Tap to Open / 点击打开',replay:'Replay ↻',sound:'Sound on',muted:'Muted',update:'Check for updates',install:'Update now',checking:'Checking…',current:'You have the latest version.',ready:'An update is ready.',error:'Unable to check for updates.',fallback:'The 3D card could not be loaded. Here is your greeting:',lang:'Switch to Chinese'},
  zh:{title:'圣诞祝福',subtitle:'一份小小心意，满载温暖。',eyebrow:'✦  一点圣诞魔法  ✦',loading:'正在加载贺卡…',open:'点击打开 / Tap to Open',replay:'重新播放 ↻',sound:'声音开启',muted:'静音',update:'检查更新',install:'立即更新',checking:'正在检查…',current:'已是最新版本。',ready:'新版本已准备好。',error:'无法检查更新。',fallback:'无法加载 3D 贺卡，请阅读这份祝福：',lang:'切换为英文'},
};
let lang='en', muted=false, state='loading', mixer, action, envelope, letter, flap, seal;
let renderer, scene, camera, registration, pendingUpdate=false, audio, revealTimers=[], burstTime, burstDone=false;
let burstPool=[], particles=[];
let drawAddress, updateTrail, glow, contactShadow, failed=false;
let phaseTime=0, entranceTime=0, openingIdleTime=0, flight, cameraViews, last=null;
let loadingWatchdog, entranceWatchdog, entranceWatchdogStarted=null, entranceTimeLeft=entranceBudgetMs;
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
// Freeze an actual rendered frame so the browser test can inspect the shot.
let testCapture=null, testFrozen=false;
const testHook=new URLSearchParams(location.search).has('card-test') ? {
  snapshot:null, frames:null,
  captureAt(time, phase='opening'){this.snapshot=null;testCapture={time,phase};this.release()},
  release(){testFrozen=false;last=null},
} : null;
if(testHook) window.__christmasCardTest=testHook;
function emptyBounds(){return {left:Infinity,top:Infinity,right:-Infinity,bottom:-Infinity}}
function expandProjectedBounds(point,box,bounds){
  point.project(camera);
  const x=box.left+(point.x+1)*box.width/2, y=box.top+(1-point.y)*box.height/2;
  bounds.left=Math.min(bounds.left,x);bounds.right=Math.max(bounds.right,x);
  bounds.top=Math.min(bounds.top,y);bounds.bottom=Math.max(bounds.bottom,y);
}
function measureEnvelope(box){
  const bounds=emptyBounds();
  const point=new THREE.Vector3();
  envelope.traverseVisible(object=>{
    if(!object.isMesh)return;
    const positions=object.geometry.attributes.position;
    for(let i=0;i<positions.count;i++){
      point.fromBufferAttribute(positions,i).applyMatrix4(object.matrixWorld);
      expandProjectedBounds(point,box,bounds);
    }
  });
  return bounds;
}
function measureBurst(box){
  if(!particles.length)return null;
  const bounds=emptyBounds(), point=new THREE.Vector3();
  for(const particle of particles){
    const {x,y,z}=particle.position;
    const radius=particle.userData.gold?.13:particle.scale.x/2;
    for(const dx of [-radius,radius])for(const dy of [-radius,radius])for(const dz of [-radius,radius]){
      expandProjectedBounds(point.set(x+dx,y+dy,z+dz),box,bounds);
    }
  }
  return bounds;
}
function sameBox(a,b){
  return b&&a.x===b.x&&a.y===b.y&&a.width===b.width&&a.height===b.height;
}
function localize() {
  const w=words[lang], g=greeting[lang];
  document.documentElement.lang=lang==='zh'?'zh-Hans':'en';
  $('title').textContent=w.title; $('subtitle').textContent=w.subtitle; document.querySelector('.eyebrow').textContent=w.eyebrow;
  $('loading-text').textContent=w.loading; drawAddress?.(g.recipient);
  $('open').textContent=w.open; $('replay').textContent=w.replay; $('mute').textContent=muted?w.muted:w.sound;
  $('language').textContent=lang==='en'?'中文':'EN'; $('language').setAttribute('aria-label',w.lang);
  $('update').textContent=pendingUpdate?w.install:w.update; $('recipient').textContent=g.recipient; $('sender').textContent=g.sender; $('fallback').textContent=w.fallback;
  const container=$('lines'), hidden=[...container.children].map(e=>e.hasAttribute('data-pending'));
  container.replaceChildren(...g.lines.map((line,i)=>{const p=document.createElement('p');p.textContent=line;if(hidden[i])p.setAttribute('data-pending','');return p;}));
}
$('language').addEventListener('click',()=>{lang=lang==='en'?'zh':'en';localize()});
$('mute').addEventListener('click',()=>{muted=!muted;$('mute').setAttribute('aria-pressed',String(muted));localize()});
function sound() {
  if(muted)return;
  try { audio ||= new AudioContext(); audio.resume(); for(const [i,f] of [523,659,784].entries()) { const o=audio.createOscillator(),g=audio.createGain(),t=audio.currentTime+i*.11; o.type='sine';o.frequency.value=f;g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(.08,t+.02);g.gain.exponentialRampToValueAtTime(.0001,t+.35);o.connect(g).connect(audio.destination);o.start(t);o.stop(t+.36) } } catch {}
}
function showMessage(immediate=false) {
  state='message'; phaseTime=0;
  // The HTML face replaces the risen paper at the start of its approach.
  if(letter) letter.visible=false;
  $('message').hidden=false; document.body.classList.add('opened'); localize();
  [...$('lines').children].forEach((p,i)=>{if(!immediate){p.setAttribute('data-pending','');revealTimers.push(setTimeout(()=>p.removeAttribute('data-pending'),650+i*450))}});
}
function fail(){
  if(failed)return;
  failed=true;
  clearTimeout(loadingWatchdog);clearTimeout(entranceWatchdog);
  $('canvas').hidden=true; $('loading').hidden=true; $('open').hidden=true; $('fallback').hidden=false;
  showMessage(true);
}
function clearParticles(){
  for(const particle of particles)particle.visible=false;
  particles=[];
}
function createBurstParticles() {
  const star=new THREE.Shape();
  for(let i=0;i<10;i++){const a=Math.PI/2+i*Math.PI/5,r=i%2?.055:.13,x=Math.cos(a)*r,y=Math.sin(a)*r;if(i===0)star.moveTo(x,y);else star.lineTo(x,y)}
  star.closePath();
  const geometry=new THREE.ShapeGeometry(star);
  return Array.from({length:38},(_,i)=>{
    const gold=i%3===0;
    const particle=gold
      ? new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({color:0xffdf83,side:THREE.DoubleSide,transparent:true,depthTest:false,depthWrite:false,toneMapped:false}))
      : new THREE.Sprite(new THREE.SpriteMaterial({map:snowTexture,color:0xffffff,transparent:true,depthTest:false,depthWrite:false,toneMapped:false}));
    particle.visible=false;particle.renderOrder=10;particle.userData.gold=gold;
    scene.add(particle);
    return particle;
  });
}
function burst() {
  if(reduced)return;
  const origin=envelope.localToWorld(new THREE.Vector3(0,1.05,.15));
  particles=burstPool;
  for(const particle of particles){
    const data=particle.userData;
    if(!data.gold)particle.scale.setScalar(.10+Math.random()*.12);
    particle.position.copy(origin);particle.material.opacity=1;particle.visible=true;
    data.vx=(Math.random()-.5)*2.1;data.vy=Math.random()*1.7+.7;data.vz=(Math.random()-.5)*.5;
    data.life=1.5+Math.random()*.5;
  }
}
let snowTexture;
function makeSnowTexture(){const n=32,data=new Uint8Array(n*n*4);for(let y=0;y<n;y++)for(let x=0;x<n;x++){const i=(y*n+x)*4,d=Math.hypot((x+.5-n/2)/(n/2),(y+.5-n/2)/(n/2));data[i]=data[i+1]=data[i+2]=255;data[i+3]=Math.round(220*Math.max(0,1-d)**2)}const texture=new THREE.DataTexture(data,n,n,THREE.RGBAFormat);texture.magFilter=THREE.LinearFilter;texture.minFilter=THREE.LinearFilter;texture.needsUpdate=true;return texture}
$('open').addEventListener('click',()=>{
  if(state!=='idle')return;
  sound(); openingIdleTime=phaseTime; phaseTime=0; last=null; state='opening'; $('open').hidden=true; burstDone=false;
  action.reset().setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
  if(reduced){action.paused=true;action.time=action.getClip().duration;mixer.update(0);showMessage(true)}
});
$('replay').addEventListener('click',()=>{
  revealTimers.forEach(clearTimeout);revealTimers=[];$('message').hidden=true;document.body.classList.remove('opened');
  if(failed){showMessage(true);return}
  clearParticles();letter.visible=true;action.reset().play();action.paused=true;mixer.update(0);
  poseIdle(envelope,0); enterIdle(); $('open').focus({preventScroll:true});
});
function enterIdle(){
  clearTimeout(entranceWatchdog);entranceWatchdogStarted=null;
  setCameraPose(camera,cameraViews.idle);
  state='idle'; phaseTime=0; last=null; $('open').disabled=false; $('open').hidden=false;
}

function watchLoading() {
  clearTimeout(loadingWatchdog);
  if(!document.hidden&&!$('loading').hidden)loadingWatchdog=setTimeout(fail,12000);
}

function watchEntrance() {
  clearTimeout(entranceWatchdog);
  if(entranceWatchdogStarted!==null){
    entranceTimeLeft-=performance.now()-entranceWatchdogStarted;
    entranceWatchdogStarted=null;
  }
  if(document.hidden||state!=='entrance')return;
  entranceWatchdogStarted=performance.now();
  entranceWatchdog=setTimeout(()=>{
    if(failed||state!=='entrance')return;
    poseIdle(envelope,0);
    entranceTime=entranceDuration+trailLifetime;
    updateTrail?.(entranceTime,flight);
    finishEntrance('watchdog');
  }, Math.max(0,entranceTimeLeft));
}

function finishEntrance(reason) {
  if(testHook)testHook.entranceCompletion={reason,time:phaseTime};
  enterIdle();
}

async function warmScene(box) {
  state='warming';
  envelope.visible=true;contactShadow.visible=true;
  try {
    // Without parallel compilation, even compileAsync can block on the driver.
    if(renderer.extensions.has('KHR_parallel_shader_compile')){
      glow.intensity=.44;
      flight=createEntranceFlight(envelope,camera,box.width);
      poseIdle(envelope,0);envelope.rotation.y=Math.PI-.16;
      contactShadow.position.set(0,-1.075,.19);
      updateTrail?.(1.66,{...flight,startX:0});
      burst();
      await warmWithinBudget(renderer,scene,camera,hasTime=>{
        if(failed)return;
        // Exercise the real framebuffer with a small fragment workload.
        const size=Math.min(160,box.width,box.height);
        renderer.setScissor((box.width-size)/2,(box.height-size)/2,size,size);
        renderer.setScissorTest(true);
        try {
          renderer.render(scene,camera);
          if(!failed&&hasTime()){
            poseIdle(envelope,0);
            if(!reduced){action.play();mixer.setTime(burstTime)}
            renderer.render(scene,camera);
          }
        } finally {
          renderer.setScissorTest(false);
        }
      });
    }
  } catch {
    // The model can still play if the optional GPU warm-up fails.
  } finally {
    action.stop();clearParticles();updateTrail?.(0,flight);
    glow.intensity=0;poseIdle(envelope,0);
  }
  if(!failed)state='ready';
}

document.addEventListener('visibilitychange',()=>{
  last=null;watchLoading();watchEntrance();
});
$('canvas').addEventListener('webglcontextlost',fail);
if ('ongesturestart' in window) document.addEventListener('gesturestart',event=>event.preventDefault(),{passive:false});
localize();
watchLoading();
try {
  renderer=new THREE.WebGLRenderer({canvas:$('canvas'),alpha:true,antialias:true});
  if(testHook)testHook.renderer=renderer;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.NeutralToneMapping;renderer.toneMappingExposure=1;
  scene=new THREE.Scene();
  const pmrem=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment();const metalEnvironment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();
  camera=new THREE.PerspectiveCamera(50,1,.1,50);
  scene.add(new THREE.HemisphereLight(0xfff5dd,0x9ba797,.85));
  const light=new THREE.DirectionalLight(0xffe4b5,2.65);
  light.position.set(-3,4,6);scene.add(light);snowTexture=makeSnowTexture();
  contactShadow=new THREE.Mesh(new THREE.PlaneGeometry(3.55,1.52),new THREE.MeshBasicMaterial({
    map:snowTexture,color:0x020a06,transparent:true,depthWrite:false,toneMapped:false,
  }));
  contactShadow.rotation.x=-Math.PI/2;contactShadow.visible=false;scene.add(contactShadow);
  if(!reduced){
    updateTrail=createEntranceTrail(scene,snowTexture);
    burstPool=createBurstParticles();
  }
  new GLTFLoader().load(modelUrl,gltf=>{
    if(failed)return;
    letter=gltf.scene.getObjectByName('Letter');flap=gltf.scene.getObjectByName('Flap');seal=gltf.scene.getObjectByName('Seal');
    const clip=gltf.animations.find(clip=>clip.name==='Open');
    burstTime=gltf.scene.getObjectByName('Envelope')?.userData.burstTime;
    if(!clip||!letter||!flap||!seal||!Number.isFinite(burstTime)||burstTime<=0||burstTime>=clip.duration){fail();return}
    envelope=gltf.scene;
    envelope.traverse(object=>{
      if(!object.isMesh)return;
      const materials=Array.isArray(object.material)?object.material:[object.material];
      for(const material of materials)if(material.metalness>.5){material.envMap=metalEnvironment;material.envMapIntensity=.55;material.needsUpdate=true}
    });
    drawAddress=createAddress(envelope);
    glow=new THREE.PointLight(0xffbd6d,0,1.8,2);
    glow.position.set(0,.81,.29);envelope.add(glow);
    envelope.visible=false;scene.add(envelope);
    mixer=new THREE.AnimationMixer(envelope);
    action=mixer.clipAction(clip);
    mixer.addEventListener('finished',()=>{if(state==='opening')showMessage()});
    state='preparing';localize();
  },undefined,fail);
  const canvas=$('canvas'), stage=canvas.parentElement;
  let viewportBox, stageBox;
  function frame(now) {
    if(failed)return;
    requestAnimationFrame(frame);
    if(document.hidden)return;
    const box=canvas.getBoundingClientRect(), composition=stage.getBoundingClientRect();
    if(!box.width||!box.height||!composition.width||!composition.height)return;
    if(!sameBox(box,viewportBox)||!sameBox(composition,stageBox)){
      if(box.width!==viewportBox?.width||box.height!==viewportBox?.height)renderer.setSize(box.width,box.height,false);
      cameraViews=frameEnvelope(camera,box,composition);
      if(state==='entrance'||state==='warming'||state==='ready')flight=null;
      if(state==='message'&&!reduced)setCameraPose(camera,cameraViews.wide);
      viewportBox=box;stageBox=composition;
    }
    if(state==='preparing'){void warmScene(box);return}
    if(state==='loading'||state==='warming')return;
    if(testFrozen){renderer.render(scene,camera);return}
    const reveal=state==='ready';
    const dt=reveal?0:frameDelta(now,last);
    last=now;phaseTime+=dt;
    if(reveal){
      if(reduced)enterIdle();
      else {state='entrance';phaseTime=0}
    }
    if(state==='entrance'){
      entranceTime=phaseTime;
      flight??=createEntranceFlight(envelope,camera,box.width);
      poseEntrance(envelope,phaseTime,flight);
      if(phaseTime>=entranceDuration)finishEntrance('timeline');
    }else if(state==='idle'&&!reduced){
      poseIdle(envelope,phaseTime);
    }else if(state==='opening'){
      const settle=1-THREE.MathUtils.smoothstep(phaseTime,0,.42);
      poseIdle(envelope,openingIdleTime,settle);
      poseOpeningCamera(camera,cameraViews,phaseTime,burstTime);
      mixer.update(dt);
      if(state==='opening'&&!burstDone&&action.time>=burstTime){burstDone=true;burst()}
    }else if(state==='message'&&!reduced){
      poseRecedingEnvelope(envelope,phaseTime);
    }
    if(updateTrail&&entranceTime<entranceDuration+trailLifetime){
      if(state!=='entrance')entranceTime+=dt;
      updateTrail(entranceTime,flight);
    }
    glow.intensity=.44*THREE.MathUtils.smoothstep(-flap.rotation.x,.32,1.85);
    contactShadow.position.set(envelope.position.x,-1.075+Math.min(0,envelope.position.y),envelope.position.z+.19);
    contactShadow.material.opacity=THREE.MathUtils.clamp(.82-envelope.position.y*.6,0,.82);
    for(const particle of particles){
      const data=particle.userData;
      particle.position.x+=data.vx*dt;particle.position.y+=data.vy*dt;particle.position.z+=data.vz*dt;
      data.vy-=1.2*dt;data.life-=dt;
      particle.material.opacity=Math.min(1,Math.max(0,data.life)*1.4);
      if(data.life<=0)particle.visible=false;
    }
    particles=particles.filter(particle=>particle.visible);
    renderer.render(scene,camera);
    if(reveal){
      canvas.classList.remove('warming');$('loading').hidden=true;
      clearTimeout(loadingWatchdog);watchEntrance();
    }
    if(testHook){
      const time=state==='opening'?action.time:phaseTime;
      const capture=testCapture?.phase===state&&time>=testCapture.time;
      if(capture||testHook.frames){
        const shot={
          phase:state,time,timestamp:now,presentedAt:performance.now(),bounds:measureEnvelope(box),canvas:box.toJSON(),
          flap:flap.rotation.x,letter:letter.position.y,seal:seal.scale.x,burst:burstDone,
          cameraPosition:camera.position.toArray(),cameraPitch:camera.rotation.x,
          cameraRoll:camera.rotation.z,cameraFov:camera.fov,burstBounds:measureBurst(box),
        };
        if(state==='entrance'){
          const point=envelope.position.clone().project(camera);
          shot.center=[box.left+(point.x+1)*box.width/2,box.top+(1-point.y)*box.height/2];
          shot.address=Math.cos(envelope.rotation.y)<-.85;
        }
        if(state==='opening'){
          const left=new THREE.Vector3(-1.58,1.044,-.073).project(camera);
          const right=new THREE.Vector3(1.58,1.044,-.073).project(camera);
          shot.mouthWidth=(right.x-left.x)*box.width/2;
        }
        testHook.frames?.push(shot);
        if(capture){
          testFrozen=true;testCapture=null;
          testHook.snapshot={
            ...shot,burstTime,age:time-burstTime,
            camera:[...camera.matrixWorld.elements,...camera.projectionMatrix.elements],
            particles:particles.map(p=>{const v=p.position.clone().project(camera);return {x:(v.x+1)*box.width/2,y:(1-v.y)*box.height/2,gold:p.userData.gold}}),
          };
        }
      }
    }
  }
  requestAnimationFrame(frame);
} catch { fail() }
if('serviceWorker' in navigator){navigator.serviceWorker.register('./sw.js',{scope:'./'}).then(r=>{registration=r;function ready(){pendingUpdate=!!r.waiting||!!(r.active&&r.installing);localize()}ready();r.addEventListener('updatefound',()=>r.installing?.addEventListener('statechange',ready));navigator.serviceWorker.addEventListener('controllerchange',()=>{if(pendingUpdate)location.reload()})}).catch(()=>{});}
$('update').addEventListener('click',async()=>{if(!registration){$('update-status').textContent=words[lang].error;return}if(registration.waiting||registration.installing){pendingUpdate=true;(registration.waiting||registration.installing).postMessage({type:'ACTIVATE'});return}$('update-status').textContent=words[lang].checking;try{await registration.update();pendingUpdate=!!registration.waiting||!!registration.installing;localize();$('update-status').textContent=pendingUpdate?words[lang].ready:words[lang].current}catch{$('update-status').textContent=words[lang].error}});
fetch('./version.json').then(r=>r.ok?r.json():Promise.reject()).then(info=>{$('version').textContent='v'+info.version}).catch(()=>{});
