# Game GLB loading: diagnosis and verification

## Finding and scope

On macOS Apple M4, system Chrome 156.0.8078.80 reported `net::ERR_ABORTED` for the original Game loader even when the Game became ready. The behavior was reproduced with cache disabled, a fresh context, service workers blocked, and CDP network emulation at 100 ms latency, 4 Mbps down and 1 Mbps up. The diagnostic used a loopback server; it is not a production-network or physical-mobile result.

Two separate problems were identified:

1. With the pinned Three.js 0.187.0 `FileLoader` stream-wrapper path, this Chrome/CDP environment reported aborted requests after all model bytes had been read. A test of the actual original Game captured all 18 responses on the existing stream reader: every captured byte length and SHA-256 matched both its local GLB and `game-pack.json`. The same 18 errors occurred with observation disabled. A direct native `fetch().arrayBuffer()` control produced `Network.loadingFinished` instead. This establishes a reproducible association with the wrapper in this environment, not the internal Chromium cause and not a rule that all aborts are harmless.
2. Navigating away during loading did not promptly cancel original Game asset requests. In the baseline cancellation test, all four originally in-flight GLBs finished receiving their complete expected bytes after leaving; the test expecting a partial-transfer cancellation failed after 15 seconds. With the candidate, the four in-flight GLBs had received zero of their expected bytes when CDP reported `net::ERR_ABORTED`; matching Playwright request failures were observed. The test checks that no queued request starts after leaving. This confirms client-side cancellation in the tested conditions; it does not measure when the server releases its connection.

The independent mechanism fixture compared the same 417,656-byte table GLB using: direct fetch, a `Request` with an `AbortSignal.any` signal, a manually wrapped response stream with and without that signal, pinned Three.js `FileLoader`, and actual `GLTFLoader`. Both direct variants finished; both manual wrappers and both Three.js loaders reported `ERR_ABORTED`. The byte-returning paths all matched the table's local SHA-256 `078e2645a2ca520b1724d72473d74627aecc94bdf7157f501539c1f0cb1b130f`; `GLTFLoader` produced a 52-mesh scene. Another control reproduced the direct/loader distinction under both `Content-Length` and chunked framing. No `Response.clone()`, stream tee, or extra reader was used for the observed Game requests.

The Game-only change reads the response using native `fetch` and passes the same bytes and original URL base to `GLTFLoader.parseAsync`. A scene-owned abort controller and loading manager cancel its own work when the route is disposed or another worker fails. The existing four-worker limit remains; disposed/aborted checks prevent new queued requests and discard any model that finishes parsing late. HTTP failures and invalid GLBs still use the existing recovery UI. Gallery's shared loading path and the GLB assets are unchanged.

## Evidence

- [Original Game and framing controls](../../output/playwright/game-loading-fix/loading-baseline-cdp.json): original full Game, observed and unobserved, each emitted 18 loading failures before teardown; observed 18/18 hashes matched.
- [Isolated stream mechanism](../../output/playwright/game-loading-fix/loading-mechanism.json): actual CDP request IDs and the six controls above.
- [Candidate Game and framing controls](../../output/playwright/game-loading-fix/loading-candidate-cdp.json): candidate full Game, observed and unobserved, each emitted 18 loading-finished events and no loading failures before teardown; observed 18/18 hashes matched. This extra instrumentation was not included in timed samples.
- [Baseline cancellation output](../../output/playwright/game-loading-fix/loading-baseline-cancellation.log) and [candidate cancellation output](../../output/playwright/game-loading-fix/loading-candidate-cancellation.log): request IDs, received/expected bytes, Playwright failures and exit codes. These tests used Playwright's bundled headless Chromium with the repository's SwiftShader options, a 300 ms / 4 Mbps / 1 Mbps emulated profile, and cache disabled.

The focused browser suite additionally exercised an actual `route.abort()` while staying on Game and successfully retrying, a truncated GLB and retry, a valid GLB with extra metadata, and leaving/re-entering while four intercepted requests were held. Those four candidate cases passed before the final formatting of the test file; the passthrough cancellation case was rerun after it. Full integrated checks are recorded separately by the parent review.

## Cold-start comparison

A frozen baseline was built from `4b6bd494c170581e934bf6adb6539a17a5123c33` (same app source as main `284a192`); its build ID was `87423ed187d3babe`. The candidate build ID was `df37c64681102b95`, from `4f20912bbddfaf7ecf9964646e7c46b1cc3c1fa4` plus the uncommitted Game loader change. The candidate also contains the intervening narrow-screen CSS fix, so the builds differ in more than the loader. All 18 asset files in both frozen builds matched their manifests and one another by SHA-256 and length.

The paired run used one Chrome 156.0.8078.80 process with the actual `ANGLE Metal Renderer: Apple M4`, one loopback server switching frozen roots, 1440 × 900 viewport, DPR 1, 1020 × 586 drawing buffer, fresh context per sample, no service worker, disabled cache, 100 ms latency, 4 Mbps down and 1 Mbps up. CPU was not throttled. Baseline and candidate alternated five times; all ten samples reached Game ready with 18 transferred GLBs and expected response byte lengths.

| Build | Ready median | Range | Samples |
| --- | ---: | ---: | --- |
| Baseline | 9,587 ms | 9,523–9,694 ms | 5 |
| Candidate | 9,547 ms | 9,529–9,626 ms | 5 |

The small difference and overlapping ranges do not establish a speed improvement. Whole-host CPU busy ranged about 47–100% across samples, including the browser; another workstream could have run on the same machine. Five samples per side and emulation cannot establish real-world device performance. The [paired raw data](../../output/playwright/game-loading-fix/loading-paired-performance.json) includes order, host load, individual results, renderer and response timings.

A separate, instrumented diagnostic profile (not a formal timing sample) showed the candidate's 639,086-byte shared JavaScript chunk begin around 435 ms and finish around 1,954 ms; the first GLB request began around 1,983 ms, the last GLB response ended around 9,511 ms, final model progress appeared at 9,512 ms, the first following WebGL draw was invoked at 9,515 ms and a frame observed ready at 9,533 ms. These values are browser navigation-relative; the draw timestamp is an invocation, not GPU completion, and the final parse interval does not represent total parsing work, which overlaps transfers. The local test server sends the JavaScript without compression, so the chunk's production transfer time must be measured separately. See the [startup profile](../../output/playwright/game-loading-fix/loading-startup-profile.json).

The 18 unchanged GLBs total 3,697,784 bytes. At a strict shared 4,000,000 bits/s, those bytes alone require about 7.4 seconds in the ideal case, before other resources, latency or processing. The observed roughly 7.5-second interval between first GLB start and last GLB response is consistent with this bandwidth limit. The provisional 3-second desktop / 5-second mobile interactive targets were not met under this emulated profile; this does not measure a physical phone. Assess real hosting compression, physical device/network results and asset delivery options before changing assets or promising those targets.

## Reproduction

Run from the repository with its pinned dependencies and system Chrome installed. The diagnostics and performance tools refuse to overwrite their output directory. Builds must already exist and remain unchanged during a comparison. The original baseline diagnostics above were collected before the portable script was parameterized; it preserves the same fixture, observation and CDP method.

```sh
export PATH=/opt/homebrew/opt/node@24/bin:$PATH
node scripts/audit-game-loading-mechanism.mjs /path/to/baseline-dist /tmp/loading-mechanism-new
node scripts/audit-game-loading-diagnostics.mjs /path/to/baseline-dist /tmp/loading-original-new
node scripts/audit-game-loading-diagnostics.mjs /path/to/candidate-dist /tmp/loading-candidate-new
node scripts/audit-game-loading-performance.mjs /path/to/baseline-dist /path/to/candidate-dist /tmp/loading-paired-new
node scripts/audit-game-loading-performance.mjs /path/to/baseline-dist /path/to/candidate-dist /tmp/loading-profile-new profile
TEST_BUILD_DIR=/path/to/candidate-dist node scripts/test-game-loading.mjs
```

For the original/fixed cancellation contrast, set `GAME_LOADING_TEST=passthrough` and run the last command against each frozen build; the original is expected to exit nonzero. A fresh output directory and isolated runtime should be used for each diagnostic run. No deployment or production change was performed by this investigation.

## Final integration verification

The primary agent integrated the same loader and <=260px repair into main snapshot `31e5475e51135544c074976373da18f2bee7548b`, preserving upstream Gallery/model and viewport changes. Final build `042c99b1e32521a0` passed five loading regression cases, 45 Game/browser groups including WebKit, 16 PWA cases and the other checks listed in [release readiness](release-readiness.md). A separate real browser download matched the original table GLB exactly.

The primary agent independently reran the portable six-control [mechanism fixture](../../output/playwright/game-loading-fix/mechanism-independent.json): the two native controls finished, the four wrapped/Three controls emitted the expected abort, and all byte-returning controls matched the original table hash. The [latest-build native diagnostic](../../output/playwright/game-loading-fix/native-latest-diagnostics.json) then recorded 18 finished / zero failed requests in both observed and unobserved Game runs; 18/18 actually consumed byte hashes matched. This is separate correctness evidence, not additional formal paired performance samples. Physical devices, production compression, server-side connection release and sustained GPU memory remain unverified.

Main later advanced to `2581395` solely for catalog-count test maintenance. The feature adopted it without changing runtime/asset sources; a fresh build remained `042c99b1e32521a0`, and the two affected full suites passed again. See the [verification manifest](../../output/playwright/game-loading-fix/verification-manifest.json).
