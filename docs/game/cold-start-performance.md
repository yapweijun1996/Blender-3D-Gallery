# Production Game cold-start audit — 2026-11-06

## Scope and identity

The repository baseline was `d932f985c01dbdca69f2ef651f00937522986808`, with local production build `d5a0777b42aace5e`. Its 123 emitted file hashes were frozen before measurement; see [build hashes](../../output/playwright/cold-start-20261106/baseline-d932-build-hashes.json). During the first attempt, production changed from `c0b0543ff2f7cf51` to `d5a0777b42aace5e`; the script stopped and preserved that [interrupted attempt](../../output/playwright/cold-start-20261106/version-change-interrupted.json). The mixed-identity observation is not included below.

The complete production audit then used build `d5a0777b42aace5e`. Each visit checked a cache-busted production `build-info.json` before and after, and the browser's actual entry module matched the frozen local build. Before the run, an independent GET of the production document was byte-identical to the local `index.html`. The online and local manifests listed the same 18 GLB paths, sizes and SHA-256 hashes. In a separate instrumented Game visit, all 18 actually consumed GLB bodies also matched the online manifest. The timed visits did not capture or hash response bodies. Production remained read-only throughout.

## Observed production delivery

Real GET responses were HTTP/2 and carried `Content-Encoding: gzip`, `Vary: Accept-Encoding`, `Cache-Control: max-age=600`, and content type, length, age and ETag headers. The following example is from a throttled production sample; values are measured encoded response-body bytes and decoded resource bytes, not estimates from file extensions.

| Resource | Encoded bytes | Decoded bytes | Content type |
| --- | ---: | ---: | --- |
| Entry JavaScript | 21,191 | 100,373 | `application/javascript` |
| Shared Three/OrbitControls chunk | 158,988 | 641,223 | `application/javascript` |
| Game page chunk | 15,983 | 43,023 | `application/javascript` |
| Table GLB | 41,893 | 417,656 | `model/gltf-binary` |
| All 18 Game GLBs | 1,220,024 | 3,697,784 | `model/gltf-binary` |

In each of the ten formal samples, all 18 expected GLBs returned HTTP 200 and their decoded lengths matched the manifest; there were no page errors or GLB request failures. [Raw samples](../../output/playwright/cold-start-20261106/production-d5a-samples.json) retain selected response headers, CDN age, individual resource timing, initiators, request IDs and protocols. They also retain the separate response-byte diagnostic and normal Service Worker journeys. A [desktop screenshot](../../output/playwright/cold-start-20261106/production-desktop.png) shows the ready scene.

## Ready timing

Tests used system Chrome 156.0.8078.80 on an Apple M4 macOS host with the actual `ANGLE Metal Renderer: Apple M4`, a 1440 × 900 viewport at DPR 1 and a 990 × 569 drawing buffer. Each formal sample used a new browser context, disabled the browser HTTP cache, blocked Service Workers, and fetched the real hosted resources. Five unthrottled and five 100 ms / 4 Mbps down / 1 Mbps up CDP page-throttled visits alternated sequentially in one browser process. Each number is navigation-to-Game-ready wall time in milliseconds.

| Profile | Median | Range | Individual samples in execution order |
| --- | ---: | ---: | --- |
| Real network, no synthetic throttle | 282 | 253–1,622 | 1,622 / 282 / 253 / 304 / 265 |
| Real hosting, synthetic page network throttle | 3,429 | 3,414–3,433 | 3,429 / 3,433 / 3,419 / 3,429 / 3,414 |

A fresh context and disabled HTTP cache do not reset DNS, CDN edge cache, all connection state, or other host activity. The slow first unthrottled observation is preserved; its cause has not been established. These results describe a headless desktop and a synthetic network profile, not a physical phone or a population-level production latency. The provisional 3-second desktop target was not met in this specific throttled profile; the physical-mobile target remains untested. Host CPU readings in the raw report include post-ready observation and, for the worker-enabled cold sample, the Service Worker installation wait; they do not isolate the timed interval.

For the five throttled visits, the first GLB began around 795–821 ms and the last finished around 3,397–3,416 ms, giving a 2,595–2,603 ms GLB span. The actual 1,220,024 encoded GLB bytes alone require approximately 2.44 seconds at an ideal shared 4 Mbps, before latency and other resources. The prior local report's approximately 7.4-second figure used uncompressed GLBs; it must not be applied to this production gzip transfer.

An independent, instrumented real-network visit recorded the final `18/18` model-progress update at 252.3 ms, the first following WebGL draw invocation at 255.3 ms, and a frame observing ready at 275.7 ms. These are navigation-relative diagnostic times, not formal performance samples; draw invocation is not GPU completion. The existing architecture waits for the dynamically imported Game/shared Three.js modules and saved-state setup before starting its four model-loading workers.

## Service Worker observations

The code registers the worker immediately; its install verifies `build-info.json` and sequentially re-fetches and verifies the shell. One ordinary, unthrottled fresh-context visit showed 29 worker-associated requests (the worker script, build identity and 27 shell resources). In that one observation the Game was ready at approximately 262 ms, while the worker's first shell re-fetch began approximately 362 ms after the first browser request. This sample does not show the shell downloads delaying readiness, and one visit cannot exclude competition on slower networks.

A subsequent new page in the same context had an active worker controller and reused warm browser state. The optional offline Game pack was not prepared; its 18 GLB requests still appeared as worker fetches. This was one qualitative warm revisit, not a cold-versus-warm speed comparison or offline verification. The raw report's methodology calls this a “warm reload”; the implementation actually closes the first page and opens a new page within the same browser context. The script wording has been corrected for future runs. No page-only CDP throttle was applied to the worker-enabled visits: it would not necessarily throttle worker-origin traffic.

## Decision and follow-up

No production optimization has been demonstrated or applied by this audit. The 4 Mbps GLB phase is already close to the observed compressed-byte transfer floor. At the audit decision point, worker-count changes and model preloads had not been tested. The bounded worker experiment below followed this measurement contract: compare candidate and baseline with byte-identical assets, the same gzip/HTTP/2 and cache conditions, at least five alternating observations per side, plus real cancellation, failure/retry and offline-pack regression tests. Treat worker-install scheduling as a separate question and measure worker and page traffic under a genuinely shared bottleneck. Do not compare the online build against an uncompressed HTTP/1 loopback server as a speedup claim.

Reproduce the production audit with pinned dependencies, Node 24 and system Chrome:

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH node scripts/audit-game-production-startup.mjs /tmp/new-production-audit
```

The output directory must not already exist. A changed production build stops the run rather than mixing observations. Results depend on the live site and network; inspect the recorded identities and headers before comparing them with this audit.

## Bounded worker-count experiment

A temporary candidate changed only the Game model-loading worker limit from four to six. The candidate source was verified against commit `d932f985c01dbdca69f2ef651f00937522986808` as a single literal change, and the other 18 Game/source files matched the restored source. Both frozen builds had the same 18 GLB paths, lengths and SHA-256 hashes. The candidate's [source patch](../../output/playwright/cold-start-20261106/concurrency-candidate.patch), [source and 123 emitted-file hashes](../../output/playwright/cold-start-20261106/candidate-build-hashes.json), and [build log](../../output/playwright/cold-start-20261106/candidate-build.log) are retained. This source comparison was made after building and is not independent build attestation.

During candidate construction, the first build was accidentally run in the working directory, replacing its ignored `dist`; the result was moved to the temporary candidate directory, and the working `dist` was restored from the untouched frozen baseline. All 123 restored files were checked against the baseline hashes. The baseline build was `d5a0777b42aace5e`; the candidate was `4e37e843b4b1ee65`. No production deployment occurred.

The builds were served by the same local TLS/HTTP/2 server with gzip level 6, using Chrome 156 on Apple M4 Metal, a 1440 × 900 viewport, DPR 1 and an identical 990 × 569 canvas. Each visit used a fresh context, disabled browser cache, blocked Service Workers and emulated 100 ms latency / 4 Mbps down / 1 Mbps up. Each of 20 visits completed 18/18 GLBs with HTTP 200, HTTP/2, gzip and expected encoded/decoded lengths, with no recorded errors. The temporary TLS key was generated outside the repository and removed after the run.

Local gzip encoded the GLBs to 1,209,980 bytes, 0.82% less in aggregate than the measured production responses; individual files also differed. This is a representative local test, not a deployed-candidate or physical-phone measurement. Host CPU counters were measured across navigation-to-ready only and include the browser and other host activity.

| Order | Workers | Ready median | Range | Samples in execution order |
| --- | ---: | ---: | ---: | --- |
| Four then six | 4 | 3,390.93 ms | 3,383.37–3,392.65 ms | 3,390.93 / 3,392.39 / 3,383.37 / 3,383.63 / 3,392.65 |
| Four then six | 6 | 3,353.09 ms | 3,347.73–3,367.50 ms | 3,367.50 / 3,363.29 / 3,353.09 / 3,349.24 / 3,347.73 |
| Six then four | 4 | 3,380.47 ms | 3,365.79–3,392.03 ms | 3,365.79 / 3,374.34 / 3,380.47 / 3,388.03 / 3,392.03 |
| Six then four | 6 | 3,353.74 ms | 3,344.16–3,431.71 ms | 3,431.71 / 3,344.16 / 3,353.74 / 3,350.54 / 3,365.11 |

The first order's per-pair six-minus-four differences were −23.43, −29.10, −30.28, −34.39 and −44.92 ms. The reversed order produced +65.92, −30.17, −26.73, −37.48 and −26.92 ms; the slower first six-worker observation is retained. Median differences were approximately 37.8 ms and 26.7 ms, respectively, or roughly 1.1% and 0.8% of the corresponding four-worker median. The two ranges overlap in the reversed run, and physical-mobile performance and peak-memory effects were not measured. These results show a small difference under these local conditions; they do not establish its size or direction on production networks and devices.

The six-worker candidate was **not retained**: the small local median difference did not justify an unmeasured concurrency and memory trade-off. The Game scene source was restored byte-for-byte to the four-worker baseline; existing gameplay and offline contracts were not changed. See the [four-first raw result](../../output/playwright/cold-start-20261106/concurrency-http2-4-vs-6.json) and [six-first raw result](../../output/playwright/cold-start-20261106/concurrency-http2-6-vs-4.json) for all requests, samples, host load and gzip comparisons.

Reproduce with frozen builds, system `openssl`, and separate new output directories. The script removes its temporary test key. Use `four-first` and `six-first` to select the pair order:

```sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH node scripts/audit-game-concurrency-http2.mjs \
  /path/to/four-worker-dist /path/to/six-worker-dist \
  output/playwright/cold-start-20261106/production-d5a-samples.json /tmp/new-concurrency-audit four-first
```

The two build logs remove a trailing space from the Vite warning line. Repository JSON evidence copies replace only the local worktree path in the interrupted-run stack and the temporary baseline/candidate directory names in paired results with placeholders. [Normalization hashes](../../output/playwright/cold-start-20261106/artifact-normalization.json) identify both original and published copies; original files remain in `/tmp/game-cold-start-production-audit-01/`, `/tmp/game-cold-start-concurrency-http2-01/` and `/tmp/game-cold-start-concurrency-http2-reversed/` on the measurement host.

## Independent regression and disposition

After rejecting the candidate, the primary agent rebuilt the restored source. Build `d5a0777b42aace5e` reproduced all 123 frozen output files byte-for-byte; there is no application, public asset, dependency or deployment-workflow diff. The primary agent independently recomputed both paired summaries from the 20 observations and checked all 360 GLB response records for HTTP 200, completed HTTP/2 and gzip responses. See [verification summary](../../output/playwright/cold-start-20261106/regression/verification-summary.json).

| Executed check | Result | Evidence |
| --- | --- | --- |
| `npm run build` | Exit 0; 123 baseline hashes match | [Log](../../output/playwright/cold-start-20261106/regression/build.log) |
| `npm test` | 79 passed; 0 failed; 0 skipped | [Log](../../output/playwright/cold-start-20261106/regression/unit.log) |
| `node scripts/test-game-loading.mjs` | 5 passed: aborted/truncated recovery, valid extras, intercepted and real-network cancellation | [Log](../../output/playwright/cold-start-20261106/regression/loading.log) |
| `npm run test:game-responsive` | 20 placement/aiming cases over 10 viewport sizes; no recorded errors | [Results](../../output/playwright/cold-start-20261106/regression/responsive-results.json) |
| `npm run test:browser` | 45 groups passed, including keyboard focus, reduced motion, touch, repeated navigation, WebGL recovery, Gallery previews/downloads and WebKit shot smoke; no recorded errors | [Results](../../output/playwright/cold-start-20261106/regression/game-browser-results.json), [log](../../output/playwright/cold-start-20261106/regression/game-browser.log) |

The primary agent visually inspected [390 × 844](../../output/playwright/cold-start-20261106/regression/390x844-aiming.png) and [1440 × 900](../../output/playwright/cold-start-20261106/regression/1440x900-aiming.png) aiming screenshots; controls and the scene fit without visible horizontal overflow. A [768 × 1024 screenshot](../../output/playwright/cold-start-20261106/regression/768x1024-aiming.png) is also retained. These are browser-emulated layouts, not physical-device certification or a complete screen-reader audit. The build retains its existing >500 kB decoded Three.js chunk warning; the actual production encoded chunk size is recorded above.

**Disposition: NEEDS REVIEW, evidence-only delivery.** No startup runtime optimization was retained, and no production improvement is claimed. The compressed GLB transfer is the measured limiting interval in the specified synthetic network profile; the unexplained slow first real-network visit, physical-mobile performance, peak memory, globally throttled Service Worker contention and full assistive-technology coverage remain unverified. Asset licensing remains owner-deferred; no model, appearance or download behavior changed. No merge, deployment or KB content update was performed for this follow-up. Rollback of this delivery requires reverting only its audit scripts, evidence and documentation; application output already matches the original baseline.
