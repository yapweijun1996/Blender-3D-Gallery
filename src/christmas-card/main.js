import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import modelUrl from '../../models/christmas-envelope/envelope.glb?url';
import { greeting } from './config.js';
import { frameEnvelope, poseLandingCamera, poseOpeningCamera, setCameraPose } from './framing.js';
import { createEntranceFlight, entranceBudgetMs, entranceDuration, frameDelta, poseEntrance, poseIdle, poseRecedingEnvelope } from './motion.js';
import { createAddress, createEntranceTrail, trailLifetime } from './accents.js';
import { createCardAudio } from './audio.js';
import { createLetterFlight, handoverDuration, revealFade, revealInterval, starApproachTime } from './letter.js';
import { createMouthLight, createStardust } from './magic.js';
import { applyPaperGrain } from './paper.js';
import { cardPixelRatio, softwareRendering } from './raster.js';
import { createBoundsRecorder } from './recording.js';
import { createSealEffect } from './seal.js';
import { warmWithinBudget } from './warmup.js';
import { startCardUpdates } from './updates.js';

const $ = id => document.getElementById(id);
const words = {
  en:{title:'A Christmas Greeting',subtitle:'A little wish, wrapped with love.',eyebrow:'✦  A LITTLE CHRISTMAS MAGIC  ✦',loading:'Loading your greeting…',open:'Tap to Open / 点击打开',replay:'Replay ↻',sound:'Sound on',muted:'Muted',fallback:'The 3D card could not be loaded. Here is your greeting:',lang:'Switch to Chinese'},
  zh:{title:'圣诞祝福',subtitle:'一份小小心意，满载温暖。',eyebrow:'✦  一点圣诞魔法  ✦',loading:'正在加载贺卡…',open:'点击打开 / Tap to Open',replay:'重新播放 ↻',sound:'声音开启',muted:'静音',fallback:'无法加载 3D 贺卡，请阅读这份祝福：',lang:'切换为英文'},
};
let lang='en', state='loading', mixer, action, envelope, letter, flap, seal;
let renderer, scene, camera, burstTime, sealBreakTime, burstDone=false;
let dust, mouthLight, sealEffect, letterFlight, revealed=0;
let drawAddress, updateTrail, warmPaper, contactShadow, failed=false;
let phaseTime=0, sequenceTime=0, entranceTime=0, openingIdleTime=0, flight, cameraViews, last=null;
let loadingWatchdog, entranceWatchdog, entranceWatchdogStarted=null, entranceTimeLeft=entranceBudgetMs;
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const audio=createCardAudio({visible:!document.hidden});
const updates=startCardUpdates({canReload:()=>state==='idle'||(state==='message'&&
  (failed||reduced||phaseTime>=($('lines').children.length+3)*revealInterval+revealFade))});
// Freeze an actual rendered frame so the browser test can inspect the shot.
let testCapture=null, testFrozen=false;
const testHook=new URLSearchParams(location.search).has('card-test') ? {
  snapshot:null, frames:null,
  captureAt(time, phase='opening', freeze=true){
    this.snapshot=null;
    testCapture={time,phase,freeze};
    if(freeze)this.release();
  },
  release(){testFrozen=false;last=null},
} : null;
if(testHook) window.__christmasCardTest=testHook;
const recordBounds=testHook&&createBoundsRecorder();
function emptyBounds(){return {left:Infinity,top:Infinity,right:-Infinity,bottom:-Infinity}}
function measureBurst(particles,box){
  if(!particles.length)return null;
  const bounds=emptyBounds();
  for(const {x,y,radius} of particles){
    bounds.left=Math.min(bounds.left,box.left+x-radius);bounds.right=Math.max(bounds.right,box.left+x+radius);
    bounds.top=Math.min(bounds.top,box.top+y-radius);bounds.bottom=Math.max(bounds.bottom,box.top+y+radius);
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
  $('open').textContent=w.open; $('replay').textContent=w.replay; $('mute').textContent=audio.muted?w.muted:w.sound;
  $('mute').setAttribute('aria-pressed',String(audio.muted));
  $('language').textContent=lang==='en'?'中文':'EN'; $('language').setAttribute('aria-label',w.lang);
  updates.localize(lang); $('recipient').textContent=g.recipient; $('sender').textContent=g.sender; $('fallback').textContent=w.fallback;
  const lines=$('lines');
  if(lines.dataset.language!==lang){
    lines.dataset.language=lang;
    lines.replaceChildren(...g.lines.map(line=>{
      const p=document.createElement('p');p.textContent=line;p.setAttribute('data-reveal','');return p;
    }));
  }
  if(!$('message').hidden)revealCopy(revealed);
}
$('language').addEventListener('click',()=>{lang=lang==='en'?'zh':'en';localize()});
function activateAudio() {
  if(audio.activate()&&!reduced&&(state==='entrance'||state==='idle'))audio.play('entrance');
}
$('mute').addEventListener('click',event=>{
  if(event.isTrusted){
    audio.setMuted(!audio.muted);
    if(!audio.muted)activateAudio();
    localize();
  }
});
document.addEventListener('click',event=>{
  if(event.isTrusted&&event.target!==$('mute'))activateAudio();
},true);
$('moon-flight').addEventListener('animationend',event=>{
  if(event.animationName==='moon-crossing')$('moon-flight').classList.remove('flying');
});
function revealCopy(count){
  revealed=count;
  $('message').querySelectorAll('[data-reveal]').forEach((item,i)=>item.toggleAttribute('data-pending',i>=count));
}
function positionMessage({left,top,right,bottom}){
  const message=$('message');
  message.classList.add('on-paper');
  message.style.left=`${left}px`;message.style.top=`${top}px`;
  message.style.width=`${right-left}px`;message.style.height=`${bottom-top}px`;
}
function showApproachStar(rect, time){
  const message=$('message');
  if(message.hidden){
    message.classList.add('arriving');
    revealCopy(1);
    message.hidden=false;
  }
  positionMessage(rect);
  const progress=THREE.MathUtils.smoothstep(time,handoverDuration-starApproachTime,handoverDuration);
  message.style.setProperty('--arrival-star-opacity',String(.67+.33*progress));
}
function clearMessageProjection(){
  const message=$('message');
  message.classList.remove('on-paper','arriving');
  for(const property of ['left','top','width','height','--arrival-star-opacity'])message.style.removeProperty(property);
}
function showMessage(immediate=false) {
  state='message';phaseTime=0;
  const message=$('message');
  message.classList.remove('arriving');
  message.style.removeProperty('--arrival-star-opacity');
  if(immediate){
    if(letter)letter.visible=false;
    clearMessageProjection();
  }
  localize();
  revealCopy(immediate?Infinity:1);
  message.hidden=false;
  if(!failed)audio.play('arrival');
}
function fail(){
  if(failed)return;
  failed=true;
  clearTimeout(loadingWatchdog);clearTimeout(entranceWatchdog);
  $('canvas').hidden=true; $('loading').hidden=true; $('open').hidden=true; $('fallback').hidden=false;
  showMessage(true);
}
function burst() {
  dust?.mouth(envelope.localToWorld(new THREE.Vector3(0,1.055,.26)));
}
let snowTexture;
function makeSnowTexture(){const n=32,data=new Uint8Array(n*n*4);for(let y=0;y<n;y++)for(let x=0;x<n;x++){const i=(y*n+x)*4,d=Math.hypot((x+.5-n/2)/(n/2),(y+.5-n/2)/(n/2));data[i]=data[i+1]=data[i+2]=255;data[i+3]=Math.round(220*Math.max(0,1-d)**2)}const texture=new THREE.DataTexture(data,n,n,THREE.RGBAFormat);texture.magFilter=THREE.LinearFilter;texture.minFilter=THREE.LinearFilter;texture.needsUpdate=true;return texture}
$('open').addEventListener('click',()=>{
  if(state!=='idle')return;
  openingIdleTime=phaseTime; phaseTime=0; sequenceTime=0; last=null; state='opening'; $('open').hidden=true; burstDone=false;
  if(reduced){showMessage(true);return}
  action.reset().setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
});
$('replay').addEventListener('click',()=>{
  $('message').hidden=true;clearMessageProjection();
  if(failed){showMessage(true);return}
  action.stop();letterFlight.reset();sealEffect?.reset();dust?.clear();mouthLight?.(envelope,0);
  burstDone=false;
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

async function warmScene(box, composition) {
  state='warming';
  envelope.visible=true;
  contactShadow.visible=true;
  contactShadow.position.set(0,-1.075,.19);
  const viewport=new THREE.Vector4(), scissor=new THREE.Vector4();
  const draw=pose=>()=>{
    if(failed)return;
    pose();
    renderer.getViewport(viewport);
    renderer.getScissor(scissor);
    const scissorTest=renderer.getScissorTest();
    const scale=Math.min(1,224/Math.max(viewport.z,viewport.w));
    const width=Math.max(1,Math.floor(viewport.z*scale)), height=Math.max(1,Math.floor(viewport.w*scale));
    const x=Math.floor(viewport.x+(viewport.z-width)/2), y=Math.floor(viewport.y+(viewport.w-height)/2);
    // Keep the normal framebuffer format and lights while submitting every visible material.
    const culled=[];
    scene.traverseVisible(object=>{
      if((object.isMesh||object.isPoints)&&object.frustumCulled){
        culled.push(object);
        object.frustumCulled=false;
      }
    });
    try {
      renderer.setViewport(x,y,width,height);
      renderer.setScissor(x,y,width,height);
      renderer.setScissorTest(true);
      renderer.render(scene,camera);
    } finally {
      renderer.setViewport(viewport);
      renderer.setScissor(scissor);
      renderer.setScissorTest(scissorTest);
      for(const object of culled)object.frustumCulled=true;
    }
  };
  const draws=[draw(()=>{
    setCameraPose(camera,cameraViews.entrance);
    flight=createEntranceFlight(envelope,camera,box.width);
    poseIdle(envelope,0);
    envelope.rotation.y=Math.PI-.16;
    updateTrail?.(1.66,{...flight,startX:0});
  })];
  if(!reduced)draws.push(
    draw(()=>{
      poseIdle(envelope,0);
      poseOpeningCamera(camera,cameraViews,sealBreakTime*.93,burstTime);
      sealEffect.update(sealBreakTime*.93);
    }),
    draw(()=>{
      poseOpeningCamera(camera,cameraViews,burstTime,burstTime);
      action.play();
      mixer.setTime(burstTime);
      sealEffect.update(sealBreakTime+.30);
      warmPaper(.85);
      mouthLight(envelope,.85);
      burst();
      dust.update(.23);
    }),
    draw(()=>{
      mixer.setTime(action.getClip().duration-.001);
      setCameraPose(camera,cameraViews.wide);
      letterFlight.begin();
      poseRecedingEnvelope(envelope,handoverDuration);
      letterFlight.pose(camera,box,composition,handoverDuration);
      warmPaper(0);
      mouthLight(envelope,0);
    }),
  );
  try {
    await warmWithinBudget(renderer,scene,camera,draws);
  } catch {
    // The model can still play if the optional GPU warm-up fails.
  } finally {
    action.stop();letterFlight.reset();sealEffect?.reset();dust?.clear();mouthLight?.(envelope,0);updateTrail?.(0,flight);
    warmPaper(0);poseIdle(envelope,0);setCameraPose(camera,cameraViews.entrance);
  }
  if(!failed)state='ready';
}

document.addEventListener('visibilitychange',()=>{
  audio.setVisible(!document.hidden);
  last=null;watchLoading();watchEntrance();
});
$('canvas').addEventListener('webglcontextlost',fail);
if ('ongesturestart' in window) document.addEventListener('gesturestart',event=>event.preventDefault(),{passive:false});
localize();
watchLoading();
try {
  renderer=new THREE.WebGLRenderer({canvas:$('canvas'),alpha:true,antialias:true});
  if(testHook)testHook.renderer=renderer;
  const software=softwareRendering(renderer);
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.NeutralToneMapping;renderer.toneMappingExposure=1;
  scene=new THREE.Scene();
  const pmrem=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment();const metalEnvironment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();
  camera=new THREE.PerspectiveCamera(50,1,.1,50);
  scene.add(new THREE.HemisphereLight(0xfff5dd,0x9ba797,.95));
  const light=new THREE.DirectionalLight(0xffe4b5,2.57);
  light.position.set(-3,4,6);scene.add(light);snowTexture=makeSnowTexture();
  contactShadow=new THREE.Mesh(new THREE.PlaneGeometry(3.55,1.52),new THREE.MeshBasicMaterial({
    map:snowTexture,color:0x020a06,transparent:true,depthWrite:false,toneMapped:false,
  }));
  contactShadow.rotation.x=-Math.PI/2;contactShadow.visible=false;scene.add(contactShadow);
  if(!reduced){
    dust=createStardust(scene);
    updateTrail=createEntranceTrail(dust.createEntranceBatch());
    mouthLight=createMouthLight(scene);
  }
  new GLTFLoader().load(modelUrl,gltf=>{
    if(failed)return;
    letter=gltf.scene.getObjectByName('Letter');flap=gltf.scene.getObjectByName('Flap');seal=gltf.scene.getObjectByName('Seal');
    const clip=gltf.animations.find(clip=>clip.name==='Open');
    burstTime=gltf.scene.getObjectByName('Envelope')?.userData.burstTime;
    sealBreakTime=gltf.scene.getObjectByName('Envelope')?.userData.sealBreakTime;
    if(!clip||!letter||!flap||!seal||!Number.isFinite(burstTime)||burstTime<=0||burstTime>=clip.duration||
      !Number.isFinite(sealBreakTime)||sealBreakTime<=0||sealBreakTime>=burstTime||
      letter.userData.paperBounds?.length!==4||seal.userData.crackRays?.length!==10){fail();return}
    envelope=gltf.scene;
    envelope.traverse(object=>{
      if(!object.isMesh)return;
      const materials=Array.isArray(object.material)?object.material:[object.material];
      for(const material of materials)if(material.metalness>.5){material.envMap=metalEnvironment;material.envMapIntensity=.55;material.needsUpdate=true}
    });
    drawAddress=createAddress(envelope);
    warmPaper=applyPaperGrain(envelope);
    envelope.visible=false;scene.add(envelope);
    letterFlight=createLetterFlight(letter,scene);
    if(!reduced)sealEffect=createSealEffect(seal,scene,sealBreakTime,dust);
    mixer=new THREE.AnimationMixer(envelope);
    action=mixer.clipAction(clip);
    state='preparing';localize();
  },undefined,fail);
  const canvas=$('canvas'), stage=canvas.parentElement;
  let viewportBox, stageBox, recordedViewport, layoutDirty=true;
  const invalidateLayout=()=>{layoutDirty=true};
  const layoutObserver=typeof ResizeObserver==='function'?new ResizeObserver(invalidateLayout):null;
  for (const target of [canvas,stage,document.querySelector('header'),document.querySelector('.card-actions')]) {
    layoutObserver?.observe(target);
  }
  window.addEventListener('resize',invalidateLayout,{passive:true});
  window.addEventListener('scroll',invalidateLayout,{passive:true});
  function frame(now) {
    if(failed)return;
    requestAnimationFrame(frame);
    if(document.hidden)return;
    let resized=false;
    if(layoutDirty||!viewportBox||!layoutObserver){
      const box=canvas.getBoundingClientRect(), composition=stage.getBoundingClientRect();
      if(!box.width||!box.height||!composition.width||!composition.height)return;
      layoutDirty=false;
      const ratio=cardPixelRatio(box.width,box.height,devicePixelRatio||1,software);
      if(ratio!==renderer.getPixelRatio())renderer.setPixelRatio(ratio);
      if(box.width!==viewportBox?.width||box.height!==viewportBox?.height)renderer.setSize(box.width,box.height,false);
      dust?.setPixels(canvas.height,box.height);
      resized=!sameBox(box,viewportBox)||!sameBox(composition,stageBox);
      if(resized){
        cameraViews=frameEnvelope(camera,box,composition);
        if(state==='entrance'||state==='warming'||state==='ready')flight=null;
        if((state==='handover'||state==='message')&&!reduced)setCameraPose(camera,cameraViews.wide);
        viewportBox=box;stageBox=composition;
        if(testHook)recordedViewport=box.toJSON();
      }
    }
    const box=viewportBox, composition=stageBox;
    if(state==='preparing'){void warmScene(box,composition);return}
    if(state==='loading'||state==='warming')return;
    if(testFrozen){renderer.render(scene,camera);return}
    const reveal=state==='ready';
    const dt=reveal?0:frameDelta(now,last);
    last=now;phaseTime+=dt;
    if(state==='opening'||state==='handover'||state==='message')sequenceTime+=dt;
    if(reveal){
      if(reduced)enterIdle();
      else {state='entrance';phaseTime=0}
    }
    if(state==='entrance'){
      entranceTime=phaseTime;
      if(!flight){
        setCameraPose(camera,cameraViews.entrance);
        flight=createEntranceFlight(envelope,camera,box.width);
      }
      poseEntrance(envelope,phaseTime,flight);
      poseLandingCamera(camera,cameraViews,envelope.position,phaseTime);
      if(phaseTime>=entranceDuration)finishEntrance('timeline');
    }else if(state==='idle'&&!reduced){
      poseIdle(envelope,phaseTime);
    }else if(state==='opening'){
      const settle=1-THREE.MathUtils.smoothstep(phaseTime,0,.42);
      poseIdle(envelope,openingIdleTime,settle);
      poseOpeningCamera(camera,cameraViews,phaseTime,burstTime);
      const previousTime=action.time, previousFlap=flap.rotation.x;
      mixer.update(dt);
      sealEffect.update(action.time);
      if(previousTime<sealBreakTime&&action.time>=sealBreakTime)audio.play('seal');
      if(previousFlap>-.20&&flap.rotation.x<=-.20)audio.play('flap');
      if(!burstDone&&action.time>=burstTime){burstDone=true;burst();audio.play('sparkle')}
      // Capture the lift endpoint after the mixer has applied its last pose.
      if(action.time>=action.getClip().duration){
        letterFlight.begin();
        state='handover';phaseTime=0;
      }
    }
    let projectedLetter;
    if(state==='handover'){
      poseRecedingEnvelope(envelope,phaseTime);
      projectedLetter=letterFlight.pose(camera,box,composition,phaseTime);
      if(phaseTime>=handoverDuration){
        positionMessage(projectedLetter);
        showMessage();
      }else if(phaseTime>=handoverDuration-starApproachTime)showApproachStar(projectedLetter,phaseTime);
    }else if(state==='message'&&!reduced){
      if(resized)positionMessage(letterFlight.pose(camera,box,composition,handoverDuration));
      const count=1+Math.floor(phaseTime/revealInterval);
      if(revealed!==count&&revealed<$('lines').children.length+4)revealCopy(count);
    }
    if(updateTrail&&entranceTime<entranceDuration+trailLifetime){
      if(state!=='entrance')entranceTime+=dt;
      updateTrail(entranceTime,flight);
    }
    const halo=state==='opening'
      ? THREE.MathUtils.smoothstep(-flap.rotation.x,.24,1.75)
      : state==='handover'?1-THREE.MathUtils.smoothstep(phaseTime,0,.78):0;
    warmPaper(halo);
    mouthLight?.(envelope,halo);
    contactShadow.position.set(envelope.position.x,-1.075+Math.min(0,envelope.position.y),envelope.position.z+.19);
    contactShadow.material.opacity=THREE.MathUtils.clamp(.82-envelope.position.y*.6,0,.82);
    dust?.update(dt);
    renderer.render(scene,camera);
    if(reveal){
      canvas.classList.remove('warming');$('loading').hidden=true;
      if(state==='entrance'){
        $('moon-flight').classList.add('flying');
        audio.play('entrance');
      }
      clearTimeout(loadingWatchdog);watchEntrance();
    }
    if(testHook){
      const time=state==='opening'?action.time:phaseTime;
      const capture=testCapture?.phase===state&&time>=testCapture.time;
      if(capture||testHook.frames){
        const particles=dust?.measure(camera,box)||[];
        const shot={
          phase:state,time,sequenceTime,timestamp:now,presentedAt:performance.now(),
          bounds:recordBounds(envelope,camera,box),canvas:recordedViewport,
          flap:flap.rotation.x,letter:letter.position.y,seal:sealEffect?.measure(),burst:burstDone,halo,
          cameraPosition:camera.position.toArray(),cameraPitch:camera.rotation.x,
          cameraRoll:camera.rotation.z,cameraFov:camera.fov,burstBounds:measureBurst(particles,box),particleCount:particles.length,
        };
        if(state==='opening'||state==='handover'||state==='message'){
          if(letter.visible){
            shot.letterRect=projectedLetter||letterFlight.project(camera,box);
            shot.letterBounds=recordBounds(letter,camera,box);
          }
        }
        if(state==='handover'&&!$('message').hidden){
          shot.starOpacity=Number(getComputedStyle($('message-star')).opacity);
        }
        if(state==='message'){
          shot.message=$('message').getBoundingClientRect().toJSON();
          shot.revealed=[...$('message').querySelectorAll('[data-reveal]:not([data-pending])')].map(element=>element.id||'line');
          const replay=$('replay');
          shot.replayOpaque=!replay.hasAttribute('data-pending')&&getComputedStyle(replay).opacity==='1';
          if(phaseTime===0){
            const star=getComputedStyle($('message-star'));
            shot.starOpaque=star.visibility==='visible'&&star.opacity==='1';
          }
        }
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
          testFrozen=testCapture.freeze;testCapture=null;
          testHook.snapshot={
            ...shot,burstTime,age:time-burstTime,
            camera:[...camera.matrixWorld.elements,...camera.projectionMatrix.elements],
            particles,
          };
        }
      }
    }
  }
  requestAnimationFrame(frame);
} catch { fail() }
