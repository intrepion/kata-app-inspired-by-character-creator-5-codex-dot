# Waist shading repair, 2026-11-10

Local-only verification. This work has not been published.

## Reproduced defect

The supplied screenshot showed triangular/fluted shading above the shirt hem.
The prior shirt/trouser clearance test passed while the defect remained visible.

The source builder flattened **every** shirt vertex below .985 m to .955 m,
not just the boundary loop. This collapsed multiple rows into a horizontal,
folded surface: 86 coplanar triangles, negligible-area faces, and 44–52 strictly
overlapping face pairs across the sampled build values. Their smooth normals
produced the fluted shading. The last repair expanded those same rows without
repairing their topology.

Both the deployed c0e7c43 asset and earlier e9ed705 asset reproduce the shading
in the close-up viewer. The deployed comparison is byte-identical to the
previously retrieved live asset (SHA-256
2fbaf1f7f6807327b034fff330d077319f33dfb45b7b607abc1960421a1e4191).

The old CPU fallback silently recalculated normals from triangle areas, hiding
the authored-normal problem. It now uses the same authored normal attributes,
normal morph deltas, bind matrices and weighted bone matrices as the WebGL
shader. This change reproduced the supplied screenshot before repairing the
asset. It does not claim identical lighting or shadow rendering.

## Repair

- Identify the complete lowest boundary loop, not individual low vertices.
- Pin only that loop to the hem height and solve a smooth height field for the
  connected interior waist rows. Sleeve and upper-torso vertices stay unchanged.
- Preserve vertex correspondence, UVs, skin weights, morphs and pose corrections.
- Reapply trouser clearance, then rebuild both the Blender source and runtime GLB.
- Keep the existing height framing and pose correction implementation.

## Tests and visual evidence

- Three new geometry tests fail on c0e7c43 while its old clearance test passes.
  The rebuilt source GLB and actual browser-exported GLB pass all four tests.
- Geometry tests cover build 0/25/50/75/100% and shoulders 0/50/100%, rejecting
  collapsed triangles, inward/horizontal lower-shell faces and coplanar interior
  overlaps. Existing clearance checks cover 101 build settings.
- New normal tests prove authored normals and morph deltas affect CPU shading.
  A weighted two-bone test independently follows shader matrix order, including
  bind transforms and nonuniform mesh/parent transforms.
- A Python graph fixture catches accidental sleeve-tip leveling and verifies
  untouched sleeves, upper torso and XY coordinates across three shape keys.
- `npm run check`: 44 tests pass. `npm run test:garment-source`: passes with NumPy.
- `npm run build` and `git diff --check`: pass.
- Final localhost close-ups inspected front/back at five builds for Neutral,
  T-pose, Hello and Stride, plus side/oblique views. Shoulder endpoints were
  exercised. The matching triangular hem shading is absent in these views.
- Height still visibly measures 257/287/317 px at 90/100/110%, with foot anchoring.
- Actual localhost browser export retains narrow build, active wave corrective,
  all four pose clips and editable corrective weight tracks. Blender 4.3.2
  imports it with 53 bones, UVs, embedded textures and editable bones/morphs.
- Source-to-GLB deformation agreement remains within 0.00116 mm over four poses
  and five build/shoulder combinations. See `qa/waist-source-roundtrip.json`,
  `qa/waist-pose-deformation.json` and `qa/waist-browser-export-blender.json`.

Screenshots: `screenshots/waist-deployed-authored-normals.jpg` and
`screenshots/waist-fixed-authored-normals.jpg`. They are browser captures of the
same local close-up test, before and after repair, using authored normals.

## Reproduce

Run the app server, then open `/tests/waist.html` on localhost. Never use file URLs.
The default reads the current runtime asset. For historical comparisons:

```
mkdir -p artifacts/waist
git show c0e7c43:assets/human/foundation.glb > artifacts/waist/deployed.glb
git show e9ed705:assets/human/foundation.glb > artifacts/waist/previous.glb
npm run dev
npm run check
npm run test:garment-source
GARMENT_TEST_GLB=artifacts/waist/browser-narrow-wave.glb node --test tests/garment-fit.test.mjs
```

## Limits

This environment still supplies no WebGL2 context. Visual testing used localhost
browser rendering with the corrected CPU normal path, which demonstrably
reproduced the screenshot's defect, but hardware WebGL shadows are not verified.
The prior claim that distant software previews ruled out waist defects was too
strong and is superseded by this record. Numeric clearance alone is not a visual
acceptance test. This remains a fixed-pose prototype, not cloth simulation.
