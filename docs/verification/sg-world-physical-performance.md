# Singapore Open World phone performance check

Physical iPhone and Android results are **NOT RUN**. A three-second iPhone 15 viewport check in Chromium with SwiftShader verified that the live route exposes the sampler's inputs, touch controls and build ID. That check measured build `be41f84176b2759f` while the starting tiles were still loading.

Open [Singapore Open World](https://yapweijun1996.github.io/Blender-3D-Gallery/?page=sg-world) on the physical phone. On iPhone, turn on Web Inspector in Safari's Advanced settings and select the phone's tab from the Mac Safari Develop menu. On Android, enable USB debugging, connect the phone, and inspect the tab from `chrome://inspect/#devices` in desktop Chrome. Keep the phone tab visible, disable screencasting and leave profiling, network and CPU throttling off. [Safari Web Inspector](https://webkit.org/web-inspector/enabling-web-inspector/) · [Chrome remote debugging](https://developer.chrome.com/docs/devtools/remote-debugging/)

1. Record device model, OS and browser versions, orientation, refresh mode, power mode and whether the phone is warm. Use the same conditions across repeats.
2. Reload before each run to start on Bayfront Avenue near Marina Bay Sands. Select **Proton Saga**, set the **Time** button to 13:00 and leave gameplay running. Check `document.querySelector('.world-stage[data-state="ready"]')?.inspectWorld()` in the console. Wait until `loading.pending`, `loading.ready` and `loading.failed` are zero and `people` is greater than zero, then let the scene warm up for 15 seconds. For repeat runs, use the same audio setting.
3. Paste the sampler below into the remote console. For the stationary run, call `measureWorld('bayfront-parked')` and leave the controls alone for 30 seconds. For the driving run, call `measureWorld('bayfront-southbound')`. After the three-second lead, use ▲ and ◀/▶ to follow Bayfront Avenue in the direction the car initially faces. Stay in the left lane around 30 km/h, use ■ to brake for traffic, and continue for the full 30 seconds. Record stops, crashes and route deviations with the output.
4. Repeat each scenario three times and retain every valid run. Report average FPS, p50/p95 frame intervals, longest gap and intervals over 50 ms. Include the start/end draw calls, triangles, tile counts, and render scale as scene snapshots. The [game plan](../singapore-game-plan.md) proposes 30 FPS, 150 draw calls and 300,000 visible triangles for an iPhone. The minimum supported device remains open.

```js
async function measureWorld(scenario) {
  const stage = document.querySelector('.world-stage[data-state="ready"]');
  if (!stage?.inspectWorld || document.hidden) {
    throw new Error('Open the ready world in the foreground');
  }
  const response = await fetch(new URL('build-info.json', location.href), { cache: 'no-cache' });
  if (!response.ok) throw new Error('Build information unavailable');
  const { build } = await response.json();
  if (!build) throw new Error('Build identifier unavailable');

  const snapshot = () => {
    const { x, z, speed, vehicleId, hour, calls, triangles, tiles, loading, traffic, people } = stage.inspectWorld();
    const canvas = stage.querySelector('canvas:not(.drive-minimap)');
    const width = stage.getBoundingClientRect().width;
    return {
      x, z, speedMps: speed, vehicleId, hour, calls, triangles, tiles, loading, traffic, people,
      renderScale: canvas && width > 0 ? canvas.width / width : null,
    };
  };

  const deltas = [];
  const round = value => Number(value.toFixed(2));
  const result = await new Promise((resolve, reject) => {
    let lead, frame, first, previous, start;
    function cleanUp() {
      clearTimeout(lead);
      cancelAnimationFrame(frame);
      document.removeEventListener('visibilitychange', checkForeground);
      removeEventListener('pagehide', abort);
    }
    function abort() {
      cleanUp();
      reject(new Error('Discard this run because the world tab was hidden or left'));
    }
    function checkForeground() {
      if (document.hidden) abort();
    }
    function tick(now) {
      if (document.hidden || !stage.isConnected) return abort();
      if (first === undefined) {
        first = now;
        start = snapshot();
      } else {
        deltas.push(now - previous);
      }
      previous = now;
      const elapsed = now - first;
      if (elapsed < 30000) {
        frame = requestAnimationFrame(tick);
        return;
      }
      const end = snapshot();
      cleanUp();
      const sorted = deltas.sort((a, b) => a - b);
      const percentile = p => round(sorted[Math.ceil(sorted.length * p) - 1]);
      resolve({
        scenario, build, measuredAt: new Date().toISOString(), viewport: [innerWidth, innerHeight],
        dpr: devicePixelRatio, coarsePointer: matchMedia('(pointer: coarse)').matches,
        samples: sorted.length, elapsedMs: round(elapsed), meanFps: round(sorted.length * 1000 / elapsed),
        p50Ms: percentile(0.5), p95Ms: percentile(0.95), maxMs: round(sorted[sorted.length - 1]),
        over50Ms: sorted.filter(ms => ms > 50).length, start, end,
      });
    }
    document.addEventListener('visibilitychange', checkForeground);
    addEventListener('pagehide', abort, { once: true });
    if (document.hidden || !stage.isConnected) return abort();
    console.log('30-second sample starts in 3 seconds');
    lead = setTimeout(() => {
      console.log('Sample started');
      frame = requestAnimationFrame(tick);
    }, 3000);
  });
  console.log(JSON.stringify(result));
  return result;
}
```

The `requestAnimationFrame` intervals measure browser frame pacing with the inspector attached. They do not measure GPU execution time, network load time, or sustained thermal performance. Render scale is estimated from canvas backing width and stage width.
