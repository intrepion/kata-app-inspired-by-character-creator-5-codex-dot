# Regional skin material pass

Implementation `7c3970a`, based on expression milestone `af1477d`, was approved for publication on 2026-11-10.

## What changed

- One existing adult face with new 2048px color, pore-normal and roughness maps. Masks are baked from real neutral UV triangles, so facial regions follow the existing morphs and expressions without adding geometry.
- Modest warm cheek/nose/ear variation, a slightly cooler under-eye region, lower roughness around the nose/forehead/lips and more matte cheeks. Seeded pores vary across regions and are reduced at the lips and eyelids.
- A restrained directional, thin-tissue backlight term, strongest at the ears. This is an artistic, shadow-aware surface approximation, not volumetric subsurface scattering or a measured tissue model.
- Original and regional materials can be selected by the comparison fixture. Normal app use defaults to the new material. No project fields, expression algorithms, geometry, rigs or pose data changed.
- The interface and GLB material metadata explain the export boundary.

This is an incremental realism improvement, not a fully photorealistic character, a new skin scan or Character Creator parity. The existing stylized eyebrows, eye rendering, scalp texture, closed-mouth rig and coarse anatomy still limit close-up realism. There are no dynamic wrinkle maps or wetline changes.

## License check

The retained MakeHuman skin material header explicitly grants CC0. The original anatomical assets retain their existing verified CC0 grants. All new procedural map logic and shading code are MIT; no new third-party asset was fetched. `ASSET-LICENSES.md` and the map provenance record document the result.

## Verified on the Mac

- Chrome hardware WebGL, ANGLE Metal / Apple M1. Eighteen captures cover original/new pairs at front, three-quarter and profile under identical studio, side and rim lights. No WebGL shader/console errors were recorded. `screenshots/persona-skin-comparison.png` is the full matrix; `persona-skin-closeup.png` shows the clearer front and side-light comparison.
- The actual exported GLB was loaded back into the same Three.js scene with the same camera, lighting and environment. Three-quarter rim, profile rim and a smiling side-lit view were compared. Mean channel differences were below 0.30/255 over the full image. The difference includes export normal/texture resampling and loss of the browser shader; it is not a scattering-only measurement. `screenshots/persona-skin-transfer.png` includes amplified differences.
- The software preview loads the maps and retains the real edited geometry. Its flat/reduced lighting does not implement normal/roughness response or the skin shader and is not a photorealism test.
- All 99 expression UI checks pass on the changed app, covering independent sliders, reset, repeated operations, undo/redo, cancelled import, actual in-memory project save/open, old project compatibility, invalid inputs, reload and 390px layout.
- Full syntax and Node regression suite: 108 passed. `npm run build` passes. The generated static build includes all skin textures and provenance; its face preview was opened through localhost and showed no console errors. Browser testing used `http://127.0.0.1` only; no file URLs were opened.

## Actual exported data and Blender

The browser produced baseline, regional-neutral and regional-expression/skirt-stride GLBs. An independent validator checks their captured hashes, all original geometry/topology/UV/weight/morph buffers, selected eye/expression weights, and all four static pose clips. The retained source GLB and packed Blender source have unchanged SHA-256 hashes.

Blender 5.2.3 imports the actual expression/skirt export and confirms:

- 53 original body bones plus nine independent skirt auxiliaries.
- Editable body/garment bones, head-width morph, smile, frown, brow, blink and gaze targets with measured vertex movement.
- The three 2048px skin maps have exact decoded pixel equivalence after browser export and Blender import. The roughness map is packed into the glTF metallic-roughness texture's green channel.
- Imported Principled Subsurface Weight and Transmission Weight are both zero. No fake `KHR_materials_volume` or transmission extension is used to imply portable scattering.
- The editable reimport is saved as `artifacts/skin-editable.blend`.

Six Blender Cycles renders of the baseline/regional exports provide front and backlit three-quarter/profile checks without fixing or enhancing the imported materials. Hair was hidden for skin inspection. These use Blender's lights, world and AgX, so they are not pixel-matched to the browser. The pore/color/roughness improvement remains; the browser backlight term is absent. The shader is **not** portable to Blender simply because the textures and rig are portable.

The existing advice for editable exports still applies: clear shape-key animation before freely changing keys, or the static pose action can restore stored weights. Identity-fitted eye/expression targets may need refitting if identity keys are edited outside the app.

## Reproduce

```sh
node server.mjs --port 4194 --qa-exports
# http://127.0.0.1:4194/tests/skin.html?auto&capture&exports
# http://127.0.0.1:4194/tests/skin-transfer.html
# http://127.0.0.1:4194/tests/expression-controls.html?capture
# http://127.0.0.1:4194/tests/skin.html?auto&capture&software
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python tools/validate-skin-export.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python tools/render-skin-export.py
npm run check
npm run build
```

Rebuild the deterministic maps with Blender and `tools/build-skin.py`; this reads but does not save over the packed source. The evidence capture endpoints are exact-name, same-origin, loopback-only, bounded and opt-in. They are not copied into the static production build.
