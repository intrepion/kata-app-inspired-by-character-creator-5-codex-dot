# Anatomy revision QA

## Status

Revision based on source commit `3826ab42c349f15d40dfd9cc3fcc66753addd272`. Publication was authorized after local review. QA did not edit real-user autosave data. The release is deployed by the repository's check-and-build and GitHub Pages workflow.

## Test-first work

Four new anatomy tests first failed against the old model: adult proportions, identifiable anatomical parts, smooth normals, and fingers/thumbs. Camera tests also failed before the renderer existed and exposed a vertical framing error, which was corrected. Final `npm run check`: 17 tests pass. `npm run build` and `git diff --check` pass.

Coverage includes all presets, individual parameter endpoints, all poses, finite nondegenerate triangles, unit vertex normals, full-body framing at 390px and desktop widths, and a software overlap regression proving that depth wins regardless of triangle order.

## Browser verification

Viewed the live public app to identify the original silhouette and rendering problems. All local app inspection used a running HTTP server at `http://127.0.0.1:4186`; no file URLs were used. Native Python HTTP serving was required because the browser and command runner have separate loopback network namespaces.

The browser harness passes all 19 assertions: rendered preview, depth-tested renderer, Face/Body switching, slider pixel changes, undo/redo, pose selection, orbit, project/OBJ/PNG exports, safe name rendering, autosave, cancellation, valid/malformed import, unsaved-edit warning after undo and reload restoration.

Visually reviewed the default body and face, side and back silhouette, raised-hand pose, and actual 390px iframe layout. The captures in `docs/screenshots/anatomy-*.jpg` are genuine browser viewport screenshots. The narrow image intentionally includes the surrounding browser viewport, not a resized desktop mockup. Full-page and clipped screenshot APIs timed out; viewport captures worked.

## Rendering and compatibility

This Chrome environment has WebGL disabled. The tested browser path is the smooth software depth-buffer renderer. WebGL shaders are syntax-reviewed code, not browser-executed validation here. Safari, Firefox, physical phones, screen readers, native file-dialog round trips and downstream professional 3D applications were not tested. Browser file assertions inspect generated Blobs and use constructed FileLists.

Existing version-1 project validation, import limits, autosave keys and undo history are unchanged. QA uses the separate `kata-persona-v1-qa` key. Projects preserve their parameters, not the old toy-like appearance: loading them intentionally regenerates the improved geometry.

## Limits

This is a stylized procedural human figure, not a scan or photoreal digital human. Separate surface sections can still show seams at extreme morphs or bends. No rig, skin weights, UVs, facial expressions or animation were added. OBJ still exports independent RGB-colored triangles without smooth-normal declarations; importing applications may require normal recalculation. GPU rendering and low-powered-device performance remain unverified.
