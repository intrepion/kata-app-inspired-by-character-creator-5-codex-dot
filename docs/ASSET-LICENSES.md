# Human foundation asset provenance

## Scope

`assets/human/foundation.glb` is a reusable adult human built with MakeHuman/MPFB anatomical topology. `assets/source/foundation.blend` retains the weighted rig, UVs, editable shape keys, separate outfit, trousers, hair and eyes, and four pose actions. The model is a fictional composite, not a scan of an identified person. No third-party community wardrobe or hair was assumed to be free.

## Verified sources

- **Base mesh, macro targets, face/body targets, game-engine rig, skinning weights, clothing and scalp helper topology:** [MakeHuman Community MPFB2](https://github.com/makehumancommunity/mpfb2/tree/6ff1eb358f6c1959ced77e79e6dd2406d9a71f49), commit `6ff1eb358f6c1959ced77e79e6dd2406d9a71f49`. Asset license **CC0 1.0**. The repository's `LICENSE.md`, section C, explicitly covers meshes, targets, textures, clothes, rigs, poses, expressions and mesh metadata. The base OBJ also declares its September 2020 CC0 release. The code is GPLv3; it is a build-time dependency, not shipped as application code. Saved/exported output is addressed separately in section D.
- **Eye geometry, fitting data and original foundation brown eye texture (the portrait build replaces its material):** [MakeHuman](https://github.com/makehumancommunity/makehuman/tree/a8bc2d54ff0ac92e78ff71431b1023eda42bf482/makehuman/data/eyes), commit `a8bc2d54ff0ac92e78ff71431b1023eda42bf482`. `high-poly/high-poly.mhclo` and `materials/brown.mhmat` explicitly declare **CC0**. The corresponding OBJ and `brown_eye.png` are the referenced assets.
- **UV skin texture:** `skins/young_caucasian_male/young_lightskinned_male_diffuse.png` from the official [MakeHuman system assets CC0 pack](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html), downloaded November 2026. The material file explicitly declares the September 2020 **CC0** release and references this exact PNG. The material name internally says `old_caucasian_male_detailed`, but its directory, tags and diffuse reference identify the young adult texture; filename provenance is preserved here rather than rewritten. This is an original MakeHuman texture, not a generated skin approximation.

The explicit copyright holders identified in MakeHuman's asset headers at the time of CC0 release were Data Collection AB, Joel Palmius, and Jonas Hauquier. Attribution is retained as provenance although CC0 does not require it.

## Authored derivatives

- `Outfit` and `Pants` are new fitted sportswear surfaces extracted and offset from MPFB's CC0 `helper-tights` topology, with preserved UVs, source skinning weights and the same body shape keys. They are separate meshes, not recolored body faces.
- `HairCrop` is an original cropped scalp shell derived from the continuous CC0 anatomical head surface. The portrait revision fits this underlay closer to skin and adds an original dithered fade and tapered ribbon fibers. It is not a production strand groom.
- Pose actions `relaxed`, `tpose`, `wave`, `stride`, material choices and target combinations are authored for this project. The asset derivatives are provided under CC0 to the extent any rights subsist.

License evidence is retained under `assets/source/licenses/`, including the complete CC0 text, MPFB license explanation, exact skin material header and official pack manifest. The portrait runtime GLB embeds skin, procedural detail, iris and hair images. No runtime network request is needed.

## Rebuild and validation

Requires Blender 4.3+ and git. Run `tools/rebuild-human.sh` to fetch the pinned upstream source dependencies and rebuild. The skin PNG and license evidence are retained locally; the large system ZIP is not needed for rebuilding. The direct Python build script uses `MPFB_SOURCE` and `MH_SOURCE` if already available. Nothing is published or pushed by these scripts.

`tools/validate-human.py` reimports the GLB into Blender, verifies topology/UVs/weights/morphs/animations/images, edits a jaw morph and forearm bone, and checks evaluated vertex movement. `assets/human/qa.json` is its machine-readable result. `tools/roundtrip-human.py` separately validates the exact UI-downloaded Fern GLB, checks the Botanist preset morphs, hair omission, effective world-space height scaling, active wave pose against source geometry, and editable jaw/forearm deformation; it writes `docs/BLENDER-ROUNDTRIP.json`. Browser visual checks must use a running localhost HTTP server, never `file://`.

## Known boundaries

This is a foundational neutral adult with a small set of moderate morph ranges, not a full demographic library or production facial animation rig. Skin color tinting does not change anatomical ancestry. The outfit is fitted prototype sportswear, not simulated cloth. Height is whole-character scaling. Face controls use authored MakeHuman targets; body controls also propagate to the clothing. Eye geometry is fitted in the source rest shape, so eye-size adjustments are deliberately modest. Additional extreme/custom shape combinations require collision and rig-fit review.

## Original portrait additions (November 2026)

`tools/portrait-human.py` generates all new portrait maps and attachments from deterministic numeric functions and authored curves. No external image, proprietary Character Creator content, community hair asset, or likeness was downloaded. These new additions and their generator are provided under the repository MIT license. Existing foundation components retain their CC0 terms.

- `portrait_skin_normal.png`, `portrait_skin_roughness.png`: seeded microdetail, layered on the unchanged CC0 diffuse texture. Not a scan or biological skin simulation.
- `portrait_hair.png`, `portrait_hair_cap.png`, `portrait_hair_roughness.png`, `portrait_brow.png`: original seeded grayscale strand/detail textures and a scalp-boundary fade.
- `portrait_iris.png`: radial fibers, pupil and limbal ring without a painted catchlight.
- `HairStrands`, `Brows`, `Lashes`, `Iris`, `Cornea`: original generated geometry, fitted to the licensed foundation and assigned inherited skin weights. Brows/lashes retain facial morphs.
- Neutral reflection cards are generated in Three.js. No HDR environment photograph is bundled.

Run `blender -b --python-exit-code 1 --python tools/portrait-human.py` to apply the repeatable portrait layer to the retained source. The full rebuild script runs it after regenerating the foundation. Four existing poses and all approved body/garment buffers are preserved.

## Original distinct-face additions (November 2026)

`tools/distinct-faces.py` creates nine paired geometric controls using original, deterministic shared-space deformation fields. The same fields deform the body head, sclera, iris, cornea, brows, lashes, scalp and hair fibers. All 18 new targets, three new preset recipes and their generator are MIT. The underlying CC0 anatomy, original MIT portrait textures and attachments retain their existing terms. No new third-party assets, image downloads or likenesses are used.

Neutral source shape weights are explicitly zero. The added controls preserve the original geometry, UVs, skin weights, prior shape targets, materials and embedded image bytes from portrait commit `3a5fb77`; automated snapshot tests cover all ten meshes and eight embedded images. The roughness PNG post-process removes Blender-added color-profile metadata from linear data maps without changing compressed pixels.

## Original auxiliary skirt (local milestone, November 2026)

`src/skirt-rig.js` authors an original parametric A-line surface, UVs, build-fit morphs, auxiliary bone placements and normalized garment-only weights. The fit references the existing CC0 trousers contour without changing it. The new generator, garment topology and auxiliary pose/weight data are MIT under this repository's license. No TailorRig dataset, model, code, output or demo asset is included or used. No new third-party asset, texture, scan or likeness is downloaded. Existing human/portrait asset licenses are unchanged.

The optional skirt is built locally in the runtime and retained in GLB exports; the existing `foundation.glb` and `foundation.blend` are byte-identical to the distinct-face baseline. See `docs/QA-SKIRT.md` for independent body-rig preservation and Blender editing evidence.

## Original blink and gaze controls

`src/eye-rig.js` adds original MIT runtime deformation code and fitted export targets. No new external or Reallusion assets are used. The retained `assets/human/foundation.glb` and `assets/source/foundation.blend` remain byte-identical to the prior milestone; their original licenses above still apply.

## Original expression prototype

The expression deformation fields in `src/expression-rig.js`, tests and interface additions are original MIT application code. No external assets were added. The retained CC0 foundation GLB and packed Blender source are unchanged; only runtime/exported meshes receive new named targets. No proprietary facial poses, textures or topology were copied.

## Original regional skin pass (local prototype, November 2026)

`tools/build-skin.py` creates four 2048px maps in `assets/human/skin/` from the retained CC0 skin and neutral UV geometry. It rasterizes actual UV triangles into anatomical coordinates and authors smooth cheek, forehead, nose, lip, under-eye and ear regions. Seeded pore depressions, subtle color modulation, varying roughness and a thin-tissue mask are original MIT additions. No new third-party photograph, scan, model, likeness, texture, service or proprietary Character Creator asset was downloaded. The exact retained skin material header still explicitly grants CC0; `assets/source/licenses/skin.mhmat`, `CC0.txt` and the MPFB license explanation remain bundled.

The derived diffuse combines CC0 source pixels with original MIT processing. Normal, roughness and thin-tissue maps and their generator are original MIT. `assets/human/skin/provenance.json` records the seed, image hashes and unchanged foundation GLB hash. The packed foundation `.blend` and `.glb` were not rewritten. GLB exports embed the new PBR maps; the browser shader itself is not portable glTF SSS. See [skin verification and transfer limits](QA-SKIN.md).
