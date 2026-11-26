import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { chromium } from 'playwright';
import { launchOptions } from './browser-test-utils.mjs';
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
async function assertHero(page,width,height) {
  const p=await envelopePixels(page);
  if(width===390) assert.ok(p.width>=width*.85,`Mobile envelope width ${p.width}px is below 85% of ${width}px`);
  else assert.ok(p.height>=height*.45,`Desktop envelope height ${p.height}px is below 45% of ${height}px`);
  assert.ok(p.minX>0&&p.maxX<p.canvasWidth-1&&p.minY>0&&p.maxY<p.canvasHeight-1,`Envelope clipped: ${JSON.stringify(p)}`);
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
try {
 for (const [width,height] of [[390,844],[1440,900]]) {
  const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  page.on('requestfailed',r=>errors.push(`${r.url()}: ${r.failure()?.errorText}`));
  page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
  await page.goto(url);
  await page.locator('#open:not([disabled])').waitFor({timeout:30000});
  await page.waitForTimeout(1700);
  assert.equal(await page.locator('meta[name=viewport]').getAttribute('content'),'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover');
  assert.equal(await page.locator('h1').count(),1);
  assert.ok(await page.evaluate(()=>document.querySelector('header').getBoundingClientRect().top>=document.querySelector('.controls').getBoundingClientRect().bottom));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await assertHero(page,width,height);
  const body=await envelopePixels(page),[red,green,blue]=body.median;
  assert.ok(body.count>1000&&red>=130&&red<=180&&green<45&&blue<55,`Envelope body colour outside deep red range: ${JSON.stringify(body.median)}`);
  await page.screenshot({path:`output/christmas-card/${width}-01-idle.png`});
  await page.evaluate(()=>window.__christmasCardTest.captureAt(1));
  await page.locator('#open').click();
  await page.waitForFunction(()=>window.__christmasCardTest.snapshot!==null);
  const opening=await page.evaluate(()=>window.__christmasCardTest.snapshot.time);
  await page.screenshot({path:`output/christmas-card/${width}-02-opening.png`});
  await page.evaluate(()=>window.__christmasCardTest.captureAt(1.5));
  await page.waitForFunction(()=>window.__christmasCardTest.snapshot!==null);
  const mid=await page.evaluate(()=>window.__christmasCardTest.snapshot.time);
  await assertHero(page,width,height);
  await page.screenshot({path:`output/christmas-card/${width}-03-mid-flap.png`});
  await page.evaluate(()=>window.__christmasCardTest.captureAt(64/24+.3));
  await page.waitForFunction(()=>window.__christmasCardTest.snapshot!==null);
  const burstSnapshot=await page.evaluate(()=>window.__christmasCardTest.snapshot);
  assert.ok(opening<mid&&mid<burstSnapshot.time&&burstSnapshot.age>=.29&&burstSnapshot.age<.5);
  await page.screenshot({path:`output/christmas-card/${width}-04-burst.png`});
  await assertBurstPixels(page,burstSnapshot);
  await page.evaluate(()=>window.__christmasCardTest.release());
  await page.locator('#message:not([hidden])').waitFor();
  await page.waitForFunction(()=>document.querySelectorAll('#lines [data-pending]').length===0);
  assert.equal(await page.locator('#lines [data-pending]').count(),0);
  await assertMessageFits(page);
  await page.screenshot({path:`output/christmas-card/${width}-05-message.png`});
  // Longer representative English and Chinese copy remains visible without clipping.
  await page.locator('#lines p').evaluateAll(lines=>lines.forEach((line,i)=>line.textContent=['May your home be filled with laughter and warmth throughout this beautiful season,','and may every new day bring hope, kindness, and precious moments to share,','wishing you a joyful Christmas and a bright and peaceful new year.'][i]));
  await assertMessageFits(page);
  await page.locator('#language').click();assert.equal(await page.locator('html').getAttribute('lang'),'zh-Hans');
  await page.screenshot({path:`output/christmas-card/${width}-06-message-zh.png`});
  await page.locator('#lines p').evaluateAll(lines=>lines.forEach((line,i)=>line.textContent=['愿这个温暖的圣诞季为你和家人带来欢笑与幸福，','愿新的一年里每一天都充满希望、平安和美好，','愿我们珍惜相聚时光，拥有无尽的喜悦与祝福。'][i]));
  await assertMessageFits(page);
  await page.locator('#replay').click();assert.equal(await page.locator('#open').isVisible(),true);
  await page.waitForFunction(async()=>{const r=await navigator.serviceWorker.getRegistration('./');return !!r?.active});
  await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
  await context.setOffline(true);
  await page.reload();await page.locator('#open:not([disabled])').waitFor({timeout:30000});
  await page.locator('#open').click();await page.locator('#message:not([hidden])').waitFor();
  assert.deepEqual(errors,[]);
  console.log(`PASS ${width}x${height}: interaction, layout and offline reload`);
  await context.close();
 }
} finally {await browser.close();await new Promise(resolve=>server.close(resolve))}
