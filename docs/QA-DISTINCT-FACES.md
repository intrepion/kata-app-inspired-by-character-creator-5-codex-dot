# Distinct adult faces: local milestone

Local, unpublished implementation based on portrait commit `3a5fb77`. All visual testing uses a localhost HTTP server. No browser file URLs or directly opened artifacts are used.

## Changes

- Nine additional neutral-centered controls: head width, head height, cheek fullness, chin length, nose width, nose projection, eye spacing, brow height and lip fullness.
- Eighteen new editable shape targets, shared across the head and seven fitted parts: eyes, iris, cornea, brows, lashes, scalp and strands.
- Angular/Vale, Rounded/Marlowe and Long/Ellis adult presets. Their skin, hair, colors, body and neutral pose match Explorer so they demonstrate geometry rather than styling changes. Original Explorer, Pilot and Botanist remain.
- Old v2 projects default only omitted new fields to 0.5. Invalid supplied fields still fail. Project saving, autosave and forty-edit undo/redo include new controls. V1 migration retains its original source payload and warning.
- All additions are original MIT geometric fields and preset recipes; existing verified CC0/MIT assets retained. No new asset downloads.

## Test-driven implementation

Project tests failed for missing controls, presets and migration before implementation. Asset tests failed for missing targets/attachment morphs. Visual and geometric stress checks exposed chin-driven lip opening, eye/nose pinching and overlapping nasal contractions. The generator was corrected before acceptance: chin falloff stops above the mouth seam, eye-spacing transitions are wider, and nasal projection moves the tip/nostril region together.

Neutral-portrait snapshot tests also caught nonzero newly created source weights and Blender-added color-profile chunks on two roughness data textures. These were corrected; the baseline was not rewritten to match the new output.

## Automated evidence

- Full Node syntax/regression suite: 69 checks passed (13.9 seconds on the final rerun); static production build passed. Logs: `distinct-final-check.log` and `distinct-final-build.log` in the evidence bundle.
- 256 deterministic combinations of existing jaw/nose/eyes and the nine new control endpoints: no reversed triangles relative to the base and no triangle area below 5% of base (excluding originally negligible triangles). This is a sampled regression, not a proof against every possible surface collision.
- The 93 approved body/garment position, normal, UV, joint, weight and old morph buffers remain exact.
- All ten neutral portrait meshes, old morph data/weights, material definitions and eight embedded image byte streams match `3a5fb77` exactly. Every new target defaults to zero in the source and bundled GLB.
- All new body deltas are zero below 1.33 m; body/waist geometry remains untouched.
- Blender source-to-GLB comparison covers all 18 new targets on all eight fitted face meshes.
- Blender skeleton/UV/weight/material tests and existing four-pose/build/shoulder roundtrip checks passed. Maximum source/portable roundtrip difference was 1.14 micrometers; the new target comparison stayed below 0.66 micrometers. Installed Blender 5.2 names imported actions directly; the validator accepts those names and the prior suffixed names.
- Garment boundary/sleeve regression passed with Blender's bundled Python 3.13 and NumPy 2.3.4. The Mac system Python lacks NumPy, so the plain npm command needs that dependency in its selected Python environment. Nothing new was installed.

## Browser evidence

Actual Apple M1 Chrome WebGL: `ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)`. The final preset matrix uses identical skin/materials/lighting, no hair, and front, three-quarter and profile angles.

Visual inspection of the served PNG matrices confirmed distinct preset silhouettes in all three views, closed mouth seams in the tested presets, and attached eyes, brows, lashes and crop hair in the inspected cases. Individual endpoints remain usable; combined endpoint recipes are intentionally exaggerated. The software preview preserves shape differences with lower-resolution, simpler lighting.

The original browser-foundation harness passes all 20 checks, including migration, actual project import and cancellation, undo/redo, invalid/future/oversize handling and 375 px no-horizontal-overflow layout.

The final hardware run completed at 2026-11-10 10:38:51 UTC: 149 checks passed. It rendered all twelve bald preset/angle combinations, four crop presets, individual control endpoints and combined extremes; checked actual app preset selection, autosave, save/import and undo/redo; and exported the edited extreme in the wave pose with crop hair. The bounded software run completed at 10:39:41 UTC: 136 checks passed, with four front presets, a crossed crop extreme and the same export checks. Full reports and rendered comparison PNGs are retained in the evidence bundle.

Final hardware timing: asset/renderer creation 604 ms; first relaxed update/render 967.4 ms including shader compilation; first other-pose update/render 462.3–581.9 ms. Across 36 cases with 20 warm edits each, case medians were 0.4–2.4 ms and P95 values 0.9–4.2 ms, with an isolated 90.5 ms maximum. These are this Mac's browser-cache-dependent CPU update/render submission timings at 320×400 CSS px, not GPU completion or FPS. Chrome reported roughly 1.1 GB for the full acceptance page after export; it includes QA thumbnails, export buffers and a retained download Blob, so it is not a measured steady-state app memory figure. No low-memory-device acceptance claim is made.

## Export and limits

The exact final software-browser export `portrait-extreme.glb` (50,225,112 bytes) was reimported in Blender 5.2.3. It passed all 18 targets on eight fitted meshes, 53 bones, four clips, 1,624 fixed-appearance keyframe samples, UVs, materials, weighted vertices and eight embedded images. Changing HeadWide moved body vertices 13.10 mm and all seven fitted parts; a bone edit moved vertices 198.14 mm. Missing-target and missing-clip negative controls were rejected.

Final exported SHA-256: `f0cbd8221e8d9c6a3f22f645552bd5aab8fc513801e72d36ef62a88e1fca6ef2`. The earlier hardware export independently passed browser checks and had the same byte size, but the CPU run replaced that capture, so the Blender result refers specifically to the final CPU export. Both paths use the full editable exporter, not a raster fallback model.

Runtime GLB is about 23 MB; the source Blender file is about 35 MB. Triangle count stays 63,108. The larger morph data increases load/memory cost, and first use of each pose measures its camera envelope. CPU fallback is intentionally slower and omits normal-map lighting, clearcoat and reflected highlights.

This is a stylized single-foundation character tool, not photorealism, a demographic library, a production facial rig or Character Creator parity. No expressions, facial animation, simulated hair or cloth were added. Extreme combinations remain exaggerated and warrant artistic review; the sampled checks do not claim exhaustive collision freedom.

## Reproduce the checks

Run `node server.mjs --qa-exports --port 4193`, then visit `http://127.0.0.1:4193/tests/distinct-faces.html?auto=1&capture`. Append `&software=1` for the bounded fallback run. Review the captured images at `/tests/distinct-review.html`. The capture routes are disabled without the explicit flag, accept only bounded same-origin loopback requests and exact evidence filenames, and are not in the production build.

For the numerical export check, run `blender -b --python-exit-code 1 --python tools/validate-distinct-export.py`. It validates the exact export hash against the final software report and edits the imported asset in memory. Browser viewing remains HTTP localhost only.
