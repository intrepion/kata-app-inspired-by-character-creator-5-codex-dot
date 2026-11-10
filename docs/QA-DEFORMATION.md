# Height, garment and pose correction verification

Pre-publication verification record. These checks were completed locally before the user approved publication.

## Changes

- Keep a pose-specific camera envelope fixed across height, shape and orbit edits.
  The feet remain on the same world-space ground while height visibly changes.
- Fit the shirt hem around each trouser morph rather than flattening it through
  the waistband. Preserve the original garment topology and skinning.
- Use anatomical elbow planes and clavicle movement, with portable pose
  corrective morphs to preserve shoulder/elbow volume.
- Normalize four skin weights before corrective baking, matching the GLB runtime.
- Export each pose with the current appearance and only its matching corrective,
  explicitly clearing other pose corrections.

## Regression evidence

- `npm run check`: 38 tests pass. Test concurrency is capped at two to avoid
  intermittent worker SIGKILLs observed under default concurrency in this workspace.
- `npm run build` and `git diff --check`: pass.
- Actual localhost height comparison on the original HEAD renderer: fails, with
  the 90%, 100% and 110% figures visually the same size. The identical browser
  check passes on the fixed renderer. Screenshot: `screenshots/persona-height-baseline-failure.jpg`.
- New waist test on the original HEAD asset: fails with -0.37 mm clearance at
  the narrowest build/shoulders. Updated asset passes across 101 build values,
  three shoulder values and circumference cross-sections, with at least 2 mm clearance.
- Saved pose corrective test passes without rebaking during validation.
- Source-to-GLB regression: all four poses and five build/shoulder combinations
  agree within 0.00116 mm. The pre-fix asset differed by up to 4.00 mm.
- Actual browser-exported narrow-wave GLB imports and remains editable in
  Blender 4.3.2: 53 bones, all appearance and pose morphs, embedded textures,
  connected garments, and all four pose clips. Report: `qa/browser-export-blender.json`.

## Browser observations

Only HTTP localhost pages were used; no file URLs or directly opened artifacts.

- Height 90%, 100%, 110% rendered at 257, 287, 317 pixels, with foot anchoring
  passing. This is the actual renderer output, not a camera formula-only assertion.
- Visually inspected 40 comparisons: Neutral, T-pose, Hello and Stride, front and
  back, five build settings, with narrow/broad shoulder endpoints. No prior
  waistband penetration or obvious collapsing/twisted joint artifact was visible.
- All pose/build comparisons remain inside the frame.
- Browser export retains the selected wave corrective and narrow appearance,
  with corrective weight tracks in every exported pose.
- Actual app migration, old autosave preservation, import, cancel import, undo,
  redo, failed/oversized/future-version imports, selection states and 375px layout
  pass in the browser regression harness. Normal autosave keys were not modified.
- The normal renderer startup path also loaded successfully in a fresh localhost
  copy of the current app, selecting software preview automatically.

Evidence screenshots are under `docs/screenshots/persona-*-fixed.jpg` and
`persona-*-front-back.jpg`, plus `persona-project-regression.jpg`.

## Browser limitation

The shared Chromium test browser intermittently displayed “Aw, Snap!” / “Can't
open this page” with error code 9, followed by tab-control timeouts. Forced
software tests ran successfully. A minimal page with no app, assets or libraries
created a 2D context and returned null for WebGL 2 without crashing. Both the old
baseline and current app subsequently started through the normal fallback path.
A later forced-software reload also failed while Blender/Node checks were running,
so WebGL is not the sole trigger. Resource pressure is plausible but unconfirmed:
kernel logs are not accessible and cgroup kill counters are not exposed. Heavy
checks and browser review were separated thereafter.
Therefore the lower-level cause of error 9 is not established, and this is not
proof of a deterministic application or GPU-driver bug. Hardware WebGL rendering
could not be verified here because the browser provides no WebGL 2 context.

## Reproduce

```
npm run dev
npm run prepare-browser-qa
# http://127.0.0.1:4186/tests/deformation.html?software=1
# http://127.0.0.1:4186/tests/browser-foundation.html?software=1
npm run check
npm run build
blender -b --python-exit-code 1 --python tools/validate-poses.py
blender -b --python-exit-code 1 --python tools/validate-pose-roundtrip.py
```

Pose correction is exact for the base shape but approximate at appearance
extremes, where deviation from full dual-quaternion deformation is at most
7.2 mm in these tests. This prototype does not implement simulated cloth or
arbitrary-pose collision handling.
