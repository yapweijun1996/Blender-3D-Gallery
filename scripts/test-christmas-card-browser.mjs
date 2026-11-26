import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { chromium } from 'playwright';
import { launchOptions } from './browser-test-utils.mjs';
import { entranceBudgetMs, entranceDuration, loopStart, loopEnd, maxFrameDelta } from '../src/christmas-card/motion.js';
import { handoverDuration, starApproachTime } from '../src/christmas-card/letter.js';
import { mutePreference } from '../src/christmas-card/audio.js';
import { codePointCount, decodeGreeting, fragmentLimit } from '../src/christmas-card/greeting-link.js';
import { particleLimit } from '../src/christmas-card/magic.js';
const root = path.resolve('dist'), base = '/Blender-3D-Gallery/';
const types = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.webmanifest':'application/manifest+json','.svg':'image/svg+xml','.png':'image/png','.glb':'model/gltf-binary'};
const server = http.createServer(async (req,res) => {
  let pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  if (!pathname.startsWith(base)) {res.writeHead(404).end();return}
  if (pathname.endsWith('/')) pathname += 'index.html';
  const file=path.resolve(root,pathname.slice(base.length));
  if (!file.startsWith(root+path.sep)) {res.writeHead(403).end();return}
  try {const bytes=await fs.readFile(file);res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'}).end(bytes)} catch {res.writeHead(404).end()}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url=`http://127.0.0.1:${server.address().port}${base}christmas-card/?card-test=1`;
await fs.mkdir('output/christmas-card',{recursive:true});
const browser=await chromium.launch(launchOptions);
// Measure the rendered red paper, independently of the camera calculations.
async function envelopePixels(page) {
  const canvasBox=await page.locator('#canvas').boundingBox(), buttonBox=await page.locator('#open').boundingBox();
  const png = await page.locator('#canvas').screenshot();
  return page.evaluate(async ({base64,canvasBox,buttonBox}) => {
    const data=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));
    const bitmap=await createImageBitmap(new Blob([data],{type:'image/png'}));
    const canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;
    const ctx=canvas.getContext('2d');ctx.drawImage(bitmap,0,0);const pixels=ctx.getImageData(0,0,canvas.width,canvas.height).data;
    let minX=canvas.width,maxX=-1,minY=canvas.height,maxY=-1,count=0;const hist=[new Uint32Array(256),new Uint32Array(256),new Uint32Array(256)];
    for(let y=0;y<canvas.height;y++)for(let x=0;x<canvas.width;x++){const i=(y*canvas.width+x)*4,[r,g,b]=pixels.subarray(i,i+3);const inButton=buttonBox&&x>=buttonBox.x-canvasBox.x&&x<buttonBox.x-canvasBox.x+buttonBox.width&&y>=buttonBox.y-canvasBox.y&&y<buttonBox.y-canvasBox.y+buttonBox.height;if(!inButton&&r>75&&r>g*1.35&&r>b*1.18){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);hist[0][r]++;hist[1][g]++;hist[2][b]++;count++}}
    const median=hist.map(channel=>{let n=0;for(let i=0;i<256;i++){n+=channel[i];if(n>=count/2)return i}return 0});
    return {width:maxX-minX+1,height:maxY-minY+1,minX,minY,maxX,maxY,canvasWidth:canvas.width,canvasHeight:canvas.height,count,median};
  },{base64:png.toString('base64'),canvasBox,buttonBox});
}
async function assertHero(page,width,height,idle=false) {
  const p=await envelopePixels(page);
  if(width===390){
    const ratio=p.width/width;
    assert.ok(idle ? ratio>=.64&&ratio<=.78 : ratio>=.85,`Unexpected mobile ${idle?'rest':'close-up'} width: ${p.width}px`);
  }
  else assert.ok(p.height>=height*.45,`Desktop envelope height ${p.height}px is below 45% of ${height}px`);
  assert.ok(p.minX>0&&p.maxX<p.canvasWidth-1&&p.minY>0&&p.maxY<p.canvasHeight-1,`Envelope clipped: ${JSON.stringify(p)}`);
}
async function assertPaperPixels(page, samples) {
  const colors=await page.evaluate(async samples=>{
    const result=[];
    for(const {png,rect} of samples){
      const bytes=Uint8Array.from(atob(png),c=>c.charCodeAt(0));
      const bitmap=await createImageBitmap(new Blob([bytes],{type:'image/png'}));
      const canvas=document.createElement('canvas');
      canvas.width=bitmap.width;canvas.height=bitmap.height;
      const ctx=canvas.getContext('2d');ctx.drawImage(bitmap,0,0);bitmap.close();
      const x=Math.round(rect.left+(rect.right-rect.left)*.18);
      const y=Math.round(rect.top+(rect.bottom-rect.top)*.72);
      const data=ctx.getImageData(x-3,y-3,7,7).data;
      const average=[0,0,0];
      for(let i=0;i<data.length;i+=4)for(let j=0;j<3;j++)average[j]+=data[i+j]/49;
      result.push(average);
    }
    return result;
  },samples);
  const ivory=[246,238,220];
  assert.ok(colors.every(rgb=>rgb.every((channel,i)=>Math.abs(channel-ivory[i])<=12)),
    `Both frames show warm ivory paper: ${JSON.stringify(colors)}`);
  assert.ok(colors[0].every((channel,i)=>Math.abs(channel-colors[1][i])<8),
    `Paper color changed across the HTML reveal: ${JSON.stringify(colors)}`);
}
async function assertStarPixels(page, phase) {
  const png=await page.locator('#message-star').screenshot();
  const pixels=await page.evaluate(async base64=>{
    const bytes=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));
    const bitmap=await createImageBitmap(new Blob([bytes],{type:'image/png'}));
    const canvas=document.createElement('canvas');
    canvas.width=bitmap.width;canvas.height=bitmap.height;
    const ctx=canvas.getContext('2d');
    ctx.drawImage(bitmap,0,0);bitmap.close();
    const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;
    let count=0;
    for(let i=0;i<data.length;i+=4){
      if(data[i]>=110&&data[i]<=201&&data[i+1]<145&&data[i+2]<105&&data[i]>data[i+1]*1.20)count++;
    }
    return count;
  },png.toString('base64'));
  assert.ok(pixels>=20,`The star must be painted in the ${phase} frame, found ${pixels} gold pixels`);
}
async function assertBurstPixels(page, snapshot) {
  const png=await page.locator('#canvas').screenshot();
  const visible=await page.evaluate(async ({base64,particles})=>{
    const bytes=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));
    const bitmap=await createImageBitmap(new Blob([bytes],{type:'image/png'}));
    const canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;
    const ctx=canvas.getContext('2d');ctx.drawImage(bitmap,0,0);
    const pixels=ctx.getImageData(0,0,canvas.width,canvas.height).data;
    let gold=0,snow=0;
    for(const particle of particles){
      let match=false;
      for(let dy=-3;dy<=3&&!match;dy++)for(let dx=-3;dx<=3;dx++){
        const x=Math.round(particle.x)+dx,y=Math.round(particle.y)+dy;
        if(x<0||y<0||x>=canvas.width||y>=canvas.height)continue;
        const i=(y*canvas.width+x)*4,r=pixels[i],g=pixels[i+1],b=pixels[i+2];
        if(particle.gold ? r>=210&&g>=140&&g<=245&&b>=45&&b<=190&&r>g*1.04 : r>=200&&g>=200&&b>=200){match=true;break}
      }
      if(match){if(particle.gold)gold++;else snow++}
    }
    return {gold,snow};
  },{base64:png.toString('base64'),particles:snapshot.particles});
  assert.ok(visible.gold>=2&&visible.snow>=2,`Burst pixels not visible in front of the envelope: ${JSON.stringify(visible)}`);
}
async function assertMessageFits(page) {
  assert.ok(await page.locator('#message').evaluate(e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth&&e.scrollHeight<=e.clientHeight}));
}
async function assertSharedMessageFits(page) {
  await page.waitForFunction(()=>{
    const message=document.getElementById('message');
    const rect=message.getBoundingClientRect();
    const stage=document.querySelector('.scene').getBoundingClientRect();
    const header=document.querySelector('header').getBoundingClientRect();
    const actions=document.querySelector('.card-actions').getBoundingClientRect();
    return !message.hidden&&rect.left>=0&&rect.right<=innerWidth&&rect.top>=header.bottom&&
      rect.bottom<=actions.top&&Math.abs((rect.left+rect.right)-(stage.left+stage.right))<2&&
      message.scrollWidth<=message.clientWidth&&message.scrollHeight<=message.clientHeight;
  },undefined,{timeout:5000});
  await assertMessageFits(page);
}
async function readSharedGreeting(page) {
  return page.evaluate(()=>({
    to:document.getElementById('recipient').textContent,
    msg:[...document.querySelectorAll('#lines p')].map(p=>p.textContent).join('\n'),
    from:document.getElementById('sender').textContent,
  }));
}
const maxGreeting = {
  to:'W'.repeat(60),
  msg:Array.from({length:7},()=> '🎄'.repeat(40)).join('\n'),
  from:'W'.repeat(60),
  lang:'en',
};
const longFragment='#'+new URLSearchParams(maxGreeting);
const supportedGreetingSizes=[{width:390,height:844},{width:1440,height:900},{width:1366,height:657}];
async function assertGreetingLinks() {
  const context=await browser.newContext({viewport:supportedGreetingSizes[0],deviceScaleFactor:1});
  try {
    const page=await context.newPage();
    await page.addInitScript(()=>{
      window.greetingProbe={address:[]};
      Object.defineProperty(navigator,'clipboard',{value:{writeText:async value=>{window.greetingProbe.copied=value}}});
      Object.defineProperty(navigator,'share',{value:async data=>{window.greetingProbe.shared=data}});
      window.open=(url,target,features)=>{window.greetingProbe.whatsapp={url,target,features};return null};
      const fillText=CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText=function(text,...args){
        if(this.canvas.width===960&&this.canvas.height===620)window.greetingProbe.address.push(text);
        return fillText.call(this,text,...args);
      };
    });
    await page.goto(url);
    const write=page.locator('#write-card'), dialog=page.getByRole('dialog');
    const box=await write.boundingBox();
    assert.ok(box.width>=44&&box.height>=44,'The compose button is a 44px touch target');
    await write.click();
    await dialog.waitFor();
    assert.equal(await dialog.locator('#compose-privacy').textContent(),'Anyone with the link can read your message.');
    await page.waitForFunction(()=>document.activeElement?.id==='compose-title');
    await page.keyboard.press('Escape');
    await dialog.waitFor({state:'hidden'});
    await page.waitForFunction(()=>document.activeElement?.id==='write-card');
    await page.locator('#language').click();
    await write.click();
    assert.equal(await dialog.locator('#compose-privacy').textContent(),'任何拿到链接的人都可以阅读你的留言。');
    await dialog.getByLabel('收件人').fill('🎅'.repeat(41));
    assert.equal(await dialog.getByLabel('收件人').inputValue(),'🎅'.repeat(40));
    const greeting={to:'小美 🧑‍🎄',msg:'圣诞快乐 🎄\n平安喜乐 & with love!',from:'阿林 💛'};
    await dialog.getByLabel('收件人').fill(greeting.to);
    await dialog.getByLabel('留言').fill(greeting.msg);
    await dialog.getByLabel('寄件人（选填）').fill(greeting.from);
    assert.ok((await dialog.locator('#compose-msg-count').textContent()).startsWith(codePointCount(greeting.msg)+'/240'));
    await dialog.getByRole('button',{name:'复制链接'}).click();
    const copied=new URL(await page.evaluate(()=>window.greetingProbe.copied));
    assert.equal(copied.search,'','Shared greetings use only the fragment');
    assert.deepEqual(decodeGreeting(copied.hash),{...greeting,lang:'zh'});
    await dialog.getByRole('button',{name:'分享链接',exact:true}).click();
    assert.deepEqual(await page.evaluate(()=>window.greetingProbe.shared),{url:copied.href});
    await dialog.getByRole('button',{name:'分享到 WhatsApp'}).click();
    const whatsapp=await page.evaluate(()=>window.greetingProbe.whatsapp);
    const destination=new URL(whatsapp.url);
    assert.equal(destination.origin,'https://wa.me');
    assert.equal(destination.searchParams.get('text'),copied.href);
    assert.match(whatsapp.features,/(^|,)noopener(,|$)/);
    await dialog.getByRole('button',{name:'预览'}).click();
    await dialog.waitFor({state:'hidden'});
    const previewUrl=new URL(page.url());
    assert.equal(previewUrl.searchParams.get('card-test'),'1');
    assert.equal(previewUrl.hash,copied.hash);
    await page.locator('#replay:visible').waitFor();
    assert.deepEqual(await readSharedGreeting(page),greeting);
    assert.ok((await page.evaluate(()=>window.greetingProbe.address)).includes(greeting.to),'The address side uses the composed recipient');
    await page.waitForFunction(()=>!!navigator.serviceWorker.controller);

    await page.close();
    await context.setOffline(true);
    const shared=await context.newPage();
    await shared.goto(copied.href);
    await shared.locator('#open:not([disabled])').click();
    await shared.locator('#replay:visible').waitFor();
    assert.deepEqual(await readSharedGreeting(shared),greeting);
    await shared.locator('#language').click();
    assert.equal(await shared.locator('html').getAttribute('lang'),'en');
    assert.deepEqual(await readSharedGreeting(shared),greeting,'The UI toggle preserves the sender’s words');
    await assertSharedMessageFits(shared);
    const {to,msg,from}=decodeGreeting(longFragment);
    await shared.evaluate(fragment=>{location.hash=fragment},longFragment);
    await shared.waitForFunction(expected=>document.getElementById('recipient').textContent===expected,to);
    assert.deepEqual(await readSharedGreeting(shared),{to,msg,from});
    for(const viewport of supportedGreetingSizes){
      await shared.setViewportSize(viewport);
      await assertSharedMessageFits(shared);
    }
    await shared.evaluate(()=>{location.hash='#msg=No+signature'});
    await shared.waitForFunction(()=>document.getElementById('lines').textContent==='No signature');
    assert.equal(await shared.locator('#sender').isHidden(),true,'An unsigned custom message omits the default sender');
    await shared.evaluate(()=>{location.hash=''});
    await shared.waitForFunction(()=>document.getElementById('sender').textContent.includes('With love'));
    console.log('PASS compose, native share, WhatsApp, preview, offline link, and hash changes');
  } finally {await context.close()}
}
async function assertUntrustedGreeting() {
  const context=await browser.newContext({viewport:supportedGreetingSizes[0],serviceWorkers:'block'});
  try {
    const page=await context.newPage();
    await page.route('**/*.glb',route=>route.abort());
    const hostile='<img src=x onerror=window.greetingXss=1>';
    const text='#to='+encodeURIComponent(hostile)+'&msg='+encodeURIComponent(hostile)+'%0Ahello%ZZ&lang=zh';
    await page.goto(url+text);
    await page.locator('#fallback:not([hidden])').waitFor();
    assert.deepEqual(await readSharedGreeting(page),{to:hostile,msg:hostile+'\nhello%ZZ',from:''});
    assert.equal(await page.locator('#message img,#message a,#message script').count(),0);
    assert.equal(await page.evaluate(()=>window.greetingXss),undefined);
    await page.evaluate(fragment=>{location.hash=fragment},longFragment);
    const {to,msg,from}=decodeGreeting(longFragment);
    await page.waitForFunction(expected=>document.getElementById('recipient').textContent===expected,to);
    assert.deepEqual(await readSharedGreeting(page),{to,msg,from});
    assert.equal(await page.locator('#lines p').count(),6);
    for(const viewport of supportedGreetingSizes){
      await page.setViewportSize(viewport);
      await assertSharedMessageFits(page);
    }
    await page.evaluate(limit=>{location.hash='to='+'x'.repeat(limit)},fragmentLimit);
    await page.waitForFunction(()=>document.getElementById('recipient').textContent==='Dear friend,');
    console.log('PASS hostile text, malformed escapes, decoded limits, and fallback layout');
  } finally {await context.close()}
}
const readHeaderBottom=page=>page.evaluate(()=>Math.max(...['header','.controls'].map(selector=>
  document.querySelector(selector).getBoundingClientRect().bottom)));
async function assertMobileMoonClear(page) {
  const {moon,chrome}=await page.evaluate(()=>{
    const bounds=element=>element.getBoundingClientRect().toJSON();
    return {moon:bounds(document.getElementById('moon')),
      chrome:[...document.querySelectorAll('header .eyebrow,header h1,header p,.controls button')].map(element=>
        ({name:element.id||element.className,bounds:bounds(element)}))};
  });
  assert.ok(moon.width>0&&moon.height>0&&moon.left>=0&&moon.right<=390,'The mobile moon is visible in the viewport');
  for(const {name,bounds} of chrome){
    assert.ok(moon.right<=bounds.left||moon.left>=bounds.right||moon.top>=bounds.bottom||moon.bottom<=bounds.top,
      `The mobile moon overlaps ${name}`);
  }
}
const waitForFullReveal=page=>page.waitForFunction(()=>window.__christmasCardTest.frames?.at(-1)?.replayOpaque);
async function observeAudio(page) {
  await page.addInitScript(()=>{
    const NativeAudioContext=window.AudioContext;
    const probe=window.cardAudioProbe={contexts:0,oscillators:0,master:null};
    window.AudioContext=class extends NativeAudioContext {
      constructor(){
        super();
        probe.contexts++;
        probe.context=this;
      }
      createGain(){
        const gain=super.createGain();
        probe.master??=gain;
        return gain;
      }
      createOscillator(){
        probe.oscillators++;
        return super.createOscillator();
      }
    };
  });
}
async function readSnapshot(page) {
  await page.waitForFunction(()=>window.__christmasCardTest.snapshot!==null,undefined,{polling:50});
  return page.evaluate(()=>window.__christmasCardTest.snapshot);
}
async function observeWarmDraws(page) {
  await page.waitForFunction(()=>!!window.__christmasCardTest?.renderer);
  await page.evaluate(()=>{
    const hook=window.__christmasCardTest, renderer=hook.renderer;
    const has=renderer.extensions.has.bind(renderer.extensions);
    renderer.extensions.has=name=>name!=='KHR_parallel_shader_compile'&&has(name);
    const warm=hook.warmDraws={draws:[],late:[],parallelCompiles:0};
    const compile=renderer.compileAsync.bind(renderer);
    renderer.compileAsync=(...args)=>{warm.parallelCompiles++;return compile(...args)};
    const render=renderer.render.bind(renderer);
    renderer.render=(scene,camera)=>{
      const count=renderer.info.programs.length;
      render(scene,camera);
      const added=renderer.info.programs.length-count;
      if(renderer.getScissorTest()){
        const nodes=[];
        scene.traverseVisible(object=>{if(object.name)nodes.push(object.name)});
        warm.draws.push({nodes,calls:renderer.info.render.calls,letterDetached:scene.children.some(object=>object.name==='Letter')});
      }else if(added>0){
        warm.late.push({added,after:hook.frames?.at(-1)?.phase||'loading'});
      }
    };
  });
}
function assertWarmDraws({draws,late,parallelCompiles}) {
  assert.equal(parallelCompiles,0,'Exercise warm-up without the parallel shader extension');
  assert.equal(draws.length,4,'Every warm-up pass renders within the deadline');
  assert.ok(draws.every(draw=>draw.calls>0),'Warm-up submits real draw calls');
  assert.ok(['Address','EntranceStardust'].every(name=>draws[0].nodes.includes(name)));
  assert.ok(draws[1].nodes.includes('SealCracks'));
  assert.ok(['SealShard1','SealShard5','MouthGlow','Stardust'].every(name=>draws[2].nodes.includes(name)));
  assert.equal(draws[3].letterDetached,true);
  assert.deepEqual(late,[],'Every playback shader is ready before the first entrance frame');
}
async function holdModel(page) {
  let release;
  const gate=new Promise(resolve=>{release=resolve});
  await page.route('**/*.glb',async route=>{await gate;await route.continue()},{times:1});
  return release;
}
async function waitForOpen(page, started) {
  const remaining=15000-(performance.now()-started);
  assert.ok(remaining>0,'The 15 s readiness budget expired during navigation');
  await page.locator('#open:not([hidden]):not([disabled])').waitFor({timeout:remaining});
  assert.ok(performance.now()-started<=15000,'Open must become available within 15 s');
  assert.equal(await page.locator('#loading').isVisible(),false);
}
async function assertDesktopEntranceTimeline() {
  const context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1});
  try {
    const page=await context.newPage();
    const started=performance.now();
    await page.goto(url,{waitUntil:'domcontentloaded',timeout:15000});
    // Sample one late frame without freezing playback or recording a frame trace.
    await page.evaluate(time=>window.__christmasCardTest.captureAt(time,'entrance',false),
      entranceDuration-maxFrameDelta-.0001);
    await waitForOpen(page,started);
    const {entranceCompletion,snapshot,frames}=await page.evaluate(()=>{
      const hook=window.__christmasCardTest;
      return {entranceCompletion:hook.entranceCompletion,snapshot:hook.snapshot,frames:hook.frames};
    });
    assert.equal(frames,null,'Desktop timeline runs without a frame trace');
    assertEntranceCompletion(entranceCompletion,snapshot?.time);
    const {left,top,right,bottom}=snapshot.bounds;
    assert.ok(left>=0&&top>0&&right<1440&&bottom<900,'The late landing frame remains in the viewport');
    console.log('PASS 1440x900: full entrance finishes on its timeline without frame recording');
  } finally {await context.close()}
}
async function assertRecordingReady() {
  const viewport={width:1440,height:900};
  const context=await browser.newContext({
    viewport,deviceScaleFactor:1,recordVideo:{dir:'output/christmas-card/recording',size:viewport},
  });
  let video;
  try {
    const page=await context.newPage();
    video=page.video();
    const started=performance.now();
    await page.goto(url,{waitUntil:'domcontentloaded',timeout:15000});
    await waitForOpen(page,started);
  } finally {await context.close()}
  assert.ok((await fs.stat(await video.path())).size>0,'Desktop recording was saved');
  console.log('PASS 1440x900 with recordVideo: Open available within 15 s');
}
async function assertWarmupRecovers(mode) {
  const context=await browser.newContext({viewport:{width:1440,height:900},serviceWorkers:'block'});
  try {
    const page=await context.newPage(), release=await holdModel(page);
    if(mode==='compile'){
      // Keep the display at roughly 8 fps after reveal to exercise the entrance cap.
      await page.addInitScript(()=>{
        const requestFrame=window.requestAnimationFrame.bind(window);
        window.requestAnimationFrame=callback=>requestFrame(time=>{
          if(document.getElementById('loading')?.hidden&&document.getElementById('open')?.disabled){
            setTimeout(()=>requestFrame(callback),120);
          }else callback(time);
        });
      });
    }else await injectRenderStall(page,'entrance');
    const started=performance.now();
    try {
      await page.goto(url,{waitUntil:'domcontentloaded',timeout:15000});
      await page.waitForFunction(()=>!!window.__christmasCardTest?.renderer);
      await page.evaluate(mode=>{
        const hook=window.__christmasCardTest, renderer=hook.renderer;
        hook.frames=[];
        const probe=window.__warmupProbe={compiles:0,draws:0,flushes:0,polls:0,deleted:0,loadingDuringPolls:true};
        const has=renderer.extensions.has.bind(renderer.extensions);
        renderer.extensions.has=name=>name==='KHR_parallel_shader_compile'||has(name);
        renderer.compileAsync=()=>{
          probe.compiles++;
          return mode==='compile'?new Promise(()=>{}):Promise.resolve();
        };
        if(mode!=='fence')return;
        const render=renderer.render.bind(renderer);
        renderer.render=(...args)=>{
          if(renderer.getScissorTest()){probe.draws++;return}
          render(...args);
        };
        const gl=renderer.getContext(), flush=gl.flush.bind(gl), deleteSync=gl.deleteSync.bind(gl);
        gl.flush=()=>{probe.flushes++;flush()};
        gl.clientWaitSync=()=>{
          probe.polls++;
          probe.loadingDuringPolls &&= !document.getElementById('loading').hidden;
          return gl.TIMEOUT_EXPIRED;
        };
        gl.deleteSync=fence=>{probe.deleted++;deleteSync(fence)};
      },mode);
    } finally {release()}
    await waitForOpen(page,started);
    const {probe,visibleMs,flight,completion} = await page.evaluate(()=>{
      const flight=window.__christmasCardTest.frames.filter(frame=>frame.phase==='entrance');
      return {
        probe:window.__warmupProbe,
        visibleMs:performance.now()-flight[0].presentedAt,
        flight,completion:window.__christmasCardTest.entranceCompletion,
      };
    });
    assert.equal(probe.compiles,1);
    if(mode==='fence'){
      assert.ok(probe.draws>0&&probe.flushes>0&&probe.polls>0,'The warm draw reached an unsignaled fence');
      assert.equal(probe.deleted,1,'The timed-out fence was released');
      assert.equal(probe.loadingDuringPolls,true);
      assert.ok(flight[0].time===0&&flight[0].bounds.right<=.5,'A stalled entrance starts outside the viewport');
      assert.ok(assertStalledStep(flight,'entrance').bounds.right<144,'The envelope stays near the left edge after a stall');
    }else{
      assert.equal(completion.reason,'watchdog');
      assert.ok(completion.time<entranceDuration*.8,'The slow frames would not finish the full flight in time');
      assert.ok(visibleMs>=entranceBudgetMs-150&&visibleMs<entranceBudgetMs+1000,'Persistent slow frames settle by the entrance watchdog');
    }
    console.log(`PASS warm-up recovery: ${mode} never completes`);
  } finally {await context.close()}
}
async function assertLoadingWatchdog() {
  const context=await browser.newContext({serviceWorkers:'block'});
  try {
    const page=await context.newPage(), release=await holdModel(page);
    try {
      await page.goto(url,{waitUntil:'domcontentloaded'});
      await page.locator('#loading').waitFor();
      await page.locator('#fallback').waitFor({timeout:15000});
      assert.equal(await page.locator('#message').isVisible(),true);
      assert.equal(await page.locator('#loading').isVisible(),false);
    } finally {
      release();
      await page.unrouteAll({behavior:'wait'});
    }
    console.log('PASS loading watchdog: greeting remains available when the GLB request hangs');
  } finally {await context.close()}
}
async function injectRenderStall(page,stalledPhase) {
  await page.addInitScript(stalledPhase => {
    const stallMs=1100;
    const requestFrame=window.requestAnimationFrame.bind(window);
    let stalled=false;
    window.requestAnimationFrame=callback=>requestFrame(timestamp=>{
      const last=window.__christmasCardTest?.frames?.at(-1);
      const phase=last?.phase;
      if(phase===stalledPhase&&(phase==='entrance'||(last.time>=1.22&&!last.burst))&&!stalled){
        stalled=true;
        // A blocked render leaves a gap between animation-frame timestamps.
        const until=performance.now()+stallMs;
        while(performance.now()<until){}
      }
      callback(timestamp);
    });
  },stalledPhase);
}
function assertStalledStep(frames,phase) {
  let firstAfterStall;
  for(let i=1;i<frames.length;i++){
    const before=frames[i-1], after=frames[i];
    if(before.phase!==phase||after.phase!==phase||after.timestamp-before.timestamp<1000)continue;
    assert.ok(after.time-before.time<=maxFrameDelta+.0001,`The ${phase} skipped ahead after a stall`);
    firstAfterStall??=after;
  }
  assert.ok(firstAfterStall,`No long render stall observed during ${phase}`);
  return firstAfterStall;
}
async function assertButtonClear(page, idle) {
  const button=await page.locator('#open').boundingBox();
  assert.ok(button, 'Open button is visible');
  assert.ok(button.y+button.height<=page.viewportSize().height, 'Open fits inside the viewport');
  assert.ok(idle.bounds.bottom < button.y, `Envelope reaches ${idle.bounds.bottom}px, Open starts at ${button.y}px`);
  const stageBottom=await page.locator('.scene').evaluate(e=>e.getBoundingClientRect().bottom);
  assert.ok(button.y>=stageBottom, 'Open sits below the envelope stage');
  const write=await page.locator('#write-card').boundingBox();
  assert.ok(write&&write.width>=44&&write.height>=44&&idle.bounds.top>write.y+write.height,'Write a card clears the envelope');
}
function assertViewportFlight(frames,width,height) {
  let crossesLeft=false, fullyEntered=false;
  const phases=new Set();
  for (const {phase,time,bounds,canvas,burstBounds} of frames) {
    phases.add(phase);
    assert.deepEqual([canvas.left,canvas.top,canvas.right,canvas.bottom],[0,0,width,height], 'Canvas covers the real viewport');
    if(phase==='entrance'&&bounds.right<=0)continue;
    if(phase==='entrance'&&!fullyEntered){
      crossesLeft ||= bounds.left<0;
      fullyEntered ||= bounds.left>=0;
    }else assert.ok(bounds.left>=0, `Envelope cut off left during ${phase} at ${time}s`);
    assert.ok(bounds.right<width&&bounds.top>0&&bounds.bottom<height,
      `Envelope touches a viewport edge during ${phase} at ${time}s: ${JSON.stringify(bounds)}`);
    if(burstBounds){
      const {left,right,top,bottom}=burstBounds;
      assert.ok(left>=0&&right<width&&top>0&&bottom<height,`Burst clipped at ${time}s: ${JSON.stringify(burstBounds)}`);
    }
  }
  assert.ok(crossesLeft&&fullyEntered, 'Envelope crosses viewport x=0 and enters completely');
  for (const phase of ['entrance','idle','opening','handover','message']) assert.ok(phases.has(phase), `Missing ${phase} frames`);
}
function assertEntranceCompletion(completion,lastStep) {
  assert.equal(completion?.reason,'timeline',`Full flight must finish on its timeline: ${JSON.stringify(completion)}`);
  assert.ok(completion.time>=entranceDuration&&completion.time<=entranceDuration+maxFrameDelta+.0001,
    'The completed flight takes 3.12 animation seconds');
  assert.ok(lastStep>=entranceDuration-maxFrameDelta-.0001,
    'The recorded flight reaches its final animation step');
}
function assertEntranceLoop(entrance,idle) {
  const first=entrance[0].bounds;
  assert.ok(first.right-first.left<(idle.bounds.right-idle.bounds.left)*(idle.canvas.width===390?.46:.42),
    'Envelope starts small in the distance');
  const travelling=entrance.find(frame=>frame.time>=1.2), later=entrance.find(frame=>frame.time>=1.5);
  assert.ok(travelling.bounds.left>0&&Math.hypot(later.center[0]-travelling.center[0],later.center[1]-travelling.center[1])>8,
    'The envelope keeps travelling after 1.2 s');
  const visibleAddress=entrance.filter(frame=>frame.address&&frame.bounds.left>0);
  assert.ok(visibleAddress.at(-1).time-visibleAddress[0].time>1,'Address side stays in view for more than a second');
  const loop=entrance.filter(frame=>frame.time>=loopStart&&frame.time<=loopEnd).map(frame=>frame.center);
  const xs=loop.map(([x])=>x), ys=loop.map(([,y])=>y);
  const cx=(Math.min(...xs)+Math.max(...xs))/2, cy=(Math.min(...ys)+Math.max(...ys))/2;
  let sweep=0;
  for(let i=1;i<loop.length;i++){
    const ax=xs[i-1]-cx, ay=ys[i-1]-cy, bx=xs[i]-cx, by=ys[i]-cy;
    sweep+=Math.atan2(ax*by-ay*bx,ax*bx+ay*by);
  }
  assert.ok(Math.abs(Math.abs(sweep)-2*Math.PI)<.25,'The envelope traces one complete loop');
}
function assertOpeningCamera(frames,idle,burstSnapshot) {
  const opening=frames.filter(frame=>frame.phase==='opening');
  const idlePosition=idle.cameraPosition, maxStep=idlePosition[2]*.047;
  for(const frame of frames.filter(frame=>frame.phase==='idle'))assert.deepEqual(frame.cameraPosition,idlePosition);
  assert.deepEqual(opening[0].cameraPosition,idlePosition,'Opening starts from the idle camera');
  let previous=idle;
  for(const frame of opening){
    const step=Math.hypot(...frame.cameraPosition.map((value,axis)=>value-previous.cameraPosition[axis]));
    assert.ok(step<=maxStep,`Camera moved ${step} units in one frame, above ${maxStep}`);
    assert.ok(Math.abs(frame.cameraRoll-previous.cameraRoll)<=.0031,'Camera roll eases between frames');
    assert.ok(Math.abs(frame.cameraPitch-previous.cameraPitch)<=.006,'Camera pitch eases between frames');
    assert.ok(Math.abs(frame.cameraFov-previous.cameraFov)<=.67,'Lens eases between frames');
    previous=frame;
  }
  const close=opening.reduce((closest,frame)=>frame.cameraPosition[2]<closest.cameraPosition[2]?frame:closest);
  assert.ok(close.cameraPosition[2]<idlePosition[2]*.77,'Camera pushes in strongly while the flap opens');
  assert.ok(Math.abs(close.cameraRoll)>=.035&&Math.abs(close.cameraRoll)<=.055,'Close shot has a slight tilt');
  assert.ok(close.cameraPitch<idle.cameraPitch-.075,'Close shot looks more directly into the mouth');
  if(close.canvas.width===390)assert.ok(close.mouthWidth>=close.canvas.width*.90,'Mouth nearly fills the mobile width');
  else assert.ok(close.bounds.bottom-close.bounds.top>=close.canvas.height*.69,'The close shot fills most of the desktop height');
  assert.ok(burstSnapshot.cameraPosition[2]>idlePosition[2],'Camera widens again by the burst');
  assert.deepEqual(burstSnapshot.camera.slice(16),idle.camera.slice(16),'The lens and viewport projection stay fixed');
  const firstMessage=frames.find(frame=>frame.phase==='message');
  assert.deepEqual(firstMessage.cameraPosition,opening.at(-1).cameraPosition,'The wide shot settles before the message');
}
function assertOpeningCadence(frames, burstSnapshot) {
  const opening=frames.filter(frame=>frame.phase==='opening');
  let lastMotion=0, pose={flap:0,seal:{progress:0,separated:false},letter:0,burst:false};
  for(const frame of opening){
    assert.ok(frame.time-lastMotion<=.5,`Opening still for more than 0.5 s by ${frame.time}s`);
    if(Math.abs(frame.flap-pose.flap)>=.035||Math.abs(frame.seal.progress-pose.seal.progress)>=.04||
        frame.seal.separated!==pose.seal.separated||
        Math.abs(frame.letter-pose.letter)>=.025||frame.burst!==pose.burst){
      lastMotion=frame.time;pose=frame;
    }
  }
  const firstBurst=opening.find(frame=>frame.burst);
  assert.ok(firstBurst&&firstBurst.flap>-3.02&&burstSnapshot.flap<firstBurst.flap-.07,'Burst begins while the flap is still swinging');
  assert.ok(opening.some(frame=>frame.burst&&frame.time<firstBurst.time+.5&&frame.letter>.015),'Letter lift overlaps the burst');
  const fracture=opening.find(frame=>frame.seal.separated);
  assert.ok(opening.some(frame=>!frame.seal.separated&&frame.seal.progress>.80),'Golden cracks spread before the break');
  assert.equal(fracture?.seal.visible,5);
  assert.ok(opening.some(frame=>frame.seal.separated&&frame.seal.visible===0&&frame.particleCount>0),
    'The seal dissolves into visible stardust');
  assert.ok(burstSnapshot.halo>.75,'Warm beams accompany the burst');
  assert.ok(burstSnapshot.particles.filter(p=>!p.gold).length>10,'The pool contains slow glowing snow');
  assert.ok(new Set(burstSnapshot.particles.filter(p=>p.gold).map(p=>p.size.toFixed(3))).size>=3,
    'Stardust has three distinct sizes');
  assert.ok(frames.every(frame=>frame.particleCount<=particleLimit),'Particle pool keeps its hard cap');
}
function assertLetterHandover(frames,headerBottom) {
  const distance=(a,b)=>Math.max(...['left','top','right','bottom'].map(edge=>Math.abs(a[edge]-b[edge])));
  const lift=frames.filter(frame=>frame.phase==='opening').at(-1);
  const flight=frames.filter(frame=>frame.phase==='handover');
  const greeting=frames.filter(frame=>frame.phase==='message');
  const firstStar=flight.find(frame=>frame.starOpacity!==undefined);
  assert.ok(firstStar&&firstStar.time<handoverDuration-starApproachTime+maxFrameDelta+.0001&&
    firstStar.starOpacity>=.65&&firstStar.starOpacity<.9,'The star starts visibly during the approach');
  for(const frame of frames.filter(frame=>frame.letterBounds)){
    assert.ok(frame.letterBounds.top>=headerBottom,
      `Letter crosses header or controls during ${frame.phase} at ${frame.time}s: ${frame.letterBounds.top} < ${headerBottom}`);
  }
  assert.ok(lift.letter>2.1&&distance(lift.letterRect,flight[0].letterRect)<2,'The fully lifted letter starts the flight in place');
  let moving=flight[0], previous=flight[0];
  for(const frame of flight){
    assert.ok(distance(previous.letterRect,frame.letterRect)<21,'Projected paper edges move continuously');
    assert.ok(frame.time-moving.time<=.5,'The letter keeps moving toward the reader');
    if(distance(moving.letterRect,frame.letterRect)>.75)moving=frame;
    previous=frame;
  }
  assert.ok(distance(previous.letterRect,greeting[0].letterRect)<1.5,'There is no jump when the greeting appears');
  assert.ok(distance(greeting[0].message,greeting[0].letterRect)<1,'The HTML overlays the projected paper');
  const order=['message-star','recipient','line','line','line','sender','replay'];
  assert.deepEqual(greeting[0].revealed,order.slice(0,1));
  assert.equal(greeting[0].starOpaque,true,'The star is visible on the first card frame');
  let count=1;
  for(const frame of greeting){
    assert.deepEqual(frame.revealed,order.slice(0,frame.revealed.length));
    assert.ok(frame.revealed.length>=count&&frame.revealed.length<=count+1,'One item appears at a time, top to bottom');
    count=frame.revealed.length;
  }
  assert.equal(count,order.length);
  const completed=greeting.find(frame=>frame.replayOpaque);
  assert.ok(completed?.sequenceTime<=5.5,`Full greeting took ${completed?.sequenceTime}s of animation time`);
}
try {
 await assertDesktopEntranceTimeline();
 await assertRecordingReady();
 for(const mode of ['fence','compile'])await assertWarmupRecovers(mode);
 await assertLoadingWatchdog();
 for (const [width,height] of [[390,844],[1440,900]]) {
  const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1}),page=await context.newPage(),errors=[];
  if(width===1440)await observeAudio(page);
  await page.addInitScript(()=>{
    window.__cardCspViolations=[];
    window.__sleighPasses=0;
    addEventListener('securitypolicyviolation',event=>window.__cardCspViolations.push(event.violatedDirective));
    document.addEventListener('animationstart',event=>{
      if(event.animationName!=='moon-crossing')return;
      window.__sleighPasses++;
      const effect=event.target.getAnimations().find(animation=>animation.animationName==='moon-crossing').effect;
      const opaque=effect.getKeyframes().filter(keyframe=>Number(keyframe.opacity)===1);
      window.__sleighVisibility={width:event.target.getBoundingClientRect().width,
        seconds:effect.getComputedTiming().duration*(opaque.at(-1).computedOffset-opaque[0].computedOffset)/1000};
    });
  });
  await injectRenderStall(page,'opening');
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  page.on('requestfailed',r=>errors.push(`${r.url()}: ${r.failure()?.errorText}`));
  page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
  const releaseModel=await holdModel(page);
  await page.goto(url,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>!!window.__christmasCardTest);
  await page.locator('#loading').waitFor();
  if(width===390)await assertMobileMoonClear(page);
  const loadingStar=page.locator('.loading-stars span').nth(1);
  assert.equal(await loadingStar.evaluate(e=>getComputedStyle(e).animationName),'loading-twinkle');
  const starBox=await loadingStar.boundingBox(), loadingText=await page.locator('#loading-text').boundingBox();
  assert.ok(starBox&&loadingText&&starBox.y+starBox.height<loadingText.y,'Glowing stars sit above the loading text');
  assert.equal(await page.locator('.snowfall').evaluate(e=>getComputedStyle(e,'::before').animationName),'snow-near');
  await page.evaluate(()=>{
    const hook=window.__christmasCardTest;
    hook.frames=[];
    hook.captureAt(0,'idle');
  });
  if(width===1440)await observeWarmDraws(page);
  try {
    // Give a module-load clock time to expire while the model is still loading.
    await page.waitForTimeout(1500);
    assert.equal(await page.locator('#loading').isVisible(),true);
  } finally {releaseModel()}
  await page.waitForFunction(()=>window.__christmasCardTest.frames.some(frame=>frame.phase==='entrance'));
  const first=await page.evaluate(()=>window.__christmasCardTest.frames.find(frame=>frame.phase==='entrance'));
  assert.ok(first.time===0&&first.bounds.right<=.5,`First presented entrance frame is on-screen: ${JSON.stringify(first)}`);
  assert.equal(await loadingStar.isVisible(),false);
  assert.equal(await page.locator('#open').isDisabled(),true);
  await page.locator('#open').dispatchEvent('click');
  // The idle capture was armed before loading finished, so it never resets the entrance clock.
  const idle=await readSnapshot(page);
  await page.locator('#open:not([disabled])').waitFor({timeout:30000});
  if(width===1440)assert.equal(await page.evaluate(()=>window.cardAudioProbe.contexts),0,'The unprompted entrance stays silent');
  assert.equal(await page.evaluate(()=>window.__sleighPasses),1,'The sleigh crosses the moon once during the entrance');
  const sleigh=await page.evaluate(()=>window.__sleighVisibility);
  assert.ok(sleigh.seconds>=2&&sleigh.width>=(width===390?80:180),'The sleigh is large and fully visible for at least two seconds');
  const headerBottom=await readHeaderBottom(page);
  await assertButtonClear(page,idle);
  await page.evaluate(()=>window.__christmasCardTest.captureAt(.38,'idle'));
  assert.deepEqual((await readSnapshot(page)).camera,idle.camera,'Idle float leaves the camera still');
  assert.equal(await page.locator('meta[name=viewport]').getAttribute('content'),'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover');
  assert.equal(await page.locator('h1').count(),1);
  assert.ok(await page.evaluate(()=>document.querySelector('header').getBoundingClientRect().top>=document.querySelector('.controls').getBoundingClientRect().bottom));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await assertHero(page,width,height,true);
  const body=await envelopePixels(page),[red,green,blue]=body.median;
  assert.ok(body.count>1000&&red>=130&&red<=180&&green<45&&blue<55,`Envelope body colour outside deep red range: ${JSON.stringify(body.median)}`);
  await page.screenshot({path:`output/christmas-card/${width}-01-idle.png`});
  await page.evaluate(()=>window.__christmasCardTest.captureAt(.58));
  await page.locator('#open').click();
  const opening=(await readSnapshot(page)).time;
  await page.screenshot({path:`output/christmas-card/${width}-02-opening.png`});
  await page.evaluate(()=>window.__christmasCardTest.captureAt(.98));
  const mid=(await readSnapshot(page)).time;
  await assertHero(page,width,height);
  await page.screenshot({path:`output/christmas-card/${width}-03-mid-flap.png`});
  await page.evaluate(time=>window.__christmasCardTest.captureAt(time),idle.burstTime+.3);
  const burstSnapshot=await readSnapshot(page);
  assert.ok(opening<mid&&mid<burstSnapshot.time&&burstSnapshot.age>=.29&&burstSnapshot.age<.5);
  await page.screenshot({path:`output/christmas-card/${width}-04-burst.png`});
  await assertBurstPixels(page,burstSnapshot);
  await page.evaluate(time=>window.__christmasCardTest.captureAt(time,'handover'),handoverDuration-.065);
  const flying=await readSnapshot(page);
  await assertStarPixels(page,'approach');
  const beforePaper=await page.locator('#canvas').screenshot();
  await page.evaluate(()=>window.__christmasCardTest.captureAt(0,'message'));
  const arrived=await readSnapshot(page);
  assert.equal(arrived.time,0,'The browser captured the first arrival frame');
  await assertStarPixels(page,'first arrival');
  const afterPaper=await page.locator('#canvas').screenshot();
  await assertPaperPixels(page,[
    {png:beforePaper.toString('base64'),rect:flying.letterRect},
    {png:afterPaper.toString('base64'),rect:arrived.letterRect},
  ]);
  assert.equal(await page.locator('#message').evaluate(e=>getComputedStyle(e).backgroundColor),'rgba(0, 0, 0, 0)');
  await page.evaluate(()=>window.__christmasCardTest.release());
  await waitForFullReveal(page);
  const {frames,completion,warmDraws}=await page.evaluate(()=>{
    const hook=window.__christmasCardTest, frames=hook.frames;
    hook.frames=null;
    return {frames,completion:hook.entranceCompletion,warmDraws:hook.warmDraws};
  });
  assertViewportFlight(frames,width,height);
  const entrance=frames.filter(frame=>frame.phase==='entrance');
  assertEntranceLoop(entrance,idle);
  if(width===390)assertEntranceCompletion(completion,entrance.at(-1).time);
  if(width===1440)assertWarmDraws(warmDraws);
  assertOpeningCamera(frames,idle,burstSnapshot);
  assertStalledStep(frames,'opening');
  assertOpeningCadence(frames,burstSnapshot);
  assertLetterHandover(frames,headerBottom);
  assert.deepEqual(await page.evaluate(()=>window.__cardCspViolations),[],'HTML alignment preserves production CSP');
  await assertMessageFits(page);
  await page.screenshot({path:`output/christmas-card/${width}-05-message.png`});
  // Longer representative English and Chinese copy remains visible without clipping.
  await page.locator('#lines p').evaluateAll(lines=>lines.forEach((line,i)=>line.textContent=['May your home be filled with laughter and warmth throughout this beautiful season,','and may every new day bring hope, kindness, and precious moments to share,','wishing you a joyful Christmas and a bright and peaceful new year.'][i]));
  await assertMessageFits(page);
  await page.locator('#language').click();assert.equal(await page.locator('html').getAttribute('lang'),'zh-Hans');
  if(width===390)await assertMobileMoonClear(page);
  await page.screenshot({path:`output/christmas-card/${width}-06-message-zh.png`});
  await page.locator('#lines p').evaluateAll(lines=>lines.forEach((line,i)=>line.textContent=['愿这个温暖的圣诞季为你和家人带来欢笑与幸福，','愿新的一年里每一天都充满希望、平安和美好，','愿我们珍惜相聚时光，拥有无尽的喜悦与祝福。'][i]));
  await assertMessageFits(page);
  await page.locator('#language').click();
  await page.evaluate(()=>window.__christmasCardTest.captureAt(0,'idle'));
  await page.locator('#replay').click();
  const replayIdle=await readSnapshot(page);
  assert.deepEqual(replayIdle.camera,idle.camera,'Replay resets the camera to the idle position');
  assert.deepEqual(replayIdle.seal,{separated:false,visible:5,progress:0});
  assert.equal(replayIdle.particleCount,0);
  assert.equal(replayIdle.letter,0);
  await assertButtonClear(page,replayIdle);
  await page.evaluate(()=>window.__christmasCardTest.release());
  await page.locator('#open').click();
  await page.locator('#message:not(.arriving):not([hidden])').waitFor();
  assert.equal(await page.evaluate(()=>window.__sleighPasses),1);
  await page.waitForFunction(async()=>{const r=await navigator.serviceWorker.getRegistration('./');return !!r?.active});
  await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
  await context.setOffline(true);
  await page.reload();await page.locator('#open:not([disabled])').waitFor({timeout:30000});
  await page.locator('#open').click();await page.locator('#message:not(.arriving):not([hidden])').waitFor();
  assert.deepEqual(errors,[]);
  console.log(`PASS ${width}x${height}: entrance loop, eased camera, interaction, layout and offline reload`);
  await context.close();
 }
 const short=await browser.newContext({viewport:{width:1366,height:657},deviceScaleFactor:1});
 const shortPage=await short.newPage();
 await shortPage.goto(url);
 await shortPage.locator('#open').waitFor();
 await shortPage.evaluate(()=>window.__christmasCardTest.captureAt(3.5,'idle'));
 await assertButtonClear(shortPage,await readSnapshot(shortPage));
 const shortHeader=await readHeaderBottom(shortPage);
 await shortPage.evaluate(()=>{
   window.__christmasCardTest.frames=[];
   window.__christmasCardTest.release();
 });
 await shortPage.locator('#open').click();
 await waitForFullReveal(shortPage);
 assertLetterHandover(await shortPage.evaluate(()=>window.__christmasCardTest.frames),shortHeader);
 await short.close();
 console.log('PASS 1366x657: envelope and letter clear the controls and header, greeting completes on time');
 const reduced=await browser.newContext({reducedMotion:'reduce'});
 const reducedPage=await reduced.newPage();
 await observeAudio(reducedPage);
 const releaseReduced=await holdModel(reducedPage);
 await reducedPage.goto(url);
 await reducedPage.waitForFunction(()=>!!window.__christmasCardTest);
 try {
   const loadingStar=reducedPage.locator('.loading-stars span').nth(1);
   await loadingStar.waitFor();
   assert.equal(await loadingStar.evaluate(e=>getComputedStyle(e).animationName),'none');
 } finally {releaseReduced()}
 await reducedPage.evaluate(()=>{
   window.__christmasCardTest.frames=[];
   window.__christmasCardTest.captureAt(0,'idle');
 });
 const reducedIdle=await readSnapshot(reducedPage);
 await reducedPage.evaluate(()=>document.body.click());
 assert.deepEqual(await reducedPage.evaluate(()=>{
   const {contexts,oscillators}=window.cardAudioProbe;
   return {contexts,oscillators};
 }),{contexts:0,oscillators:0},'Loading and synthetic clicks produce no audio');
 assert.equal(await reducedPage.locator('.sleigh').isVisible(),false);
 assert.equal(await reducedPage.locator('.fir-lights').first().evaluate(e=>getComputedStyle(e).animationName),'none');
 await reducedPage.evaluate(()=>window.__christmasCardTest.release());
 await reducedPage.locator('#open').click();
 await reducedPage.locator('#message:not([hidden])').waitFor();
 await reducedPage.waitForFunction(()=>window.__christmasCardTest.frames.some(frame=>frame.phase==='message'));
 const reducedFrames=await reducedPage.evaluate(()=>window.__christmasCardTest.frames);
 assert.ok(reducedFrames.every(frame=>frame.phase!=='entrance'&&frame.phase!=='opening'));
 for(const frame of reducedFrames)assert.deepEqual(frame.cameraPosition,reducedIdle.cameraPosition);
 assert.equal(await reducedPage.locator('#lines [data-pending]').count(),0);
 assert.equal(await reducedPage.locator('.snowfall').evaluate(e=>getComputedStyle(e,'::before').animationName),'none');
 await reducedPage.waitForFunction(()=>{
   const {context,oscillators,master}=window.cardAudioProbe;
   return context?.state==='running'&&oscillators>0&&master.gain.value>0;
 });
 const mute=reducedPage.locator('#mute');
 await mute.click();
 assert.equal(await mute.getAttribute('aria-pressed'),'true');
 await reducedPage.waitForFunction(()=>window.cardAudioProbe.master.gain.value===0,undefined,
   {polling:50,timeout:5000}); // The audio thread applies gain to the shared music and effects bus.
 assert.equal(await reducedPage.evaluate(key=>localStorage.getItem(key),mutePreference),'1');
 await mute.click();
 await reducedPage.waitForFunction(()=>window.cardAudioProbe.master.gain.value>0,undefined,{polling:50,timeout:5000});
 await mute.click();
 await reducedPage.reload({waitUntil:'domcontentloaded'});
 await reducedPage.waitForFunction(()=>document.getElementById('mute').getAttribute('aria-pressed')==='true');
 assert.equal(await reducedPage.evaluate(()=>window.cardAudioProbe.contexts),0,'Reload restores mute without creating an audio context');
 await reduced.close();
 for(const failure of ['WebGL','GLB']){
   const context=await browser.newContext({serviceWorkers:'block'}),page=await context.newPage();
   if(failure==='GLB')await page.route('**/*.glb',route=>route.abort());
   else await page.addInitScript(()=>{
     const getContext=HTMLCanvasElement.prototype.getContext;
     HTMLCanvasElement.prototype.getContext=function(type,...options){
       return type.startsWith('webgl')?null:getContext.call(this,type,...options);
     };
   });
   await page.goto(url);
   await page.locator('#fallback:not([hidden])').waitFor();
   assert.equal(await page.locator('#message').isVisible(),true);
   assert.equal(await page.locator('#loading').isVisible(),false);
   await context.close();
 }
 console.log('PASS reduced motion and WebGL/GLB fallbacks');
 await assertGreetingLinks();
 await assertUntrustedGreeting();
} finally {await browser.close();await new Promise(resolve=>server.close(resolve))}
