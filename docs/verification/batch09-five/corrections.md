# Corrections from first fixed-run review

Initial evidence and asset files are preserved under initial-assets. Initial unit failure and validation.log remain unchanged.

- Porch322 exported576,772bytes, above the unchanged512,000byte budget. Removed imperceptible bevel modifiers from88 flat tiles; tile count, separate editable mesh data and grout gaps preserved. No budget/test weakening.
- Boundarywall324 pixel inspection found black coplanar overlap at the base/end-pier side and small open gaps below vent uprights. Piers now start on the base at0.20m and finish at coping underside1.57m; uprights span1.26–1.57m. Added explicit geometry checks.
- Canopy323 fascia end and side strips overlapped at the corners. Shortened side strips to meet end trim without coplanar overlap.
- All5 studio ground planes enlarged only for rendering so the stage edge no longer enters hero images. Delivered GLB excludes studio.

Corrected generation, source-edit, rendered visual inspection and browser revalidation are required. No runtime application code, old asset, test filter or original evidence was changed.
