# Repository guidance

## Project context

This project is a public gallery for real Blender-created 3D works, independent of the tool or agent used to create them. Read the relevant documents in `docs/` and inspect actual repository state before changing behavior. Proposed specifications are not proof that a feature, model or deployment exists; reconcile any differences with current evidence and the user's instructions.

## Working practices

- Keep changes focused and preserve unrelated work. Document material changes to behavior, contracts and workflows.
- Treat metadata and third-party models as untrusted. Do not run downloaded Blender scripts without review, expose secrets, or publish assets without verified rights and attribution.
- Preserve model sources and reproducibility information where available. Do not claim a model is interactive until its real GLB has been validated and tested.
- Keep gallery cards lightweight; the proposed viewer loads 3D only when needed and provides loading, error and accessibility fallbacks.
- For changes, run checks appropriate to the affected behavior and report what was verified and what was not. Do not claim a deployment or release without verifying it.
- Follow the user's explicit scope and authorization for commits, pushes and publication. Do not make destructive Git changes or publish sensitive information without explicit authorization.
