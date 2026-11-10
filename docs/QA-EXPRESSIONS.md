# Expression prototype

Implementation `d54d407`, based on published main `7f578af`, was approved for publication on 2026-11-10. The existing foundation GLB and packed Blender source remain byte-identical.

## Behavior

- Four sliders from 0–100%: Smile, Frown, Raise brows and Furrow brows.
- Smile lifts and widens the mouth corners, lifts the cheeks and adds a gentle eye squeeze. Frown lowers the mouth corners. Brow cards and forehead share each brow deformation field.
- Opposing mouth and brow sliders subtract. For example, Smile 80% and Frown 15% yield a 65% smile. Equal opposing values cancel. This avoids stacking contradictory extremes and is explained beside the controls.
- The smile squeeze uses effective blink = manual blink + 0.12 × smile × (1 − manual blink), with the net smile after opposition. The original gaze and closed-lid corrections still apply. Manual full blinks remain fully closed.
- Neutral expressions resets only the four expression sliders. Neutral eyes resets the manual blink/gaze sliders; a remaining smile still contributes its gentle eye squeeze.
- Undo/redo, autosave and `.persona` save/open retain expression fields. Old version 2 projects omit these fields and load neutral. Explicit malformed or out-of-range values remain errors. Randomize preserves expression and eye posing.

No new external assets were used. All new code and fields are original MIT additions over the existing CC0 anatomy.

## Verification

- TDD: expression project tests failed before implementation, and the geometry tests initially failed because the expression module did not exist. New tests cover defaults, invalid input, save/open, history, neutral preservation, original channel names, local finite deformations, mouth/cheek directions and brows. The complete syntax and Node suite passes 106 tests, including the publication manifest regression.
- Endpoint combinations across neutral, the three distinct adult face presets, all-low and all-high appearance values preserve nondegenerate front-face triangles. This is a sampled regression check, not an exhaustive collision proof.
- Mac hardware WebGL: ANGLE Metal / Apple M1. Reviewed nine basic comparisons including 50% and 100% smile, frown, brow endpoints, profile, three-quarter, wink and diagonal gaze; nine preset comparisons; and six appearance/garment/pose extremes.
- The same nine basic views were reviewed in the explicitly forced software fallback. Its lower resolution and flatter lighting are expected.
- All 99 expression browser checks pass; the earlier 94 blink/gaze browser checks also pass. Expression checks cover all four sliders, old projects, malformed values, independent eye values, reset/undo/redo, cancelled and repeated operations, actual in-browser generated `.persona` save/open, reload and 390px layout. The QA storage key is restored afterward.
- Browser exports: neutral, rounded smile with raised brows and blink/up-gaze, and angular mixed expressions with skirt/stride and diagonal gaze. An independent numerical validator checks their hashes, original geometry, topology, UVs, original morphs, selected expression weights, effective blink, all ten eye targets and four pose clips. Four intentionally corrupted exports are rejected.
- Blender 5.2.3 reimport verifies the original 53 bones plus nine skirt auxiliaries, editable expression and eyebrow keys, preserved visible texture pixels and alpha, and saves `artifacts/expression-editable.blend` as an editable example.
- `npm run build` passes. Browser viewing was only via HTTP localhost, never file URLs. Numerical GLB reads and headless Blender reimport were separately authorized.

## Blender editing

`Smile`, `Frown`, `BrowRaise` and `BrowFurrow` are appended to `HumanBody` and `Brows`. Mouth keys on Brows are intentionally zero. The full set is named consistently for scripts and manual selection. Choose one mouth and one brow direction after subtracting opposing controls; apply the same resulting weights to both meshes.

For a smile, its eye squeeze is exported in the existing per-mesh blink keys on HumanBody and Lashes. Preserve the exported eye weights, or recompute the effective blink above when editing the smile. Vertical-gaze interaction key weights remain effective blink multiplied by vertical gaze. Eyes, Iris and Cornea retain the existing gaze targets.

All four static pose clips retain selected expression weights. Clear or edit shape-key animation when changing keys interactively, because a selected static pose action can restore its stored values. Targets are fitted to the exported identity; changing identity shape keys externally may need refitting. glTF does not carry the app's fitting function or a unified Blender face-control panel.

## Quality limits

This is a closed-mouth expression prototype, not a production facial rig or an anatomical muscle solver. Full smile and frown are deliberately pronounced and can look stylized, especially with extreme face proportions. No mouth interior, teeth, tongue, jaw opening, wrinkle maps, lip-sync, asymmetric smile, automatic timing or facial animation timeline is included. Extreme eyelid combinations retain the previous blink prototype's thick/stretching lid appearance. Broad pose/identity combinations have been reviewed, but arbitrary collision freedom is not guaranteed. The eyebrows remain the existing stylized cards.

## Reproduce

```sh
node server.mjs --port 4193 --qa-exports
# Browse http://127.0.0.1:4193/tests/expressions.html?auto&capture
# Click Export expressions, then run:
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python tools/validate-expression-export.py --
npm run check
npm run build
```

Detailed browser/export reports and exported GLBs remain in ignored `artifacts/`; selected evidence is copied into `docs/`.
