# Game performance report

## Method

Baseline commit: `38350b3933aa5d60bc7207d50b2e5577ae8781c3`. A clean Node 24.21.0 production build was served over unthrottled loopback on an Apple M4 macOS host. Chromium 156 ran headless using SwiftShader software WebGL. Phone sizes are touch/viewport emulation, not a physical mobile GPU. Each fresh context used rack seed 42, default placement and aim, and a real 75% break. The script classifies requestAnimationFrame intervals by game phase; a transition interval can include part of the preceding phase. Renderer instrumentation was disabled during the timing samples.

Reproduce with a built directory and a new empty output directory:

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH node scripts/audit-game-performance.mjs <build-dir> <empty-output-dir>
PATH=/opt/homebrew/opt/node@24/bin:$PATH node scripts/audit-game-performance.mjs <build-dir> <empty-output-dir> performance-quality
PATH=/opt/homebrew/opt/node@24/bin:$PATH node scripts/audit-game-performance.mjs <build-dir> <empty-output-dir> lifecycle-long
PATH=/opt/homebrew/opt/node@24/bin:$PATH node scripts/audit-game-paired-performance.mjs <baseline-build> <after-build> <empty-output-dir>
```

## Baseline

| Scenario | Fresh-context ready, ms | Moving p95 frame interval, ms | Canvas pixels |
| --- | --- | --- | --- |
| 1440×900, DPR 1 | 683 / 269 / 256 | 83.3 / 66.8 / 66.8 | 1020×620 |
| 390×844, DPR 1 | 341 / 217 / 264 | 50.1 / 50.1 / 50.1 | 348×484 |
| 390×844, DPR 3, existing 1.5 cap | 339 / 229 | 66.7 / 66.6 | 522×726 |

These numbers do not meet the proposed desktop/mobile p95 targets in this software-rendered environment. They are not a hardware-GPU, physical-phone or network-speed claim. The lower-DPR phone emulation averaged 39.2–40.6 ms per moving frame versus 49.2–49.5 ms with the 1.5 cap; it supports offering a user-selected resolution trade-off, but does not establish its effect on a particular phone.

The Game pack has 18 GLBs totaling 3,697,784 bytes, with no image or texture entries. Separate instrumentation counted one setup render at 135 calls / 97,208 triangles and one aiming render at 140 calls / 97,500 triangles. The counts are submissions, not GPU timings. Materials, models, colors and scale were not altered.

Six Game→Gallery cycles in one page produced 749 DOM nodes / 90 listeners after each 300 ms settling period; immediate samples sometimes retained 943 / 95. Forced-GC settled JS heap ranged from approximately 4.01 to 4.55 MiB over those six cycles. These short, CPU-side snapshots do not prove the absence of a sustained leak and exclude GPU memory. [Raw baseline results](../../output/playwright/game-audit/baseline/performance.json) include all samples, environment and limitations.

## After changes

The same default-quality audit produced these results. The mobile canvas is shorter than baseline because the layout now reserves space for the aim hint, so the two image areas are not identical.

| Scenario | Fresh-context ready, ms | Moving p95 frame interval, ms | Canvas pixels |
| --- | --- | --- | --- |
| 1440×900, DPR 1 | 1177 / 457 / 335 | 299.9 / 83.4 / 83.4 | 1020×620 |
| 390×844, DPR 1 | 415 / 237 / 250 | 50.1 / 50.1 / 50.1 | 348×456 |
| 390×844, DPR 3, Standard | 316 / 251 | 66.7 / 66.7 | 522×684 |
| 390×844, DPR 3, selected Performance | 513 / 237* | 50.1 / 50.1 | 348×456 |

*The Performance row's ready times were measured at the default quality before selecting Performance; they are not a Performance-mode startup comparison.* The desktop initial after sample was unusually slow, so a second warmed comparison alternated the two builds in one browser process. Moving p95 intervals were **83.4 / 166.6 / 66.7 ms before** and **133.3 / 66.7 / 66.7 ms after**. The rack, renderer and 1020×620 canvas matched, but both sets varied substantially; three pairs do not establish a statistically reliable improvement or regression. The original slow sample is retained rather than silently discarded. The two Performance frame samples used the actual Options control. None of these results establishes physical-phone or hardware-GPU speed. [Raw after](../../output/playwright/game-audit/after/performance.json), [Performance quality](../../output/playwright/game-audit/after/performance-quality.json) and [paired desktop](../../output/playwright/game-audit/after/paired-desktop.json) observations include the full conditions.

For a broader lifecycle observation, 30 Game→Gallery cycles completed before and after. At cycles 1 / 15 / 30, settled JS heaps were 4,214,580 / 5,150,940 / 5,201,904 bytes before and 4,228,648 / 5,173,268 / 5,222,148 bytes after; settled DOM nodes and listeners were 749 / 90 in each sampled cycle, with no held or pending game-owner lock. The later heap values were nearly flat over this bounded run. These observations do not cover GPU allocations or prove long-duration leak freedom. [Baseline](../../output/playwright/game-audit/baseline/lifecycle-30.json) and [after](../../output/playwright/game-audit/after/lifecycle-30.json) raw snapshots retain immediate and settled measurements.

## Remaining work

Physical iOS/Android frame pacing, GPU timing and memory, thermal behavior, network-constrained loading, shader stalls and longer repeated-session tests remain unverified. No instancing, LOD, compression or asset alteration is justified solely by the software-renderer measurements.
