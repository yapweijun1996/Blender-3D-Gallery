// Load from a remote inspector after opening the mall preview on the device.
const placements = new Map([['t-junction', 4], ['cross-junction', 5], ['enclosed-shop', 25]]);
const deviceFields = ['model', 'os', 'browser', 'refreshMode', 'power', 'thermal'];
const round = number => Number(number.toFixed(2));
let measuring = false;

export function summarizeFrameIntervals(intervals, elapsed) {
  const sorted = [...intervals].sort((a, b) => a - b);
  const percentile = p => round(sorted[Math.ceil(sorted.length * p) - 1]);
  return {
    samples: sorted.length, elapsedMs: round(elapsed), meanFps: round(sorted.length * 1000 / elapsed),
    p50Ms: percentile(.5), p95Ms: percentile(.95), maxMs: round(sorted[sorted.length - 1]),
    over50Ms: sorted.filter(ms => ms > 50).length,
  };
}

function checkedBuild(revision, runId) {
  const query = new URLSearchParams(location.search);
  if (!runId || query.get('qaRun') !== runId) throw new Error('Open the tab for the requested qaRun');
  const serverRevision = import.meta.env?.VITE_MALL_QA_REVISION;
  const markedRevision = query.get('qaRevision');
  if (!/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/.test(revision) ||
      (serverRevision || markedRevision) !== revision || (markedRevision && markedRevision !== revision)) {
    throw new Error('The expected full revision must match the Vite server or manually marked tab');
  }
  return { revision, provenance: serverRevision ? 'vite-server-environment' : 'tester-reported-url', runId };
}

function canvasSnapshot(canvas, wrap) {
  const box = canvas.getBoundingClientRect();
  const viewport = window.visualViewport;
  const left = viewport?.offsetLeft ?? 0, top = viewport?.offsetTop ?? 0;
  const width = viewport?.width ?? innerWidth, height = viewport?.height ?? innerHeight;
  const visibleWidth = Math.min(box.right, left + width) - Math.max(box.left, left);
  const visibleHeight = Math.min(box.bottom, top + height) - Math.max(box.top, top);
  const fraction = Math.max(0, visibleWidth) * Math.max(0, visibleHeight) / (box.width * box.height);
  const style = getComputedStyle(canvas);
  if (!(fraction >= .5) || !canvas.width || !canvas.height || style.visibility !== 'visible' || style.opacity === '0') {
    throw new Error('Center the visible canvas before sampling');
  }
  const state = wrap.inspectVisitor?.();
  if (!(state?.drawCalls > 0) || state.visitor || state.angle !== 0) {
    throw new Error('Use a rendered stationary view with closed doors and a fresh visitor state');
  }
  if (!Number.isSafeInteger(state.renderFrame) || state.renderFrame < 1) {
    throw new Error('The viewer must expose a valid renderer frame counter');
  }
  return {
    viewport: [round(width), round(height)], cssCanvas: [round(box.width), round(box.height)],
    backingCanvas: [canvas.width, canvas.height], dpr: devicePixelRatio, visibleFraction: round(fraction),
    drawCalls: state.drawCalls, renderFrame: state.renderFrame,
  };
}

export async function measureFloorFrames({ scene, evidence, device, revision, runId }) {
  if (!placements.has(scene)) throw new Error('Choose a T-junction, cross-junction or enclosed-shop scene');
  if (!['physical-phone', 'chromium-dry-run'].includes(evidence)) throw new Error('Declare the evidence type');
  if (evidence === 'physical-phone' && navigator.webdriver) {
    throw new Error('Use the dry-run label for an automated browser session');
  }
  if (!deviceFields.every(key => typeof device?.[key] === 'string' && device[key].trim())) {
    throw new Error('Record the device model, OS, browser, refresh mode, power and thermal state');
  }
  if (measuring) throw new Error('A sample is already running in this tab');
  const build = checkedBuild(revision, runId);
  const wrap = document.querySelector('#canvas-wrap'), status = wrap?.querySelector('#canvas-status');
  const canvas = wrap?.querySelector('canvas'), select = document.querySelector('#grid-layout');
  const roof = document.querySelector('#shop-roof');
  function checkScene() {
    if (document.visibilityState !== 'visible') throw new Error('The page left the foreground');
    if (!wrap?.isConnected || !canvas?.isConnected || !select?.isConnected ||
        status?.dataset.state !== 'ready' || wrap.dataset.view !== scene || select.value !== scene) {
      throw new Error('The requested scene must be selected, ready and visible in this tab');
    }
    if (scene === 'enclosed-shop' && roof?.getAttribute('aria-pressed') !== 'false') {
      throw new Error('Hide the enclosed-shop ceiling for this run');
    }
  }
  checkScene();
  canvasSnapshot(canvas, wrap);
  const warmupMs = evidence === 'physical-phone' ? 15000 : 300;
  const sampleMs = evidence === 'physical-phone' ? 30000 : 1500;
  measuring = true;
  try {
    return await new Promise((resolve, reject) => {
      const listeners = new AbortController();
      const options = { signal: listeners.signal, capture: true, passive: true };
      const invalid = reason => { cleanup(); reject(new Error(reason)); };
      const sceneChanged = () => invalid('The ready scene or its controls changed during the run');
      const observer = new MutationObserver(sceneChanged);
      observer.observe(wrap, { attributes: true, attributeFilter: ['data-view'] });
      observer.observe(status, { attributes: true, attributeFilter: ['data-state'] });
      select.addEventListener('change', sceneChanged, options);
      document.addEventListener('visibilitychange', () => invalid('The page changed foreground visibility'), options);
      window.addEventListener('pagehide', () => invalid('The page was left during the run'), options);
      canvas.addEventListener('webglcontextlost', () => invalid('The WebGL context was lost'), options);
      for (const event of ['click', 'keydown', 'pointerdown', 'wheel', 'scroll', 'resize']) {
        window.addEventListener(event, () => invalid('Input or viewport changed during the stationary run'), options);
      }
      window.visualViewport?.addEventListener('resize', () => invalid('The visible viewport changed'), options);
      const intervals = [];
      const warmupAt = performance.now();
      let frame, first, previous, priorRender, start, startedAt;
      let callbacksWithoutRender = 0, stalledMs = 0, longestStalledMs = 0;
      function cleanup() {
        cancelAnimationFrame(frame);
        listeners.abort();
        observer.disconnect();
      }
      function tick(now) {
        try {
          checkScene();
          if (now - warmupAt >= warmupMs) {
            if (first === undefined) {
              first = now;
              start = canvasSnapshot(canvas, wrap);
              startedAt = new Date().toISOString();
              priorRender = start.renderFrame;
            } else {
              const delta = now - previous;
              intervals.push(delta);
              const current = wrap.inspectVisitor().renderFrame;
              if (!Number.isSafeInteger(current) || current < priorRender) throw new Error('Renderer frame counter was lost or reset');
              if (current === priorRender) {
                callbacksWithoutRender++;
                stalledMs += delta;
                longestStalledMs = Math.max(longestStalledMs, stalledMs);
              } else { stalledMs = 0; }
              priorRender = current;
            }
            previous = now;
            if (now - first >= sampleMs) {
              const end = canvasSnapshot(canvas, wrap);
              const renderFrames = end.renderFrame - start.renderFrame;
              if (!renderFrames) throw new Error('The renderer submitted no new frames during the sample');
              cleanup();
              resolve({
                evidence, scene, floor2mPlacements: placements.get(scene), build, startedAt, warmupMs, sampleMs,
                device: Object.fromEntries(deviceFields.map(key => [key, device[key]])),
                deviceIdentity: evidence === 'physical-phone' ? 'operator-reported' : 'automated-desktop',
                start, end, renderFrames, callbacksWithoutRender, longestNoRenderMs: round(longestStalledMs),
                ...summarizeFrameIntervals(intervals, now - first),
              });
              return;
            }
          }
          frame = requestAnimationFrame(tick);
        } catch (error) { cleanup(); reject(error); }
      }
      frame = requestAnimationFrame(tick);
    });
  } finally { measuring = false; }
}
