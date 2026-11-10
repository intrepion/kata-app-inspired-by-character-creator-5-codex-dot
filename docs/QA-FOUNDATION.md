# Human foundation verification

Date: 2026-11-10. Local source revision only; no push or deployment.

## Verified

- `npm run check`: 31 Node tests pass, with syntax checks. Seventeen legacy procedural tests remain as regression history; the new human has separate asset, schema and software-renderer coverage.
- `npm run build`: static distribution built and smoke-tested through `/dist/?qa=1`, with local vendor files, runtime GLB and license notes. No CDN dependency or Blender source in the production folder.
- Chromium, running HTTP at `http://127.0.0.1:4186`: **20/20** browser harness checks pass. They cover loaded human/exports, v1 storage preservation, approximate migration, undo/redo, pose/focus, actual `.persona` input, cancelled replacement, undoable import, future/oversized rejection, and 375px horizontal-overflow checks.
- Same localhost browser: genuine body/face visual review, including actual skeletal Hello pose and clear textured brown eyes. Screenshots are `docs/screenshots/persona-foundation-*.png`, not mockups.
- The runtime exporter harness passes 13 checks for GLB2, 53-joint skinning, UVs, ten morph targets, non-neutral morph values, embedded skin/eye images, four pose clips, selected-pose ordering, current bone transforms, omitted hair and current height.
- Exact app UI export `artifacts/Fern-app-export.glb` imported into Blender **4.3.2**. The tested project is Botanist with Hello pose and no hair. All eleven checks pass in `docs/BLENDER-ROUNDTRIP.json`. Bone count 53; expected morph weights .2; effective height factor 0.970000059; posed world bounds match the source reference exactly. Editing jaw and forearm after import deforms the skin by 5.08 mm and 13.45 cm. The imported source is retained as `artifacts/Fern-roundtrip.blend`.
- Khronos glTF Validator 2.0.0-dev.3.10: **zero errors**, four warnings and two informational notices for that exact UI export. The warnings identify skinned meshes nested under a parent. Their skeleton also inherits the character transform; the measured Blender pose/height roundtrip confirms the result. The informational notices identify unused UVs on flat-color garments. Full report: `docs/GLTF-VALIDATION.json`.
- Source-asset Blender checks additionally verify every skinned vertex has weights, every mesh has UVs, the top/pants/hair each form one connected surface, four pose actions exist, both image resolutions are retained, and bones/shape keys remain editable. Report: `assets/human/qa.json`.

The final production UI also downloaded a valid PNG and a version 2 `.persona` project, which was parsed and validated.

## Visual review and corrections

The character is based on MakeHuman's anatomical adult topology rather than independent tubes/ellipsoids. Review used front, three-quarter and close facial views, with adult proportions, continuous shoulders/limbs, distinct jaw/nose/ears/lips, fitted eyes and articulated fingers checked. Genuine Blender renders are available through `/tests/asset-review.html`. This is an anatomy-based fictional composite, not a scan or photorealistic reproduction of a specific person.

Review caught and corrected disconnected wrist clothing fragments, jagged garment boundaries, gaps in an initial helper-scalp mesh, face camera targeting, and transparent eyes being overwritten by opaque skin in the CPU path. The exported current-pose ordering was corrected after the first Blender import selected the neutral action automatically. The final download was re-imported and all checks rerun.

## Limits and unverified paths

- This cloud Chromium has WebGL disabled. The **software preview** is the visually tested path. Three.js/WebGL is integrated, but an actual hardware-accelerated browser pass is still needed; do not claim that path was visually verified.
- CPU rendering has simpler lighting, nearest texture sampling and a 900px maximum backing dimension. High-density/mobile performance and physical touch/pen hardware were not measured.
- The browser became unresponsive with several heavy QA tabs open. Closing only task-created QA tabs and continuing in one tab recovered it. Single-preview editing/export then completed. This is not a benchmark or proof of low-memory support.
- The solid crop and fitted garments are deliberately simple. There is no hair groom, shoe asset, cloth simulation, facial animation, face rig or broad demographic library. Extreme combined shapes can require manual collision/rig-fit adjustment.
- Neutral is the source A-pose; the legacy stored key remains `relaxed`. Stride is a static skeletal pose, not a walk cycle.
- The initial unavailable-WebGL message was observed before the same-human CPU fallback was added. The final no-WebGL-and-no-Canvas path is covered by `/tests/unsupported.html`.
- Version 1 geometry is not recreated exactly. Original validated parameters are retained; approximate migration is explicit in the UI.
