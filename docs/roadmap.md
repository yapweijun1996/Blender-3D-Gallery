# Roadmap and decision register

Status: the individual billiards gallery, local two-player Game and explicit offline PWA contract are implemented. See [Game delivery](game-implementation-plan.md) and [verification](game-verification.md). A searchable model library and Interactive Demo Index have been added in an isolated local branch; see [IA architecture](gallery-information-architecture.md) and [verification](verification/gallery-ia.md). This task does not deploy them. Broader curated-publication milestones remain proposed.

1. **Foundation:** resolve licensing, attribution, visual direction, supported Blender and package versions, hosting and candidate budgets. Record decisions and acceptance criteria.
2. **Gallery skeleton:** implement a responsive static gallery, base-path-aware links, one real validated GLB fixture, viewer controls and fallback states. Verify desktop and mobile behavior.
3. **Curated MVP:** add reviewed models with representative images, measured metadata and confirmed rights; implement discovery and deep links. Twelve works is an initial target to revisit, not a published count.
4. **Optional PWA:** implement and test the chosen offline contract and user-controlled update flow only if included in release scope.
5. **Growth:** improve the authoring and validation pipeline, measure storage and performance, and plan hosting as the collection expands.

## Decisions still open

- Repository code license and separate model redistribution terms.
- Final visual system, responsive breakpoints and accessibility validation.
- Supported Blender release and compatible frontend dependency versions.
- Measured performance and asset budgets and exception process.
- Initial launch scope, final model count, source storage and expansion beyond the delivered Game/PWA.

Keep decision records current: distinguish proposed, approved and superseded choices, with rationale, impacts and supporting evidence. Inspect actual repository and deployment state before treating any milestone as complete.
