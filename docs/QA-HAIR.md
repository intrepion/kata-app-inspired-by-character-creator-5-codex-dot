# Static short crop prototype

Local prototype based on the published regional-skin release `d689681`. It has not been approved for publication. Review the actual before/after captures before considering a release: the scalp-cap appearance and patterned grouping still need visual refinement.

## Implementation and limits

- Original deterministic grooming: 700 small guides with 3,500 grouped tapered fibers, 60 sparse flyaways and 657 shorter perimeter fibers. Growth varies between the upward front, swept crown, downward sides and nape.
- A new 2048px original root atlas adds fine strand/color variation and a narrower, higher-resolution hairline fade. The rear UV wrap is split correctly; the duplicated corners retain identical source positions, normals, bone weights and all 28 identity deltas.
- Cylindrical fiber normals and glTF `KHR_materials_anisotropy` provide directional highlights. Hair uses ordinary skinned triangles, per-fiber color variation and the original 53-bone rig, rather than a browser-only groom shader.
- No new project fields. Existing crop projects receive the refined style. Crop/no-hair, tint, undo/redo and editable saves remain available.
- The source `foundation.glb`, `foundation.blend`, skin maps, body, eyes, expression logic, garments and authored poses are unchanged. The baseline hairstyle remains available in the comparison fixture only.

This is a procedural short hairstyle, not a photorealistic scan or production strand groom. The scalp underlay and grouped pattern remain visible in close-ups, especially with dark tint or strong light. There is no hair physics, cutting, styling UI or long-hair collision system. Subpixel fiber self-shadow receiving is disabled in the browser to avoid shadow-map aliasing; fibers still cast shadows. Blender uses its own rendering/shadow treatment. The software preview preserves geometry, root texture and vertex colors but does not reproduce the anisotropic sheen. Viewers without the anisotropy extension fall back to ordinary PBR shading. Edge antialiasing varies between viewers.

## Verified locally

- Mac Chrome, hardware WebGL 2: ANGLE Metal / Apple M1. Eighteen matched original/new views cover brown, blond and black at front, three-quarter and profile. Six additional views cover back, opposite side, head/body endpoints, all face maxima and blond rim lighting. No renderer/shader console errors were recorded.
- Back-view review caught a root UV seam, which was repaired and recaptured. The finished captures are real localhost canvas output, not image-generated previews.
- 107 actual UI checks pass, including repeated bald/crop operations, hair tint undo/redo, project download/open, cancelled import, reload, expression/eye compatibility and 390px layout. The temporary QA autosave is restored.
- Forced software renderer completes the same 24 views and crop/bald/crop visibility check.
- The generated static build also loads from localhost in hardware WebGL, with the Face view, clumped crop, 81,278-triangle readout and enabled GLB export visible.
- Full syntax and Node regression suite: 116 passed. Static build passes. New tests cover deterministic geometry, bounded counts, normalized original weights, inherited identity targets, regional growth, exact seam-vertex preservation, data textures, software vertex colors and repeat wrapping after interpolation. Independent review found the software seam-wrap issue and a retained baseline texture cleanup gap; both are fixed and rechecked.

## Export and Blender

Four actual browser exports were captured: original baseline, refined neutral, blond head-width/height maximum with expression/skirt/stride, and bald/wave. The exact names, byte counts and SHA-256 values are retained in `HAIR-VERIFICATION.json`.

Independent structure checks validate the original non-hair geometry, UVs, weights, identity deltas, original bone parenting/rest matrices and all four static pose clips. New fibers retain 28 editable identity targets and selected weights in every pose. Scalp seam duplicates are compared to their original source vertices. Bald omits both roots and fibers.

Blender 5.2.3 imports the exact modified export with 53 body bones and nine skirt auxiliaries. Editing hair `HeadWide` moves vertices by 11.4 mm and `HeadLong` by 19.6 mm; a head-bone edit moves the hair by 21.3 mm. Expression, blink and brow editing also remains measurable. The imported Principled anisotropy is approximately 0.7. The imported character is saved as `artifacts/hair-editable.blend`; a Blender GLB re-export/re-import retains hair vertices, all 28 keys and anisotropy. That focused re-export excludes animations; the original browser export's four clips are validated separately.

Six unmodified-material Blender Cycles renders compare original/refined front, three-quarter and back. These use Blender lighting, shadows and AgX, so they are not pixel-matched browser screenshots. The authored hair shape and sheen survive, but renderer appearance differs. The existing skin shader remains browser-only; its PBR maps remain portable.

## Performance

The visible default character rises from 63,108 to 81,278 triangles (+28.8%). In the recorded 24-sample Apple M1 test, median CPU submission plus synchronous GPU completion was 2.8 ms for the original and 2.9 ms for the refined crop; 95th percentiles were 5.1 and 4.0 ms. A repeat run measured 0.4 ms medians for both versions, illustrating the variation in this environment. These are bounded draw measurements, **not interactive FPS or a device-independent performance guarantee**. Initial deterministic grooming and texture generation adds startup work and memory; the recorded runs took about 3.9–4.5 seconds. The final code caches repeated boundary calculations without changing output, but the later measured run did not demonstrate a startup speedup. The original baseline geometry is also retained in memory for comparison, so memory is higher than the old app.

## Reproduce

```sh
node server.mjs --port 4196 --qa-exports
# /tests/hair.html?auto&capture&exports
# /tests/hair.html?auto&capture&software
# /tests/expression-controls.html?capture
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python tools/validate-hair-export.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python tools/render-hair-export.py
npm run check
npm run build
```

The capture server remains localhost-only, same-origin, bounded, opt-in, exact-name and excluded from the static build. No publication or ZIP delivery is part of this prototype.
