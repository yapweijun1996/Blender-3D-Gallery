# Solar GPU queue diagnosis (2026-11-14)

Local host Chromium / SwiftShader, 1440x900, Node22. Not physical mobile or CI proof.

Pure timing instrumentation wrapped renderer.render and renderer.dispose without changing rendering inputs. Same Library scenarios and thresholds were used for baseline and experimental deferred-disposal candidate. Temporary instrumented source hashes and logs retained. Candidate source restored after each experiment, then replaced with final frame gate. No test assertions were removed or thresholds raised.

| Variant | Solar reload | Back native click | JS disposal | Observation |
|---|---:|---:|---:|---|
| HEAD baseline | 17768ms | 89ms | 4.3ms | timer gap21654ms after leaving |
| Rejected deferred disposal | 12850ms | 89ms | 1.6ms | reload still slow; pre-click4s gap |
| Experimental GPU frame gate | 3960ms | 78ms | 4.3ms | no20s queue stall |
| Final clean GPU frame gate | 4000ms | 74ms | not instrumented | Library9/9 PASS |

Initial JS render calls took114–294ms, subsequent calls mostly<4ms. They enqueue asynchronous GPU work and do not measure GPU completion. Dedicated final browser instrumentation measured GPU fence completion4056.9ms and2954.7ms during10s default overview, with377 nonblocking TIMEOUT polls. This supports expensive individual software-rendered frames plus accumulated queued frames, not slow JS resource disposal, as the dominant delay.

Final code admits at most one pending GPU frame using zero-timeout clientWaitSync; simulation and controls still update every RAF with unchanged speed/defaults/geometry/materials. Dirty work remains pending until GPU ready. Missing/failed APIs fall back to original unthrottled behavior. Disposal/context loss release the owned fence.

Focused unit5/5, build, Library9/9 PASS. Dedicated browser pause/Earth focus/resume10/navigation:236ms leave,6 created/6 deleted/live0 syncs; context-loss cleanup PASS.

Limitations: Individual overview GPU frames remain approximately3–4seconds under local SwiftShader; this fix bounds backlog, it does not claim smooth software-rendered overview or resolve all GPU performance concerns. Await unchanged CI gates before release.
