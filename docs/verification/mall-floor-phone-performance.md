# Measure repeated mall floors on a phone

Physical Android and iPhone results are pending. This stationary test measures the intervals between foreground browser animation callbacks while the mall renderer is active. It cannot measure GPU execution or certify which frames the display presented.

| Preview scene | Installed 2 m floor modules | Workload |
| --- | ---: | --- |
| `t-junction` | 4 | Three floor arms |
| `cross-junction` | 5 | Four floor arms |
| `enclosed-shop` | 25 | Floor and approach, walls and closed entrance, ceiling hidden, visitor unloaded |

The counts come from the authored junction and room layouts. The shop batches static geometry. Each result records the renderer's draw calls separately.

## Serve a known revision

Use the same clean checkout and installed lockfile for every repeat. In its terminal, verify that `git status --short` is empty and record `git rev-parse HEAD`. Start the regular preview from that checkout. Keep the source and server fixed throughout the session.

```sh
VITE_MALL_QA_REVISION="$(git rev-parse HEAD)" npm run dev -- --port 5173 --strictPort
```

On the phone open `http://127.0.0.1:5173/mall-modules-preview/?view=t-junction&qaRun=floor-A1` for the USB-forwarded Android example. Give each run a distinct label and pass that same label and the observed full revision to the sampler. The QA module compares its serving Vite environment with the expected revision. If the server was started without the environment variable, add `&qaRevision=FULL_REVISION` to the URL after checking the serving checkout. The server value records its startup environment. The result identifies the manual fallback as `tester-reported-url`.

- **Android over USB.** Enable USB debugging, unlock the phone, approve the debugging prompt, and find its serial in `adb devices -l`. Run `adb -s SERIAL reverse tcp:5173 tcp:5173`. Open the URL in Chrome **on the phone**. On the computer select that phone's tab in `chrome://inspect/#devices` and disable screencasting. Remove the forwarding afterwards with `adb -s SERIAL reverse --remove tcp:5173`. [Chrome remote debugging](https://developer.chrome.com/docs/devtools/remote-debugging/)
- **iPhone Safari.** Put the Mac and iPhone on the same trusted LAN. Start the same command with `--host MAC_LAN_IP` appended and replace `127.0.0.1` in the phone URL with that IP. Enable Safari Web Inspector on iPhone in Safari's Advanced settings. Connect via USB, unlock and trust the Mac. Enable web developer features in Mac Safari's Advanced settings and choose the physical phone and its tab in the Develop menu. USB provides the inspection channel and the LAN serves the page. [Safari Web Inspector](https://webkit.org/web-inspector/enabling-web-inspector/)

## Collect three runs per scene per phone

Reload the scene URL before each run. Use its default camera, keep the portrait orientation and canvas centered, and leave page controls untouched. In the remote console run `document.querySelector('#canvas-wrap canvas').scrollIntoView({block:'center', behavior:'instant'})` after the preview is visible. Let the scroll settle. Disable inspector profiling, screencasting and artificial network or CPU throttling. The operator identifies the physical device. Record actual model, OS, browser version, refresh setting, power mode/charging and thermal condition. Use `unknown` for conditions that cannot be observed.

Replace the example values below. Paste the block in the inspected **phone tab** and keep it in the foreground for the 15 s warm-up and 30 s measurement.

```js
import('./qa/measure-floor-frames.js').then(({ measureFloorFrames }) => measureFloorFrames({
  evidence: 'physical-phone',
  scene: 't-junction',
  runId: 'floor-A1',
  revision: 'PASTE_FULL_COMMIT_FROM_THE_SERVING_CHECKOUT',
  device: {
    model: 'PHONE MODEL', os: 'OS VERSION', browser: 'BROWSER VERSION',
    refreshMode: 'REFRESH SETTING', power: 'POWER MODE AND CHARGING', thermal: 'COOL / WARM / UNKNOWN',
  },
})).then(result => console.log(JSON.stringify(result))).catch(error => console.error(error.message))
```

Save each valid JSON result, including slow runs. Rerun a rejected sample under a new label. The sampler checks the selected control, rendered scene, ready state, foreground page and visible canvas. Changing the scene, leaving the tab, moving a control or resizing the viewport during sampling invalidates it. Keep hardware serials, account names and LAN addresses out of saved results.

Compare each phone and scene using the per-run mean FPS, nearest-rank p50 and p95 frame intervals, maximum interval, count above 50 ms, measured duration and sample count. Also retain the CSS and backing-buffer sizes, device pixel ratio, start/end draw calls, floor placements and source revision. The Three.js render-frame counter also records how many render passes ran. Intervals with no new render remain in the callback statistics and are counted separately, including the longest consecutive span. A fully stalled renderer invalidates the run. Three runs characterize short, stationary frame pacing on that particular device.

## Exercise the sampler on desktop Chromium

With the local preview server above running and Playwright Chromium installed, run the command below. It loads the real floor GLB and exercises all three assemblies and rejection paths with short timings. It labels the output `chromium-dry-run` and reports zero physical runs.

```sh
node scripts/test-mall-floor-phone-sampler.mjs http://127.0.0.1:5173/mall-modules-preview/ "$(git rev-parse HEAD)"
```
