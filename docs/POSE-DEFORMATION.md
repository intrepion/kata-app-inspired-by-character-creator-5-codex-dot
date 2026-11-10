# Pose deformation

`tools/pose-human.py` constructs the arm's full orientation from its direction
and elbow-flexion plane. The previous implementation first assigned arbitrary
world-axis rotations and then aimed each arm segment independently. Aiming
constrained direction but left the pre-rotation's roll in place, twisting the
elbow. The replacement gives the clavicle 12° of elevation in T-pose and 20°
in wave, and constrains the elbow to its anatomical rest-plane hinge.

Wave's elbow rotation is about 8.37° relative to the already bent 44.77° rest
elbow, resulting in a roughly 53° bend. This is not an almost-straight elbow.
The humerus must externally rotate for this waving gesture. Ordinary linear
blend skinning collapses volume during that rotation, so the helper also bakes
Blender's dual-quaternion preserve-volume result into portable pose corrective
morphs. The GLB retains its editable skeleton and ordinary morph targets.

## Build integration

After finalizing clothing geometry and appearance morphs, before export:

```python
pose_tools = runpy.run_path(str(ROOT/'tools/pose-human.py'))
pose_qa = pose_tools['bake_pose_correctives'](rig, [body, shirt, pants])
poses = pose_tools['build_poses'](rig)
manifest['poseCorrectives'] = pose_tools['POSE_CORRECTIVES']
```

The corrective mapping is `tpose: PoseTpose`, `wave: PoseWave`, and
`stride: PoseStride`. Relaxed has no correction. All corrective values are
zero when the helper returns. After setting appearance morphs, the renderer
must set only the current pose's corrective to 1. Exported pose animation
tracks must explicitly key all three corrective weights, including zeros, so
switching from wave to relaxed or another pose cannot leak the old correction.
The parent builder/runtime owns those animation tracks.

## Regression

Run `blender -b --python tools/validate-poses.py`. An optional argument after
`--` writes the JSON report to that path. This does not save over the blend or
GLB. It verifies elbow axial twist under 0.01°, clavicle participation, matching
base-shape DQ deformation within 0.01 mm, and all four build/shoulder corners
within 12 mm. `docs/qa/pose-deformation.json` records the original-source test:
base error under 0.00027 mm and worst extreme-shape error 7.2 mm. The
fixed corrective is exact at the default shape; it is an approximation at
appearance extremes because their positions change without changing weights.

Run the same regression after regenerating garments. Numerical deformation
checks are not a substitute for visual inspection. Visual testing must use
the app served over localhost, never file URLs.

## Portable skinning and validation

Before baking, the builder retains and normalizes each vertex's four largest
bone weights, matching the runtime GLB path. Baking with more influences and
letting the exporter truncate them afterwards introduced up to 4 mm of pose
error. The new `tools/validate-pose-roundtrip.py` compares saved Blender source
against the actual GLB across four poses and five build/shoulder combinations.
The maximum measured source/export difference is 0.00116 mm. This numerical
agreement does not remove the documented 7.2 mm approximation to full DQ at
extreme appearance settings.

`tools/rebuild-human.sh` runs both pose validators with a nonzero Python error
exit code. The source validator checks saved corrective keys without re-baking,
so stale assets fail rather than being silently repaired during validation.

## Browser review

Serve `tests/deformation.html` over localhost. Its Height section checks actual
rendered pixel size and foot anchoring; the four pose sections show front/back
comparisons at five build values with endpoint shoulder widths. Export checks
are separate to avoid retaining multiple heavyweight GLB copies during visual
review. `tests/browser-foundation.html` covers saved-project migration, import,
undo/redo, and layout without modifying normal autosave keys.

For the full verification record and browser limitations, see [deformation QA](QA-DEFORMATION.md).
