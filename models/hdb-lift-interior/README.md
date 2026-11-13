# HDB Lift Interior

V2.1 backlog 303. Open-front compact lift cabin with editable wall panels, floor, removable ceiling, handrail, light diffusers and generic button strip.

Generate with Blender 4.0.2: blender --background --python generate.py. Re-export edited source with -- --export-source. Render shipped GLB with render_views.py; convert previews with prepare_previews.py. Validate using node validate.mjs, inspect_source.py in Blender and node verify_source_edit.mjs.

Units: metres; Blender +Z up / glTF +Y up; front Blender -Y / glTF +Z. Source poses are editable but no runtime simulation is claimed. Original project asset; public redistribution terms unspecified. Physical Android/iOS not tested. No safety, engineering or official HDB specification claim.
