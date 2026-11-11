"""Verify captured browser hair cards and a focused editable Blender roundtrip.

Blender -b --python-exit-code 1 --python tools/validate-hair-cards-export.py --
Plain Python supports --self-test and --structure-only. The exact four captured
GLBs are checked before Blender imports the extreme capture. Animation creation
is disabled only in that focused Blender import/export; all four browser pose
clips, bone transforms, and selected morph tracks are validated independently.
No source asset is modified. Outputs live under artifacts/.
"""
import argparse
from collections import Counter
import copy
import gc
from functools import lru_cache
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('expression_validator', ROOT/'tools/validate-expression-export.py')
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)
base, GLB, require, near = ex.base, ex.GLB, ex.require, ex.near
CARDS = ['HairGroom', 'HairCardRoot']
ORIGINAL_HAIR = {'HairCrop', 'HairStrands'}
FILES = ['hair-cards-baseline.glb', 'hair-cards-neutral.glb', 'hair-cards-extreme.glb', 'hair-cards-bald.glb']
MORPHS = dict(zip(
    ['build','shoulders','jaw','nose','eyes','headWidth','headHeight','cheeks','chin','noseWidth','noseProjection','eyeSpacing','browHeight','lips'],
    [('BuildNarrow','BuildBroad'),('ShouldersNarrow','ShouldersBroad'),('JawNarrow','JawBroad'),('NoseNarrow','NoseBroad'),('EyesSmall','EyesLarge'),('HeadNarrow','HeadWide'),('HeadShort','HeadLong'),('CheeksLean','CheeksFull'),('ChinShort','ChinLong'),('NoseWingsNarrow','NoseWingsWide'),('NoseRetracted','NoseProjected'),('EyesClose','EyesWide'),('BrowsLow','BrowsHigh'),('LipsThin','LipsFull')]
))


def source_hashes():
    result = base.source_hashes()
    for path in sorted((ROOT/'assets/human/hair-cards').glob('*')):
        if path.is_file() and path.suffix in {'.glb','.blend','.png','.json'}:
            result[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((ROOT/'assets/human/skin').glob('*.png')):
        result[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def selected_weights(node, mesh):
    return node.get('weights', mesh.get('weights', []))


def identity_weights(names, project):
    values = {}
    for key, pair in MORPHS.items():
        value = max(0, min(1, project.get(key, .5)))
        values[pair[0]], values[pair[1]] = max(0, 1-2*value), max(0, 2*value-1)
    require(set(names) == set(values) and len(names) == 28, 'Unexpected identity morph names')
    return [values[name] for name in names]


def verify_selected_tracks(doc, name, names, weights, subset=None):
    require(len(weights) == len(names), 'Selected morph dimensions: '+name)
    subset = list(range(len(names))) if subset is None else subset
    samples = 0
    for clip in doc.g.get('animations', []):
        mapping = base.channels(doc, clip)
        require((name, 'weights') in mapping, 'Missing morph clip: '+name+'/'+clip['name'])
        sampler = mapping[(name, 'weights')]
        times, values = doc.accessor(sampler['input']), doc.accessor(sampler['output'])
        require(times and len(values) == len(times)*len(names), 'Morph clip dimensions: '+name)
        for frame in range(len(times)):
            require(near([values[frame*len(names)+i] for i in subset], [weights[i] for i in subset]), 'Pose changes selected morph: '+name+'/'+clip['name'])
            samples += len(subset)
    return samples


def embedded_texture(doc, info, label):
    require(isinstance(info, dict) and 'index' in info, 'Missing texture: '+label)
    texture = doc.g['textures'][info['index']]
    require('source' in texture, 'Missing image source: '+label)
    image = doc.g['images'][texture['source']]
    require('bufferView' in image and 'uri' not in image, 'Texture is not embedded: '+label)
    require(image.get('mimeType') == 'image/png', 'Texture is not portable PNG: '+label)
    view = doc.g['bufferViews'][image['bufferView']]
    offset = view.get('byteOffset', 0)
    raw = doc.binary[offset:offset+view['byteLength']]
    require(raw[:8] == b'\x89PNG\r\n\x1a\n' and len(raw) >= 33, 'Invalid PNG: '+label)
    width, height = struct.unpack_from('>II', raw, 16)
    require(width > 0 and height > 0, 'Empty image: '+label)
    return {'image':image.get('name', str(texture['source'])), 'width':width, 'height':height, 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest(), 'pngColorType':raw[25]}


@lru_cache(maxsize=1)
def authored_asset():
    return GLB(ROOT/'assets/human/hair-cards/hair-cards.glb')


def authored_materials():
    authored = authored_asset()
    return {name:authored.g['materials'][authored.mesh(name)[1]['primitives'][0]['material']] for name in CARDS}


def verify_card_material(doc, material, name):
    require(material.get('alphaMode') == 'MASK', 'Hair alpha mode changed: '+name)
    require(abs(material.get('alphaCutoff', .5)-.38) < 1e-7, 'Hair alpha cutoff changed: '+name)
    require(material.get('doubleSided') is True, 'Hair cards are not double sided: '+name)
    anisotropy = material.get('extensions', {}).get('KHR_materials_anisotropy', {})
    expected = authored_materials()[name]['extensions']['KHR_materials_anisotropy']
    require(expected['anisotropyStrength'] > 0 and abs(anisotropy.get('anisotropyStrength', 0)-expected['anisotropyStrength']) < 1e-6, 'Hair anisotropy changed: '+name)
    require(abs(material.get('pbrMetallicRoughness', {}).get('roughnessFactor', 1)-authored_materials()[name]['pbrMetallicRoughness']['roughnessFactor']) < 1e-6, 'Hair roughness changed: '+name)
    atlas = embedded_texture(doc, material.get('pbrMetallicRoughness', {}).get('baseColorTexture'), name+'/atlas')
    require(atlas['pngColorType'] in {4,6}, 'Hair atlas does not carry alpha: '+name)
    result = {'anisotropy':anisotropy, 'alphaMode':'MASK', 'alphaCutoff':material['alphaCutoff'], 'atlas':atlas}
    if name == 'HairGroom':
        result['normal'] = embedded_texture(doc, material.get('normalTexture'), name+'/normal')
        require(material['normalTexture'].get('scale', 1) > 0, 'Disabled hair normal texture')
    return result


def validate_face(doc, project):
    """Check appended channels without imposing the old hair/image inventory."""
    result = {'expressions':{}, 'eyes':{}}
    for parts, targets, wanted, group in [
        (ex.PARTS, ex.TARGETS, ex.expression_weights(project), 'expressions'),
        (ex.eye.PARTS, ex.eye.TARGETS, ex.eye.eye_weights(ex.effective_project(project)), 'eyes'),
    ]:
        for name in parts:
            node, mesh = doc.mesh(name)
            names = mesh['extras']['targetNames']
            require(len(set(names)) == len(names) and set(targets) <= set(names), 'Missing/duplicate face targets: '+name)
            indices = [names.index(n) for n in targets]
            weights = selected_weights(node, mesh)
            require(len(weights) == len(names) and near([weights[i] for i in indices], wanted), 'Selected face weights changed: '+group+'/'+name)
            maxima = {}
            for primitive in mesh['primitives']:
                positions = doc.accessor(primitive['attributes']['POSITION'])
                require(len(primitive['targets']) == len(names), 'Face target dimensions: '+name)
                for target_name, index in zip(targets, indices):
                    target = primitive['targets'][index]
                    delta, normal = doc.accessor(target['POSITION']), doc.accessor(target['NORMAL'])
                    require(len(delta) == len(normal) == len(positions), 'Face attribute dimensions: '+name+'/'+target_name)
                    maximum = max(abs(v) for v in delta)
                    maxima[target_name] = maximum
                    if group == 'expressions':
                        require(maximum < .05, 'Expression exceeds 5cm: '+target_name)
                        if name == 'HumanBody' or target_name.startswith('Brow'):
                            require(maximum > .0001, 'Empty expression: '+name+'/'+target_name)
                        for i in range(0, len(delta), 3):
                            if positions[i+1] < 1.30 or positions[i+2] < .05:
                                require(delta[i:i+3] == [0,0,0], 'Expression moves outside face: '+name+'/'+target_name)
                if group == 'eyes':
                    if name in ['HumanBody','Lashes']:
                        require(maxima['BlinkLeft'] > .0001 and maxima['BlinkRight'] > .0001, 'Empty eyelid blink')
                        for i, target_name in enumerate(targets[-4:]):
                            corrective = primitive['targets'][names.index(target_name)]
                            follow = primitive['targets'][names.index('GazeUp' if i%2 == 0 else 'GazeDown')]
                            sign = 1 if i < 2 else -1
                            for semantic in ['POSITION','NORMAL']:
                                a, b = doc.accessor(corrective[semantic]), doc.accessor(follow[semantic])
                                expected = [-b[j] if positions[j//3*3]*sign > 0 else 0 for j in range(len(b))]
                                require(near(a, expected, 2e-7), 'Eye corrective mismatch: '+name+'/'+target_name+'/'+semantic)
                    else:
                        require(all(maxima[k] > .0001 for k in targets[2:6]), 'Empty eye rotation')
                        require(all(maxima[k] == 0 for k in targets[:2]+targets[6:]), 'Blink deforms eyeball')
            samples = verify_selected_tracks(doc, name, names, weights, indices)
            result[group][name] = {'selectedWeights':[weights[i] for i in indices], 'maximumAbsoluteDeltasMeters':maxima, 'clipWeightSamplesCompared':samples}
    return result


def validate_hair_mesh(doc, source, name, project, cards=True):
    node, mesh = doc.mesh(name)
    names = mesh['extras']['targetNames']
    expected_names = source.mesh('HairCrop')[1]['extras']['targetNames']
    require(names == expected_names and len(names) == 28, 'Hair lost original 28 named identity keys: '+name)
    skin = doc.g['skins'][node['skin']]
    require(doc.joints(skin) == source.joints(source.g['skins'][0]), 'Hair is not bound to original 53 joints: '+name)
    require(near(doc.accessor(skin['inverseBindMatrices']), source.accessor(source.g['skins'][0]['inverseBindMatrices'])), 'Hair rest matrices changed: '+name)
    weights = selected_weights(node, mesh)
    require(near(weights, identity_weights(names, project)), 'Wrong selected hair identity weights: '+name)
    result = {'targets':names, 'selectedWeights':weights, 'clipWeightSamplesCompared':verify_selected_tracks(doc, name, names, weights), 'primitives':[]}
    vertices = triangles = 0
    for primitive in mesh['primitives']:
        attrs = primitive['attributes']
        require({'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'} <= attrs.keys(), 'Missing portable hair attributes: '+name)
        positions, normals = doc.accessor(attrs['POSITION']), doc.accessor(attrs['NORMAL'])
        uv = doc.accessor(attrs['TEXCOORD_0'])
        count = len(positions)//3
        require(count > 0 and len(normals) == len(positions) and len(uv) == count*2, 'Hair attribute dimensions: '+name)
        # Both the comparison cap and authored root unwrap a rear seam past
        # U=1 intentionally. Compare authored UVs exactly, including that seam.
        if cards:
            authored = authored_asset()
            original_uv = authored.mesh(name)[1]['primitives'][0]['attributes']['TEXCOORD_0']
            require(near(uv, authored.accessor(original_uv), 1e-7), 'Authored hair UVs changed: '+name)
        if cards and name == 'HairGroom':
            require(all(-1e-6 <= x <= 1+1e-6 for x in uv), 'Invalid hair UVs: '+name)
        indices = doc.accessor(primitive['indices'])
        require(len(indices)%3 == 0 and all(int(i) == i and 0 <= i < count for i in indices), 'Invalid hair topology: '+name)
        checks = base.weight_check(doc.accessor(attrs['WEIGHTS_0']), doc.accessor(attrs['JOINTS_0']), 53, 4)
        require(checks['vertices'] == count, 'Hair skin dimensions: '+name)
        require(len(primitive['targets']) == 28, 'Hair target count: '+name)
        maxima = {}
        for target_name, target in zip(names, primitive['targets']):
            require('POSITION' in target and len(doc.accessor(target['POSITION'])) == len(positions), 'Hair morph position dimensions: '+name+'/'+target_name)
            if 'NORMAL' in target:
                require(len(doc.accessor(target['NORMAL'])) == len(normals), 'Hair morph normal dimensions: '+name+'/'+target_name)
            maxima[target_name] = max(abs(x) for x in doc.accessor(target['POSITION']))
        require(maxima['HeadWide'] > .001 and maxima['HeadLong'] > .001, 'Hair head shape targets are empty: '+name)
        checks['maximumMorphDeltaMeters'] = maxima
        if cards:
            checks['material'] = verify_card_material(doc, doc.g['materials'][primitive['material']], name)
        result['primitives'].append(checks)
        vertices += count
        triangles += len(indices)//3
    require(vertices < 55000, 'Hair vertex budget exceeded: '+name)
    result.update(vertices=vertices, triangles=triangles)
    return result


def validate(doc, source, project, mode):
    nonhair_source = copy.copy(source)
    nonhair_source.names = {n:i for n,i in source.names.items() if n not in ORIGINAL_HAIR}
    stripped = ex.eye.without_eyes(ex.without_expressions(doc))
    result = base.validate_structure(stripped, nonhair_source, project)
    required = {'HumanBody','Outfit','Eyes','Iris','Cornea','Brows','Lashes','Skirt' if project.get('lowerGarment') == 'skirt' else 'Pants'}
    require(required <= set(doc.names), 'Original non-hair attachment missing')
    for name in result['preservedBodyMeshes']:
        _, original = source.mesh(name)
        _, actual = stripped.mesh(name)
        for a, b in zip(original['primitives'], actual['primitives']):
            require(near(source.accessor(a['attributes']['NORMAL']), doc.accessor(b['attributes']['NORMAL']), 2e-7), 'Original normals changed: '+name)
            require(len(a.get('targets', [])) == len(b.get('targets', [])), 'Original morph count changed: '+name)
            for ta, tb in zip(a.get('targets', []), b.get('targets', [])):
                if 'NORMAL' in ta:
                    require(near(source.accessor(ta['NORMAL']), doc.accessor(tb['NORMAL']), 2e-7), 'Original morph normals changed: '+name)
    result.update(validate_face(doc, project))
    hair_names = {n for n,i in doc.names.items() if 'mesh' in doc.g['nodes'][i] and n.startswith('Hair')}
    if project['hair'] == 'none':
        require(not hair_names, 'Bald export contains hair: '+str(hair_names))
        result['hair'] = {'bald':True, 'meshes':[]}
    elif mode == 'groom':
        require(hair_names == set(CARDS), 'Wrong visible hair-card meshes: '+str(hair_names))
        require('KHR_materials_anisotropy' in doc.g.get('extensionsUsed', []), 'Missing anisotropy declaration')
        result['hair'] = {name:validate_hair_mesh(doc, source, name, project) for name in CARDS}
    else:
        require(mode == 'procedural' and hair_names == {'HairCrop','HairProceduralGroom'}, 'Wrong rejected procedural comparison: '+str(hair_names))
        result['hair'] = {name:validate_hair_mesh(doc, source, name, project, cards=False) for name in sorted(hair_names)}
    return result


def blender_checks(doc, output_dir):
    import bpy
    import numpy as np
    # Blender 5.2 has no public animation-import toggle. Suppress only action
    # creation for the duration of the import and restore it in finally. The
    # captured bytes, meshes, skinning, materials, images and shapes are untouched.
    from io_scene_gltf2.blender.imp.scene import BlenderScene

    def import_static(path):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        original = BlenderScene.create_animations
        try:
            BlenderScene.create_animations = staticmethod(lambda gltf: None)
            bpy.ops.import_scene.gltf(filepath=str(path), import_pack_images=True)
        finally:
            BlenderScene.create_animations = staticmethod(original)

    def obj(name):
        material = 'Skin' if name == 'HumanBody' else name
        matches = [o for o in bpy.data.objects if o.type == 'MESH' and (o.name == name or any(m and m.name == material for m in o.data.materials))]
        require(len(matches) == 1, 'Ambiguous Blender mesh: '+name)
        return matches[0]

    def image_snapshot():
        cache = {}
        result = {}
        for material in bpy.data.materials:
            if not material.use_nodes:
                continue
            values = []
            for node in material.node_tree.nodes:
                if node.type != 'TEX_IMAGE' or not node.image:
                    continue
                im = node.image
                if im.name not in cache:
                    require(im.packed_file or im.packed_files, 'Blender image not packed: '+im.name)
                    pixels = rgba(im)
                    require(len(pixels) == im.size[0]*im.size[1], 'Blender image dimensions: '+im.name)
                    alpha = pixels[:,3]
                    pixels[alpha == 0,:3] = 0
                    cache[im.name] = {'name':im.name, 'size':list(im.size), 'visiblePixelSha256':hashlib.sha256(pixels.tobytes()).hexdigest(), 'transparentPixels':int((alpha == 0).sum()), 'opaquePixels':int((alpha == 255).sum()), 'rgbVaries':bool(np.any(pixels[:,:3] != pixels[0,:3]))}
                values.append(cache[im.name])
            result[material.name] = values
        return result

    def signature(images):
        return Counter((tuple(im['size']), im['visiblePixelSha256']) for im in images)

    def rgba(im):
        values = np.empty(len(im.pixels), dtype=np.float32)
        im.pixels.foreach_get(values)
        return np.rint(np.clip(values,0,1)*255).astype(np.uint8).reshape(-1,4)

    def texture_image(document, info):
        index = document.g['textures'][info['index']]['source']
        name = document.g['images'][index].get('name') or f'Image_{index}'
        require(name in bpy.data.images, 'Imported texture image missing: '+name)
        return bpy.data.images[name]

    def hair_pixels(document):
        result = {}
        for name in CARDS:
            material = document.g['materials'][document.mesh(name)[1]['primitives'][0]['material']]
            result[name+'/atlas'] = rgba(texture_image(document, material['pbrMetallicRoughness']['baseColorTexture']))
            if 'normalTexture' in material:
                result[name+'/normal'] = rgba(texture_image(document, material['normalTexture']))
        return result

    import_static(ROOT/'assets/human/foundation.glb')
    original_images = image_snapshot()
    import_static(ROOT/'assets/human/hair-cards/hair-cards.glb')
    authored_images = image_snapshot()
    expected_hair_pixels = hair_pixels(authored_asset())
    import_static(doc.path)
    imported_images = image_snapshot()
    for material in ['Outfit','Eyes','Iris','Cornea','Brows','Lashes']:
        require(material in imported_images and signature(imported_images[material]) == signature(original_images[material]), 'Original visible texture pixels/alpha changed: '+material)
    # The existing regional skin pass intentionally replaces foundation Skin.
    # Verify those current PNGs, not the obsolete foundation skin textures.
    skin = next(m for m in doc.g['materials'] if m['name'] == 'Skin')
    skin_checks = {}
    for filename, info, channel in [
        ('skin-color.png',skin['pbrMetallicRoughness']['baseColorTexture'],None),
        ('skin-normal.png',skin['normalTexture'],None),
        ('skin-roughness.png',skin['pbrMetallicRoughness']['metallicRoughnessTexture'],1),
    ]:
        im = texture_image(doc, info)
        original = bpy.data.images.load(str(ROOT/'assets/human/skin'/filename), check_existing=False)
        original.colorspace_settings.name = im.colorspace_settings.name
        a, b = rgba(original), rgba(im)
        require(a.shape == b.shape, 'Regional skin texture dimensions changed: '+filename)
        if channel is not None:
            a, b = a[:,channel], b[:,channel]
        require(np.array_equal(a,b), 'Regional skin texture pixels changed: '+filename)
        skin_checks[filename] = {'exactPixels':True,'channel':'RGBA' if channel is None else 'roughness G'}
        bpy.data.images.remove(original)
    actual_hair_pixels = hair_pixels(doc)
    hair_pixel_checks = {}
    for label, a in expected_hair_pixels.items():
        b = actual_hair_pixels[label]
        require(a.shape == b.shape, 'Hair texture dimensions changed: '+label)
        exact = bool(np.array_equal(a,b))
        alpha_equal = bool(np.array_equal(a[:,3],b[:,3]))
        opaque = a[:,3] == 255
        opaque_equal = bool(np.array_equal(a[opaque,:3],b[opaque,:3]))
        alpha = a[:,3].astype(np.float64)/255
        error = np.abs(a[:,:3].astype(np.float64)-b[:,:3])*alpha[:,None]
        maximum = float(error.max())
        # Canvas serializes through premultiplied alpha. At fractional coverage,
        # permit at most one 8-bit premultiplied RGB level, never altered alpha,
        # opaque color, or normal pixels. Report the measurement explicitly.
        require(alpha_equal and opaque_equal and maximum <= 1.000001, 'Hair texture visible pixels changed beyond canvas rounding: '+label)
        if label.endswith('/normal'):
            require(exact, 'Hair normal map pixels changed')
        hair_pixel_checks[label] = {'exactRgbaPixels':exact,'alphaExact':alpha_equal,'opaqueRgbExact':opaque_equal,'maxPremultipliedRgbDifference8Bit':maximum}
    for name in CARDS:
        require(any(i['transparentPixels'] > 0 and i['opaquePixels'] > 0 for i in imported_images[name]), 'Hair atlas lost visible/transparent pixels: '+name)
    require(len(imported_images['HairGroom']) >= 2 and all(i['rgbVaries'] for i in imported_images['HairGroom']), 'Hair atlas or normal detail missing')
    (output_dir/'hair-cards-texture-comparison.json').write_text(json.dumps({'regionalSkin':skin_checks,'hair':hair_pixel_checks,'importedMaterialImages':imported_images},indent=2)+'\n')
    del expected_hair_pixels, actual_hair_pixels
    print('PASS original non-skin textures, current regional skin maps, and authored hair textures', flush=True)

    rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    bones = {b.name for o in rigs for b in o.data.bones}
    require(len(bones) == 62 and set(base.AUX) <= bones, 'Blender lost original/skirt bones')
    require(not bpy.data.actions, 'Focused Blender import unexpectedly created animation actions')
    hair_objects = {name:obj(name) for name in CARDS}
    hair_report = {}
    for name, ob in hair_objects.items():
        node, mesh = doc.mesh(name)
        names, weights = mesh['extras']['targetNames'], selected_weights(node, mesh)
        require(set(ob.data.shape_keys.key_blocks.keys()) == {'Basis', *names}, 'Blender lost 28 editable hair keys: '+name)
        require(any(m.type == 'ARMATURE' for m in ob.modifiers), 'Hair not skinned in Blender: '+name)
        require(all(ob.vertex_groups[g.group].name in bones-set(base.AUX) for v in ob.data.vertices for g in v.groups if g.weight > 0), 'Hair has garment influences: '+name)
        for target, weight in zip(names, weights):
            require(abs(ob.data.shape_keys.key_blocks[target].value-weight) < 1e-6, 'Blender changed selected hair key: '+name+'/'+target)
        material = bpy.data.materials[name]
        bsdf = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        anisotropy = next(i for i in bsdf.inputs if i.name.startswith('Anisotropic') and 'Rotation' not in i.name)
        expected_anisotropy = authored_materials()[name]['extensions']['KHR_materials_anisotropy']['anisotropyStrength']
        require(abs(anisotropy.default_value-expected_anisotropy) < 1e-6, 'Blender lost anisotropy: '+name)
        hair_report[name] = {'vertices':len(ob.data.vertices), 'shapeKeys':list(ob.data.shape_keys.key_blocks.keys()), 'anisotropyInput':anisotropy.name, 'anisotropyValue':anisotropy.default_value, 'images':imported_images[name]}

    def points(ob):
        bpy.context.view_layer.update()
        evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return [evaluated.matrix_world@v.co for v in evaluated.data.vertices]

    edits = {}
    for name, key in [(name,key) for name in CARDS for key in ['HeadWide','HeadLong']] + [('HumanBody','Smile'),('HumanBody','BlinkLeft'),('Brows','BrowRaise'),('Iris','GazeRight')]:
        ob = obj(name)
        shape = ob.data.shape_keys.key_blocks[key]
        old, before = shape.value, points(ob)
        try:
            shape.value = 0 if old > .5 else 1
            after = points(ob)
            movement = max((a-b).length for a,b in zip(before,after))
            require(movement > .0001, 'Uneditable Blender morph: '+name+'/'+key)
            edits[name+'/'+key] = movement
        finally:
            shape.value = old
    armature = next(o for o in rigs if 'head' in o.pose.bones)
    head = armature.pose.bones['head']
    old_mode, old_matrix = head.rotation_mode, head.matrix_basis.copy()
    before = {name:points(ob) for name,ob in hair_objects.items()}
    try:
        head.rotation_mode = 'XYZ'
        head.rotation_euler.z += .12
        for name, ob in hair_objects.items():
            movement = max((a-b).length for a,b in zip(before[name],points(ob)))
            require(movement > .002, 'Head bone does not move hair: '+name)
            edits[name+'/headBone'] = movement
    finally:
        head.rotation_mode = old_mode
        head.matrix_basis = old_matrix
    bpy.context.view_layer.update()
    blend, roundtrip = output_dir/'hair-cards-editable.blend', output_dir/'hair-cards-blender-roundtrip.glb'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.export_scene.gltf(filepath=str(roundtrip), export_format='GLB', export_skins=True, export_morph=True, export_morph_normal=True, export_animations=False, export_extras=True)
    reexport = GLB(roundtrip)
    require(not reexport.g.get('animations'), 'Focused roundtrip unexpectedly contains clips')
    roundtrip_nodes = {}
    for name in CARDS:
        # Blender may reparent skinned geometry onto an armature and retain
        # the original node as an empty transform marker. Match the actual
        # mesh by its retained, unique material rather than that empty node.
        matches = [(node,reexport.g['meshes'][node['mesh']]) for node in reexport.g['nodes'] if 'mesh' in node and any(reexport.g['materials'][p['material']]['name'] == name for p in reexport.g['meshes'][node['mesh']]['primitives'])]
        require(len(matches) == 1, 'Roundtrip lost/duplicated hair mesh: '+name)
        node, mesh = matches[0]
        roundtrip_nodes[name] = node['name']
        require(mesh['extras']['targetNames'] == doc.mesh(name)[1]['extras']['targetNames'], 'Roundtrip lost hair target names: '+name)
        for primitive in mesh['primitives']:
            verify_card_material(reexport, reexport.g['materials'][primitive['material']], name)
    import_static(roundtrip)
    reimport_images = image_snapshot()
    for name in CARDS:
        ob = obj(name)
        require(len(ob.data.vertices) == hair_report[name]['vertices'], 'Roundtrip changed hair vertices: '+name)
        require(list(ob.data.shape_keys.key_blocks.keys()) == hair_report[name]['shapeKeys'], 'Roundtrip lost editable hair keys: '+name)
        require(any(m.type == 'ARMATURE' for m in ob.modifiers), 'Roundtrip lost hair skinning: '+name)
        require(signature(reimport_images[name]) == signature(imported_images[name]), 'Roundtrip changed hair image pixels: '+name)
        bsdf = next(n for n in bpy.data.materials[name].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        anisotropy = next(i for i in bsdf.inputs if i.name.startswith('Anisotropic') and 'Rotation' not in i.name)
        require(abs(anisotropy.default_value-hair_report[name]['anisotropyValue']) < 1e-6, 'Roundtrip lost Blender anisotropy: '+name)
        node, mesh = doc.mesh(name)
        for target, weight in zip(mesh['extras']['targetNames'], selected_weights(node,mesh)):
            require(abs(ob.data.shape_keys.key_blocks[target].value-weight) < 1e-6, 'Roundtrip changed selected hair key: '+name+'/'+target)
    return {'version':bpy.app.version_string, 'importedExactCaptureSha256':doc.sha, 'animationImportDisabled':True, 'animationExportDisabled':True, 'boneCount':len(bones), 'hair':hair_report, 'editableMovementMeters':edits, 'originalNonSkinTexturePixelsAndAlphaUnchanged':True, 'regionalSkinTextureChecks':skin_checks, 'authoredHairTextureChecks':hair_pixel_checks, 'reexportReimportPassed':True, 'roundtripMeshNodesByHairMaterial':roundtrip_nodes, 'savedBlend':str(blend.relative_to(ROOT)), 'editableBlendSha256':hashlib.sha256(blend.read_bytes()).hexdigest(), 'roundtrip':str(roundtrip.relative_to(ROOT)), 'roundtripSha256':reexport.sha}


def negative_controls(doc, source, project):
    rejected = []
    for mutation in ['missingClip','wrongHairName','wrongHairWeight','wrongBoneBind','missingNormalMap','wrongAlphaCutoff','bodyTopology','wrongExpressionWeight']:
        bad = copy.copy(doc)
        bad.g, bad.cache, bad.names = copy.deepcopy(doc.g), dict(doc.cache), dict(doc.names)
        node, mesh = bad.mesh('HairGroom')
        primitive = mesh['primitives'][0]
        material = bad.g['materials'][primitive['material']]
        if mutation == 'missingClip':
            bad.g['animations'].pop()
        elif mutation == 'wrongHairName':
            mesh['extras']['targetNames'][0] = 'InvalidIdentity'
        elif mutation == 'wrongHairWeight':
            (node if 'weights' in node else mesh)['weights'][0] += .2
        elif mutation == 'wrongBoneBind':
            index = bad.g['skins'][node['skin']]['inverseBindMatrices']
            values = list(bad.accessor(index)); values[12] += .1; bad.cache[index] = values
        elif mutation == 'missingNormalMap':
            material.pop('normalTexture')
        elif mutation == 'wrongAlphaCutoff':
            material['alphaCutoff'] = .9
        elif mutation == 'bodyTopology':
            index = bad.mesh('HumanBody')[1]['primitives'][0]['indices']
            values = list(bad.accessor(index)); values[0] += 1; bad.cache[index] = values
        else:
            body_node, body_mesh = bad.mesh('HumanBody')
            (body_node if 'weights' in body_node else body_mesh)['weights'][-4] += .2
        try:
            validate(bad, source, project, 'groom')
        except AssertionError as error:
            rejected.append({'mutation':mutation, 'rejectedBecause':str(error)})
        else:
            raise AssertionError('Negative control was accepted: '+mutation)
    return rejected


def self_test():
    names = [name for pair in MORPHS.values() for name in pair]
    require(identity_weights(names,{}) == [0]*28, 'Neutral identity oracle')
    wide = identity_weights(names,{'headWidth':1,'headHeight':0})
    require(wide[names.index('HeadWide')] == 1 and wide[names.index('HeadShort')] == 1 and sum(wide) == 2, 'Extreme identity oracle')
    require(identity_weights(names,{'headWidth':4}) == identity_weights(names,{'headWidth':1}), 'Identity clamp oracle')
    try:
        identity_weights(names[:-1], {})
    except AssertionError:
        pass
    else:
        raise AssertionError('Missing morph negative control accepted')
    print(json.dumps({'passed':True,'oracleCases':4}))


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--structure-only', action='store_true')
    parser.add_argument('--capture-report', default=str(ROOT/'artifacts/hair-cards-export-report.json'))
    parser.add_argument('--output-report', default=str(ROOT/'artifacts/hair-cards-validation.json'))
    options = parser.parse_args(argv)
    if options.self_test:
        self_test()
        return
    capture_path, output = Path(options.capture_report), Path(options.output_report)
    report = {'passed':False, 'structure':[], 'limits':['Four browser static pose clips are checked numerically against the source; no continuous or arbitrary animation is claimed.', 'Animation creation is disabled during the focused Blender import/export. The saved editable .blend and Blender roundtrip GLB do not contain the four browser pose clips.', 'The alpha-tested static cards are not simulated strands. These checks do not prove all possible collisions or receiving-renderer visual equivalence.', 'Expression and eye targets are identity-fitted in the app; later external identity editing may require refitting them.']}
    try:
        report['sourceHashesBefore'] = source_hashes()
        capture = json.loads(capture_path.read_text())
        require(capture.get('passed') is True and capture.get('exportPassed') is True, 'Browser capture/export incomplete')
        require(all(c.get('passed') for c in capture.get('checks', [])), 'Browser acceptance check failed')
        records = {item['capture']['name']:item for item in capture['exports']}
        require(set(records) == set(FILES) and len(capture['exports']) == len(FILES), 'Expected exactly the four hair-card browser exports')
        source, docs = GLB(ROOT/'assets/human/foundation.glb'), {}
        for filename in FILES:
            item = records[filename]
            doc = GLB(capture_path.parent/filename)
            require(doc.sha == item['capture']['sha256'] and len(doc.raw) == item['capture']['bytes'], 'Captured hash/size mismatch: '+filename)
            report['structure'].append(validate(doc, source, item['project'], item['mode']))
            print('PASS captured GLB structure, rig, face, hair and four clips: '+filename, flush=True)
            docs[filename] = doc
        require(records[FILES[0]]['mode'] == 'procedural' and records[FILES[1]]['mode'] == 'groom', 'Comparison modes not captured')
        extreme, project = docs[FILES[2]], records[FILES[2]]['project']
        require(project['headWidth'] == project['headHeight'] == 1 and project['pose'] == 'stride' and project['lowerGarment'] == 'skirt', 'Extreme identity/pose/garment case missing')
        require(near([project[k] for k in ['smile','browRaise','blinkLeft','gazeHorizontal']], [.7,.4,.6,.4]), 'Extreme face case missing')
        require(records[FILES[3]]['project']['hair'] == 'none' and records[FILES[3]]['project']['pose'] == 'wave', 'Bald wave case missing')
        report['negativeControlsRejected'] = negative_controls(extreme, source, project)
        print('PASS eight mutated-export negative controls', flush=True)
        if options.structure_only:
            report['limits'].append('Structure-only run: Blender import, pixel comparison, edits and roundtrip were not run.')
        else:
            print('Starting focused Blender pixel/edit/reexport/reimport checks', flush=True)
            # Free parsed accessor arrays from completed comparisons before
            # Blender constructs another full editable copy on this laptop.
            for parsed in [*docs.values(), source, authored_asset()]:
                parsed.cache.clear()
            docs.clear()
            gc.collect()
            report['blender'] = blender_checks(extreme, capture_path.parent)
        report['sourceHashesAfter'] = source_hashes()
        require(report['sourceHashesAfter'] == report['sourceHashesBefore'], 'A source asset changed during validation')
        report['passed'] = True
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        output.write_text(json.dumps(report, indent=2)+'\n')
        raise
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
