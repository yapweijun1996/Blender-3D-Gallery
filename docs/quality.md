# Quality and release

Status: the GitHub Actions workflow installs dependencies, validates every cataloged GLB with Khronos glTF Validator, builds the gallery and deploys the Pages artifact. Game-specific unit, browser and PWA lifecycle suites now gate deployment; see [executed Game verification](game-verification.md). The broader checks below remain proposals unless covered by that evidence.

## Validation

When the application exists, run the project's reproducible install, lint, typecheck, unit tests and production build. Validate catalog schema, unique slugs, safe paths, rights, images and every published GLB. Record actual commands and results; do not infer success from a plan.

Browser checks should cover gallery search and filters, direct links under the deployment base path, viewer controls, missing assets, retry, no WebGL, keyboard navigation and responsive layouts. Inspect console errors and test touch interaction. Verify repeated viewer open/close for resource leaks. If PWA support is in scope, separately test installation, offline shell, update and recovery, including real-device iOS behavior where required.

Candidate performance targets include LCP at or below 2.5 seconds and CLS at or below 0.1 under an agreed test profile, and at least 30 fps for a representative model on a selected midrange mobile device. Measure rather than assume these results. Static cards should not create a WebGL canvas per model.

## Security and release

Validate third-party asset rights and provenance. Avoid unsanitized HTML, arbitrary model script execution, credentials in public files, unsafe asset URLs and unnecessary workflow permissions. Review CI dependencies and action pins. Local authoring and the website build are separate pipelines; do not execute untrusted model scripts in CI.

Before publishing, collect build and test results, validated model counts, asset sizes, screenshots, browser/device coverage, unresolved risks and a rollback plan. Deployment requires authorization and verification of the actual published result. Until then, describe the site and assets as proposed or local, not released.
