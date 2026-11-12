# Gallery GLB transport diagnosis and fix

## Reproduction

A fresh build of `a1003a9` reproduced the strict railing failure on Ubuntu with
Playwright Chromium **156.0.8078.4** / SwiftShader: 8/9 cases passed; the 1 m railing
at 390 px emitted `net::ERR_ABORTED` despite correct consumed bytes and rendering.
The original reports were retained, not replaced by passing reruns.

The isolated CDP audit used fresh contexts, service workers blocked, cache disabled,
390 × 844 viewport and a 100 ms / 4 Mbps emulated network. For both observed and
unobserved runs of the 1 m railing, 2 m railing, sorting station and legacy pool table,
all eight baseline cases recorded exactly one GLB request, HTTP 200, the complete
expected response length, and a still-open viewer, followed by `ERR_ABORTED`.
The four byte-observed cases also matched their source SHA-256. This rules out a
duplicate request, viewer dismissal, and byte observation as necessary causes in
these reproduced cases. It does not establish the internal Chromium cause.

The eight-control mechanism fixture used the same 417,656-byte table GLB:

- Native `fetch().arrayBuffer()`, with and without a request signal: `loadingFinished`.
- Direct `getReader()` accumulation, a stream wrapper retaining its original
  Response, two other stream wrappers, pinned Three.js FileLoader and GLTFLoader:
  `ERR_ABORTED` after completion.
- Every byte-returning control matched the source SHA-256. GLTFLoader returned a
  52-mesh scene. Retaining the original Response did not resolve the event.

See [baseline CDP](../output/playwright/gallery-loading-fix/baseline-cdp.json),
[original strict railing results](../output/playwright/gallery-loading-fix/baseline-glass.json)
and [mechanism controls](../output/playwright/gallery-loading-fix/mechanism.json).

## Bounded change

The Gallery now uses the existing vehicle transport path for every model: native
fetch with the viewer abort signal, native response `arrayBuffer()`, and
`GLTFLoader.parseAsync()` with the original absolute resource base. The actual
loader changes; no request-failure or console check is suppressed. The existing
post-transfer/post-parse stale checks and renderer/model disposal remain in place.

The response body is consumed before checking HTTP status. A new 503/retry case
caught the first candidate abandoning its unread error response, then reporting
an abort during retry. Consuming it prevents that leftover request; failed HTTP
responses are still rejected and never parsed. The initial failed regression is
[preserved](../output/playwright/gallery-loading-fix/candidate-initial-lifecycle.json).

Loading remains indeterminate (`Loading the 3D model…`); the optional byte percentage
for nonvehicle models is no longer shown. Loading fallback, retry, controls and
resource cleanup remain. Game and Solar loaders, assets and catalog are unchanged.

## Final verification

- CDP audit: 8/8 pass, one finished GLB request per case, zero request/console/page
  failures, all four observed byte hashes match.
- Lifecycle regression: 4/4 pass. Closing during a real throttled table transfer
  cancels after 1,493 / 417,656 bytes, before full receipt. The sole expected abort
  is matched to that request. Opening Cue Ball then finishes without extra failures
  or a stale canvas. HTTP 503, truncated GLB and injected transport failure each
  retain fallback and successfully retry, without unexpected errors.
- Unchanged strict suites: railing 9/9, sorting station 3/3, event booth 3/3,
  floor direction sign 3/3, queue 12/12, service desk 6/6, essentials 15/15.
- General library: 9/9, including repeated opening, refresh, related-model links,
  history, fallback/retry and resource release.
- All 119 unit tests pass; build and asset validation pass. The existing >500 kB
  shared-chunk warning remains. All 87 built GLBs are byte-identical to baseline.

[Final CDP](../output/playwright/gallery-loading-fix/candidate-cdp.json),
[lifecycle](../output/playwright/gallery-loading-fix/candidate-lifecycle.json),
[strict suites](../output/playwright/gallery-loading-fix/strict-results.json) and
[source/asset verification manifest](../output/playwright/gallery-loading-fix/verification.json).
Some pre-existing test reports hard-code a macOS environment label; the added
`executedEnvironment` field records the actual Ubuntu run without rewriting those
historical script fields. Screenshots and frozen builds were retained locally.

```sh
npm run build
node scripts/audit-gallery-loading.mjs dist /tmp/gallery-audit-new
node scripts/audit-gallery-loading-mechanism.mjs dist /tmp/gallery-mechanism-new
TEST_ARTIFACT_DIR=/tmp/gallery-lifecycle-new node scripts/test-gallery-loading.mjs
npm test
npm run test:library
# Run each existing scripts/test-mall-*.mjs asset suite separately as required.
```

The CDP and mechanism scripts refuse to reuse their output directory. Mechanism
failures are diagnostic observations, not passing loader assertions; the Gallery
CDP audit exits nonzero on any failed case. These are local Chromium/viewport
results, not physical Android/iOS, production network or performance measurements.
This task did not push, open a PR, merge or deploy, and does not resolve separate
visual approval or model quality requirements.
