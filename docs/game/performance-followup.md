# Game performance follow-up

The newer [loading diagnosis and paired comparison](loading-root-cause.md) explains the abort events and cold-start limit; [release readiness](release-readiness.md) records final integration checks. The measurements below remain scoped to their original revision and were not reclassified as a post-fix speedup.

Observed on 2026-11-05 (Asia/Singapore), using checkout `d19606eb65962b66a0fc07be5b5f3c06ec6ef745` and local production build `7c832c4d674222d3`. The host is an Apple M4 Mac, macOS 27.0.1, Node 24.21.0. This is a local follow-up; it is not deployment or physical-phone evidence.

## Renderer identification

Two headless browser profiles were tested without the script supplying a GPU-forcing flag. Playwright's default `--enable-unsafe-swiftshader` argument was explicitly removed in both. Chromium's CDP command-line query was unavailable because `--enable-automation` was not set, so the complete actual browser command line was not independently obtained.

| Browser | Observed unmasked WebGL2 renderer | Browser GPU status | Interpretation |
| --- | --- | --- | --- |
| Playwright Chromium 156.0.8078.4, headless shell | `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (LLVM 10.0.0) (0x0000C0DE)), SwiftShader driver)` | WebGL and GPU compositing reported unavailable/software | Software renderer. |
| System Chrome 156.0.8078.80, headless | `ANGLE (Apple, ANGLE Metal Renderer: Apple M4, Unspecified Version)` | WebGL and GPU compositing reported enabled | Browser reports the host Apple M4 hardware renderer. |

Both profiles created a WebGL2 context with `failIfMajorPerformanceCaveat: true`; that check alone did not distinguish SwiftShader here. The renderer string and CDP GPU metadata were therefore also used. The actual game canvas in all six hardware samples reported the same Apple M4 renderer as the system-Chrome probe.

## Frame pacing on the reported host GPU

Each sample used a fresh browser context, a seeded rack (`42`), default cue placement and aim, and a real shot at 75% power. The same rack signature was observed in every sample. requestAnimationFrame intervals were classified by game phase over six seconds after motion began. Each moving sample contained 357 intervals; individual transition intervals can include work from the previous phase.

| Scenario | Canvas pixels | Ready, ms | Moving-frame p95, ms |
| --- | --- | --- | --- |
| Desktop 1440×900, DPR 1 | 1020×576 | 483.1 / 403.0 / 260.2 | 16.7 / 16.8 / 16.7 |
| Mobile viewport/touch emulation 390×844, DPR 1 | 356×364 | 250.0 / 237.0 / 306.5 | 16.8 / 16.8 / 16.7 |

Moving-frame means were approximately 16.7 ms in these six runs. These are browser frame-pacing observations on the same Mac GPU, not GPU timers or physical-phone measurements. The proposed p95 targets are not declared passed: some rounded values are 16.8 ms and the sampling environment and reference device have not been agreed.

## Controlled cold network observation

System Chrome was configured through CDP for 100 ms latency, 4,000,000 bit/s download and 1,000,000 bit/s upload. Each run used a fresh desktop context, blocked service workers and disabled the browser cache; the local server itself was loopback and CPU speed was not throttled. Time from navigation to the game's ready signal was **9,555.5 / 9,549.3 / 9,537.8 ms**.

All three runs recorded 18 GLB Resource Timing entries with nonzero transfer size and no controlling service worker. Each entry's encoded body size matched its corresponding file size in the generated game-pack manifest: 3,697,784 bytes total. This supports that the cold-state conditions and expected byte counts were observed; Resource Timing does not independently verify response hashes. CDP throttling on loopback is a simulated profile, not field latency, throughput or a real phone.

## Unresolved aborted-request events

The original samples also recorded `net::ERR_ABORTED` request failures for GLBs: desktop hardware samples recorded 1 / 2 / 1, mobile emulation 5 / 0 / 0, and the three throttled runs 16 / 18 / 15. These events are retained in the raw sample entries; the original top-level `errors` array was empty because the harness did not aggregate per-sample failures. Its original exit code was 0 only for the sampling process; it does not establish that performance or network checks passed.

One separate throttled diagnostic recorded 18 GLB request events and 18 `net::ERR_ABORTED` events **during loading**, before the game reported ready at 9,615 ms; it recorded 18 GLB Resource Timing entries. It did not establish why Playwright/CDP emitted failures while the app's loaders resolved. Browser teardown is ruled out for those diagnostic events; a loader, transport or instrumentation cause remains unverified. Future investigation should correlate Chrome DevTools request IDs and response completion with a controlled direct-fetch comparison and independently verify response hashes before treating the events as harmless or claiming a product defect.

The follow-up script was subsequently amended to label active versus teardown events and return a nonzero exit code when active sample errors are observed. This error-reporting amendment passed Node 24 syntax checking but was not rerun; the original JSON remains unchanged.

## Evidence and reproduction

The [original hardware and network samples](../../output/playwright/pr1-followup/hardware-performance.json) and [abort event timeline](../../output/playwright/pr1-followup/abort-diagnostic.json) are retained separately. Screenshots: [desktop](../../output/playwright/pr1-followup/hardware-desktop.png) and [mobile emulation](../../output/playwright/pr1-followup/hardware-mobile-emulated.png).

With a current production build and a new, nonexistent output directory:

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH node scripts/audit-game-hardware-followup.mjs dist /tmp/game-pr1-followup/performance-new
```

The script first probes Playwright Chromium and system Chrome without forced SwiftShader. If neither reports hardware, it also tries an isolated headed system-Chrome probe; it measures hardware gameplay only for a verified browser-reported hardware renderer. A software fallback may be used solely for the independently labeled network observation.

Physical iOS/Android, device GPU timing and memory, real network conditions, long-duration thermal behavior and the cause or user impact of the aborted-request events remain unverified. No application code, model asset, production service or deployment was changed by this follow-up.
