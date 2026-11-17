# Gallery maintenance tools

These are repository scripts run by a host. KB-MCP Tool Registry entries describe their contracts and source identities. Registration does not execute them or create a new callable MCP runtime tool.

## Deployment input selector

[Source](../scripts/deployment-inputs.mjs) · [Deployment contract](deployment.md) · [Skill](../.agents/skills/gallery-fast-deploy/SKILL.md)

- Runtime is Node.js 24 with Git, from the repository root.
- Command is `node scripts/deployment-inputs.mjs`.
- Inputs are the Git index, current catalog and text dependencies. Intended edits should be staged when checking the prospective cache key.
- Outputs are a printed selection count and digest, `/tmp/gallery-deployment-patterns`, and a `cache_key` line appended to `GITHUB_OUTPUT` when supplied.
- Side effects are local output-file writes. The script does not download resources or deploy the site. The workflow applies its patterns and restores or builds the resulting site.
- Verification includes sparse/normal output equivalence and a real cache-hit deployment that skipped downloads, installation and build.

## GLB lossless PNG recompression

[Source](../scripts/optimize-glb-png.py) · [Encoding evidence](verification/model-downloads/README.md) · [Skill](../.agents/skills/glb-lossless-png/SKILL.md)

- Runtime is Python with Pillow 13.0.0, the version used for the recorded batches.
- Command is `python scripts/optimize-glb-png.py <explicit GLB paths> --report <report.json>`.
- Supported inputs are single-buffer embedded GLBs with single-frame 8-bit RGB/RGBA PNG maps. Other embedded image formats retain their bytes. An unsupported PNG profile raises an error.
- For each PNG, the tool replaces only its IDAT data when smaller and retains all other chunks verbatim. It verifies decoded pixels and metadata and compares non-image GLB buffers before writing.
- Outputs are smaller input files in place and a report of changed exports with file and image hashes. Larger candidates retain the input bytes.
- The report is written after the batch. On an error, earlier files may already have changed. Use approved copies and inspect the diff before retrying. Restore only task-owned files from the recorded baseline if discarding a failed attempt.
- Verification covers 13 changed exports over two batches, 14,796,856 saved bytes, unchanged non-image payloads and image pixels, zero validator errors/warnings and 54 identical before/after canvas pairs. Phone-width checks use desktop Chromium and do not measure physical-phone performance.

## Source and registry ownership

The repository is the source of executable files. Skills explain use and acceptance. Tool Registry definitions reference pinned Git source files and SHA-256 values, with `writes_local` safety. They retain the registry's runtime trust status. Knowledge records retain project decisions, measured evidence and links to the owning documents.
