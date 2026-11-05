# Historical PR #1 pre-fix review follow-up

Date: 2026-11-05, Asia/Singapore.

PR #1 was already merged when this follow-up began: merge commit `7419def96a4ed65dcff8d423198cf05fea63a02d`, merged 2026-11-05 10:24:15 SGT. Remote main also includes later pool fixes. This follow-up inspects `d19606eb65962b66a0fc07be5b5f3c06ec6ef745` on isolated branch `codex/pr1-review-followup`.

No merge, deployment, asset-license change or KB content update was performed in this follow-up. Existing worktrees and local untracked work were retained. The owner explicitly requested no further merge or deployment.

A fresh Node 24.21.0 install/build succeeded on this revision; the existing large lazy Three.js chunk warning remains. `npm test` passed 70 tests, with zero failed/skipped.

See [mobile and accessibility follow-up](mobile-accessibility-followup.md), [performance follow-up](performance-followup.md) and [asset license decisions](asset-license-decisions.md) for new evidence, bounded conclusions and owner decisions. Physical mobile devices and screen-reader operation remain unverified.

## Acceptance disposition

- No new P0 was confirmed by these focused checks; this is not a complete security or release certification.
- P1: existing asset redistribution terms require owner disposition.
- Performance gap: cold 100ms / 4Mbps startup exceeds the provisional 3s/5s targets. GLB request-abort events remain unresolved; do not mark reliability/performance acceptance complete.
- P2: sub-320px stress viewport button-label overflow. Physical-device, screen-reader and sustained GPU-memory coverage remain open.
- This review adds scripts, documentation and retained evidence only. No runtime or asset change means no before/after optimization claim. The browser script intentionally exits 1 for the known visual finding.
