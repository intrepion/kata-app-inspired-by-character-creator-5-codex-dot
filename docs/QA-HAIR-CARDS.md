# Layered Blender hair-card experiment

Local experiment based on `ef06f32`, after the published skin release `d689681`. Nothing in this experiment has been published or approved for publication.

## Honest visual result

The new groom has a clearer swept shape, more volume and a cleaner silhouette than the rejected fiber-on-cap prototype. Scalp gaps found in the first iteration were closed, broad locks were narrowed, roots outside the actual scalp were removed and prominent hooked flyaways were reduced. The final screenshots are actual localhost hardware WebGL output.

It remains visibly synthetic. Repeated side-card tips produce a toothed edge, the broad dark locks and solid backing can still read as a helmet from behind, and blond hair has limited color and strand depth. This is an improved editable real-time prototype, **not photorealistic or finished production hair**. Blender and browser render differently; the Blender image is explicitly separate from the matched browser comparison.

## Method and editable source

- Original, deterministic Blender construction: 439 guide curves, a textured coverage cap, staggered lower coverage cards, swept shape locks and sparse breakup cards. No third-party hair assets or paid tools.
- Original 2048px grayscale strand/alpha and normal atlases, plus a 1024px scalp-root texture. Atlas variants serve dense coverage, loose locks, wisps and the hairline.
- Two delivered skinned meshes, `HairGroom` and `HairCardRoot`, preserve the original 53-bone rig and all 28 named identity morph targets. Cards use ordinary cutout PBR materials, anisotropy 0.5, roughness 0.72, embedded textures and no simulation.
- Source: `assets/human/hair-cards/original-short-groom.blend`. It contains the original human context, separate guide curves, baked mesh cards, embedded images and an editable hair tint. Compressed Blender storage keeps it around 20 MB. It is excluded from the static website build.
- App asset: `assets/human/hair-cards/hair-cards.glb`, about 8.9 MiB. The atlas is neutral for the existing hair-color control. Source images and exact hashes are recorded in `provenance.json`.

To edit the groom, keep the armature in its original neutral/rest pose, open the source `.blend`, unhide the relevant curve in `EDITABLE Hair Guide Curves` and edit its control points, radius or tilt. The visible mesh is a baked result, not a live curve modifier. Run `tools/rebake-hair-cards.py` in that open Blender scene to rebuild the card mesh from those edited curves. Review the result before saving/exporting. This does not rerun the original numeric layout and discard your edits. Direct mesh and shape-key editing remain available too.

A real editability check moved a guide control point by 6 mm, rebaked it and measured about 5.13 mm of mesh movement while retaining all 28 identity keys and rig groups. The test did not save over the authored source. `tools/build-hair-cards.py` reproduces the initial authored layout; rerunning that generator deliberately replaces guide edits, so it is not the manual-edit workflow.

References: [William Paré-Jobin / Marmoset](https://marmoset.co/posts/real-time-character-design-creation-and-presentation-breakdown/) and [Mariia Zatorska's scalp-cap process](https://marizatorska.artstation.com/blog/vq7Z/create-the-hair-cap-using-maya-and-marmoset-process-video). These inform the layered cap/card method. Their assets and demonstrated output are not reused.

## Browser and application verification

- Hardware WebGL 2 on Mac Chrome, ANGLE Metal / Apple M1. Eighteen paired views compare the rejected procedural groom and new cards in brown, blond and black at front, three-quarter and profile angles. Six additional views cover back, opposite side, head/body endpoints, all face maxima and blond rim light. No renderer/shader console errors.
- Forced software mode completes the same 24 views and crop/bald/crop visibility checks. Its simplified shading does not reproduce normal-map or anisotropic highlights.
- 107 actual UI checks pass, including repeated hair/no-hair edits, tint undo/redo, editable project save/open, cancelled import, reload, expression/eye compatibility and 390px layout. The QA autosave is restored afterward.
- 125 Node/syntax regression tests pass, including real GLB loading, bone-name remapping, bind-space correction, relative morph transforms, switching between all three hair versions, disposal, portable export and preservation of source assets. The static build passes and its actual Face view loads in hardware WebGL with 56,668 triangles and an enabled GLB export.
- Normal app startup loads only the baked asset. The rejected generator is loaded only when a comparison explicitly asks for it. Existing project fields and tint controls are unchanged.

Fine cards do not cast or receive the coarse studio shadow map in the browser preview; the cap still casts. This avoids rectangular shadow artifacts with the existing studio's bias. Exported geometry and materials remain intact, and Blender/other viewers choose their own shadow treatment. Alpha edge quality and anisotropy support vary by renderer. There is no motion groom, cutting/styling UI, or long-hair collision system.

## Export and Blender checks

Four actual browser GLBs are captured: rejected procedural baseline, neutral cards, blond head-width/height maximum with expressions/skirt/stride, and bald/wave. Captured filenames, byte counts and hashes are in `HAIR-CARDS-VERIFICATION.json`.

The validator checks original non-hair geometry, UVs, weights, identity targets, skeleton parent/rest transforms, eyes and expressions; both new hair meshes' weights, 28 keys, selected values in all four pose clips, embedded textures and authored material properties; and complete hair omission when bald. The focused Blender stage imports the actual extreme capture, edits hair/head/face controls, saves an editable file, then re-exports and reimports it. Animation creation is disabled only for that focused Blender round trip; all four browser pose clips are validated separately.

Blender 5.2.3 LTS passes the actual round trip with 62 bones (53 body plus nine skirt auxiliaries), both 28-key hair meshes and anisotropy 0.5. A head-width edit moves card vertices about 11.3 mm, head-height about 19.6 mm, and a head-bone edit about 21.1 mm. Smile, blink, brow and gaze edits remain measurable. Eight deliberately corrupted export controls were rejected. Regional skin maps and the hair normal map preserve exact sampled pixels. Hair atlas alpha and opaque RGB are exact; fractional-alpha RGB has expected canvas serialization rounding below one 8-bit premultiplied level, so the atlas is not claimed to be byte/pixel-identical everywhere. The re-export retains the hair via its materials even though Blender renames the underlying mesh nodes. Exact measurements and hashes are in the verification JSON. Six Cycles renders use the actual baseline/neutral browser exports with unchanged imported materials. They use Blender lights, shadows and AgX, so do not treat them as pixel-matched browser screenshots.

## Performance

The default character has 56,668 visible triangles, versus 81,278 in the rejected prototype (30.3% fewer). New cap and cards together are 14,745 vertices / 17,988 triangles. In the recorded local run the baked asset loaded in about 376 ms, while the old generator took 2,901 ms. This is a local load sample, not a cold-network guarantee; the extra GLB download is about 8.9 MiB.

A bounded 24-sample draw test including `gl.finish()` measured median CPU submission plus GPU completion of 1.6 ms for the rejected version and 1.2 ms for the cards; 95th percentiles were 3.7 and 2.1 ms. These are **not interactive FPS measurements**. Transparent/cutout overlap can still be expensive on weaker GPUs, and mobile GPU performance has not been measured. The old source hair remains bundled with the foundation for baseline comparison, although its procedural replacement is not built during normal startup.

## Reproduce

```sh
node server.mjs --port 4197 --qa-exports
# /tests/hair-cards.html?auto&capture&exports
# /tests/hair-cards.html?auto&capture&software
# /tests/expression-controls.html?capture
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python tools/validate-hair-cards-export.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python tools/validate-hair-card-editability.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python tools/render-hair-cards-export.py
npm run check
npm run build
```

Capture endpoints remain localhost-only, same-origin, bounded and opt-in. No purchase, publication or ZIP delivery is part of this work.
