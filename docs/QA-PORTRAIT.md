# Portrait revision: verification and limits

This is an unpublished local revision, not a claim that the public GitHub Pages app has changed.

## Implemented

- Original seeded skin pore normals and spatially varied roughness; unchanged licensed diffuse skin.
- Neutral studio key/fill and generated reflection cards, replacing the strongly warm/green lighting.
- Separate grayscale iris texture with independent tint, pupil/limbal ring, glossy clearcoat cornea, and a neutral sclera.
- Surface-fitted brow fibers and weighted lashes, including inherited facial morphs.
- Close-fitting textured crop, tapered curved fibers with longer top/short sides, and a dithered hairline fade. Bald remains available.
- Closer face view centered on the anatomical head throughout orbit, including profile and narrow canvases.
- Optional `eyeColor` in version 2 saves. Existing version 2 saves receive a default; original version 1 payloads are retained unchanged. New files with this field cannot be opened in old app builds that reject unknown keys.

## Automated verification

The initial portrait tests failed before implementation. Separate regression tests reproduced the profile clipping and duplicate animation clips before their fixes.

- `npm run check`: syntax and 51 Node tests.
- Final test-run note: one full-suite run terminated the legacy `renderer.test.mjs` process without an assertion diagnostic. An unchanged full-suite rerun passed all 51 tests, and the isolated legacy renderer suite passed all three. The cause was not established; this is not a claim of flake-free CI.
- `npm run build`: standalone static build; all assets bundled, no runtime CDN.
- `npm run test:garment-source`: unchanged source waist/sleeve constraints.
- `tests/portrait-preservation.test.mjs`: all 93 decoded body/garment position, normal, UV, skin-weight, joint and morph buffers match approved commit `41c867f` exactly. Sparse accessors are decoded before comparing.
- `tools/validate-human.py`: Blender import, 53 bones, UV/material/image retention, normalized weights, jaw and arm editing. The validator toggles an imported jaw value rather than assuming it starts at zero.
- `tools/validate-pose-roundtrip.py`: source vs GLB default and four build/shoulder corners in every pose; maximum measured vertex error approximately 0.0000012 m.

## Actual Mac browser verification

Verified on the user's Apple M1 Mac in Chrome: `ANGLE Metal Renderer: Apple M1`, WebGL 2. This is hardware verification, not SwiftShader or the compatibility CPU preview. All pages were served over localhost HTTP, never `file://`.

- Six face views: front, three-quarter, profile, bald, minimum and maximum face shapes, light/dark skin and different irises.
- Profile clipping found on the first pass and fixed; final comparison fits the full silhouette.
- Skin, iris and hair tint edits, bald/crop switching, undo/redo and autosave restoration.
- Browser-foundation harness: 20 checks including actual `.persona` file import, cancellation, undoable import, invalid/future/oversize rejection, focus/accessibility and narrow layout.
- Height changes remain visibly different with feet anchored; wave front/back at build/shoulder extremes shows no waist holes at the comparison size.
- Forced software browser harness: all 20 checks pass on the Mac, including Face view; the initial cloud browser hang was not reproduced.
- Actual browser GLB export retains embedded maps, weighted rig, morphs, four unique poses and selected height/pose. Bald export omits both scalp and strands.

## Exact browser-export capture

For automated local QA only, start `node server.mjs --qa-exports`. Visit `/tests/portrait.html?capture=1` or `/tests/roundtrip.html?capture=1` and run their visible export action. The test posts its exact exported bytes to a loopback-only, same-origin endpoint. It accepts only two fixed QA filenames, checks the GLB header and a 40 MiB limit, and writes under ignored `artifacts/`. The normal server does not accept writes; the server is not copied into the static build. The page reports byte count and SHA-256 for matching the file imported in Blender.

Final checked runtime asset SHA-256: `cf82a4d2dbc41509d413662829e15246d574c45d7f4d33412ecf7bb053206b0b`. The exact final browser portrait export was 27,902,392 bytes with SHA-256 `7f5085a923169718e675451e837bb4dd2e87cd59d7afab2c91669d55a1f59085`. Blender 5.2.3 imported it with 53 bones, four unique pose actions and zero unweighted vertices. Toggling the imported jaw extreme produced 0.006547 m of movement; the arm edit produced 0.197016 m. The preceding bald-wave export also passed Blender import and rig editing.

This avoids relying on privileged browser internal pages or browser-download tooling. It does not access the user's downloads history.

## Honest visual limits

This is a prototype improvement, not photorealism or Character Creator parity. Skin detail is synthetic, not a new scan, and tinting does not supply a range of skin scans. The eye is a fixed fitted iris/cornea approximation, not a full refractive anatomical eye. Hair is original procedural ribbon geometry over a textured scalp, not a production groom; the uniform cap-like appearance is reduced but styling remains simplified. There is no facial animation, expression rig, subsurface skin shader, cloth simulation or demographic asset library.

The CPU fallback omits normal-map response, reflections and clearcoat. Node rasterizer tests and all 20 forced-software browser checks pass on the Mac. Hardware WebGL is the visual acceptance path; fallback rendering should not be used to judge portrait realism.
