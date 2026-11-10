# Blink and gaze prototype

Local prototype based on `599524f`. Not published. The retained foundation GLB and Blender source are byte-identical to the approved distinct-faces/skirt milestone.

## What is implemented

- Independent anatomical left/right blink, 0–100%, and horizontal/vertical gaze, −100–100%.
- Positive horizontal looks to the character's right, and positive vertical looks up. Character-left is on the viewer's right in a front view.
- Gaze is constrained inside a 12° horizontal / 8° vertical envelope. The single-axis endpoints are 11.85° and 7.9° to leave room for the additive diagonal approximation.
- Skin lids and eyelashes deform together. Eyes, iris and cornea share fitted gaze pivots. Four interaction targets cancel vertical lid following when that eye closes.
- Neutral eyes reset, undo/redo, autosave, `.persona` save/open, keyboard-accessible sliders and narrow layout.
- Older version 2 projects default all omitted eye fields to zero. Explicit invalid values remain errors. No automatic blinking, mouth movement, facial-expression library or lip-sync is included.

The additions are original MIT code. No new external assets, proprietary assets or downloads were used. Existing CC0 anatomy and its original MIT portrait additions remain intact.

## Verification

- TDD: project tests failed before adding the controls. A loader-realistic fixture exposed loss of original morph names when appending targets; that regression is now tested. Corrective-normal and diagonal-angle tests also failed before their fixes.
- `npm run check`: complete syntax and Node regression suite, including original body, identity, garment, pose, project and renderer tests plus the new eye tests.
- `tests/eye-rig.test.mjs`: neutral preservation, side isolation, finite geometry, every original identity target, gaze bounds, and exact side-matched normal correction. Six identities (neutral, three adult presets, all-low and all-high combinations), five gaze states and three blink states produce 90 closure cases with 5,820 sampled iris rays. This is a sampled front-occlusion check, not an exhaustive collision proof.
- `/tests/blink-controls.html?capture`: 94 browser checks, including independent controls, reset/undo/redo, old and invalid projects, in-browser save/open, reload/autosave and 390px layout. The fixture restores the isolated QA storage key.
- `/tests/blink-gaze.html?auto&capture`: actual Mac hardware WebGL on ANGLE Metal / Apple M1. Nine front, three-quarter, profile, half-blink, full-blink, wink and diagonal-gaze comparisons.
- `?mode=presets`: nine views across the three distinct faces. `?mode=extremes`: six combined face/body/garment cases, including crop, skirt/stride and trousers/wave.
- `?software=1`: the same nine eye cases in the CPU fallback. Its flatter lighting and lower resolution are expected.
- Browser GLB exports are captured by explicit, loopback-only `--qa-exports` routes. `tools/validate-eye-export.py` independently verifies original geometry, UVs, topology, normals, morphs, bind matrices, four pose clips and selected eye/corrective weights. Intentionally corrupted exports are rejected.
- Headless Blender 5.2.3 imports the export, verifies 53 body + 9 skirt bones, edits blink/gaze shape keys and saves an editable `.blend`. Seven textures are completely pixel-identical. Hair-cap alpha and every visible texel are identical; browser PNG serialization changes only hidden RGB under zero alpha.
- `npm run build` passes. The garment-source test passes with Blender's bundled Python/NumPy; the Mac's default `python3` lacks NumPy.

Visual review was performed only through localhost HTTP, never `file://`. Numerical GLB reads and headless Blender reimport were separately approved.

## Export and Blender editing

Ten named targets are appended to `HumanBody`, `Lashes`, `Eyes`, `Iris` and `Cornea`:

- `BlinkLeft`, `BlinkRight`
- `GazeLeft`, `GazeRight`, `GazeUp`, `GazeDown`
- `BlinkLeftGazeUp`, `BlinkLeftGazeDown`, `BlinkRightGazeUp`, `BlinkRightGazeDown`

A target may have zero displacement on a part it does not affect. For example, blink never squashes an eyeball. In Blender, apply the same expression weights to the fitted parts. Use one gaze direction per axis. Each interaction target's weight is the corresponding blink weight multiplied by that vertical gaze weight. The four static body-pose clips retain the selected eye expression. Clear or edit shape-key animation before changing keys interactively, since a selected static pose action can reapply its stored weights.

The app recalculates endpoints when identity changes. Exported endpoints are fitted to the exported identity. Editing a head/eye identity key later in Blender may require refitting the eye targets; the glTF format does not retain the app's fitting function or a unified Blender control panel. The source validator also writes `artifacts/blink-editable.blend` as a reimport/editability example.

## Limits

This is an eye-morph prototype, not a production facial rig. Gaze uses linearly blended endpoints rather than continuous eyeball-bone rotations. Lid thickness and the conservative clearance envelope can look heavy at strong face combinations, and the existing eyelid texture stretches during closure. There is no tear-line simulation, wrinkle system, arbitrary-motion collision guarantee, automatic blink timing or facial animation clip. Appearance and eye controls are synchronized by the app; Blender editing is through named per-mesh shape keys.

The initial identity fit has a one-time setup cost. Cached neighbors and lightweight normal recalculation reduce later identity changes substantially (about 35 ms numerical fitting on the review Mac, excluding rendering), but this is not a frame-time guarantee. Blink and gaze slider changes reuse the fitted endpoints.

## Reproduce

```sh
node server.mjs --port 4192 --qa-exports
# Open http://127.0.0.1:4192/tests/blink-gaze.html?auto&capture
# Use Export blink and gaze, then:
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python tools/validate-eye-export.py
npm run check
npm run build
```

Reports and reproducible exports remain in ignored `artifacts/`; selected screenshots and final report snapshots are retained in `docs/`.
