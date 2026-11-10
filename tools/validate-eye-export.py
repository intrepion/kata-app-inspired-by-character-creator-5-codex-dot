"""Independent eye GLB validation and headless Blender editability checks.
Run python3 tools/validate-eye-export.py --self-test or --structure-only.
Run Blender -b --python-exit-code 1 --python tools/validate-eye-export.py for full QA.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('skirt_validator', ROOT/'tools/validate-skirt-export.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
GLB, require, near = base.GLB, base.require, base.near
TARGETS = ['BlinkLeft','BlinkRight','GazeLeft','GazeRight','GazeUp','GazeDown','BlinkLeftGazeUp','BlinkLeftGazeDown','BlinkRightGazeUp','BlinkRightGazeDown']
PARTS = ['HumanBody','Lashes','Eyes','Iris','Cornea']


def eye_weights(project):
    clamp = lambda x,a,b: max(a,min(b,x))
    left,right = [clamp(project.get(k,0),0,1) for k in ['blinkLeft','blinkRight']]
    h,v = [clamp(project.get(k,0),-1,1) for k in ['gazeHorizontal','gazeVertical']]
    up,down = max(0,v),max(0,-v)
    return [left,right,max(0,-h),max(0,h),up,down,left*up,left*down,right*up,right*down]


def without_eyes(doc):
    """Project appended eye channels away to reuse all original skirt/body checks."""
    result = copy.copy(doc)
    result.g = copy.deepcopy(doc.g)
    result.cache = copy.deepcopy(doc.cache)
    for name in PARTS:
        node,mesh = result.mesh(name)
        names = mesh['extras']['targetNames']
        keep = [i for i,n in enumerate(names) if n not in TARGETS]
        for clip in result.g['animations']:
            sampler = base.channels(result,clip)[(name,'weights')]
            values = doc.accessor(sampler['output'])
            result.cache[sampler['output']] = [values[offset+i] for offset in range(0,len(values),len(names)) for i in keep]
        for primitive in mesh['primitives']:
            primitive['targets'] = [primitive['targets'][i] for i in keep]
        for obj in [node,mesh]:
            if 'weights' in obj:
                obj['weights'] = [obj['weights'][i] for i in keep]
        mesh['extras']['targetNames'] = [names[i] for i in keep]
    return result


def validate(doc,source,project):
    expected = eye_weights(project)
    eye_report = {}
    for name in PARTS:
        node,mesh = doc.mesh(name)
        names = mesh['extras']['targetNames']
        require(names[-10:] == TARGETS and len(set(names)) == len(names), 'Missing/duplicate eye morphs: '+name)
        weights = node.get('weights',mesh.get('weights',[]))
        require(near(weights[-10:],expected), 'Wrong selected eye/corrective weights: '+name)
        maxima = {}
        for primitive in mesh['primitives']:
            attrs = primitive['attributes']
            require(len(primitive['targets']) == len(names),'Target dimensions')
            for target_name,target in zip(names[-10:],primitive['targets'][-10:]):
                delta = doc.accessor(target['POSITION'])
                require(len(delta) == len(doc.accessor(attrs['POSITION'])),'Eye delta dimensions')
                maxima[target_name] = max(abs(x) for x in delta)
            if name in ['HumanBody','Lashes']:
                require(maxima['BlinkLeft'] > .0001 and maxima['BlinkRight'] > .0001,'Empty eyelid blink')
                for i in range(4):
                    correction = doc.accessor(primitive['targets'][-4+i]['POSITION'])
                    follow = doc.accessor(primitive['targets'][names.index('GazeUp' if i%2 == 0 else 'GazeDown')]['POSITION'])
                    positions = doc.accessor(attrs['POSITION'])
                    sign = 1 if i<2 else -1
                    wanted = [-follow[j] if positions[j//3*3]*sign > 0 else 0 for j in range(len(follow))]
                    require(near(correction,wanted,2e-7),'Incorrect eyelid gaze cancellation: '+name)
                    correction_normal = doc.accessor(primitive['targets'][-4+i]['NORMAL'])
                    follow_normal = doc.accessor(primitive['targets'][names.index('GazeUp' if i%2 == 0 else 'GazeDown')]['NORMAL'])
                    wanted_normal = [-follow_normal[j] if positions[j//3*3]*sign > 0 else 0 for j in range(len(follow_normal))]
                    require(correction_normal == wanted_normal,'Corrective normals do not exactly cancel gaze normals: '+name)
            else:
                require(all(maxima[k] > .0001 for k in TARGETS[2:6]),'Empty eye rotation')
                require(all(maxima[k] == 0 for k in TARGETS[:2]+TARGETS[6:]),'Blink deforms eyeball')
        for clip in doc.g['animations']:
            sampler = base.channels(doc,clip)[(name,'weights')]
            times,values = doc.accessor(sampler['input']),doc.accessor(sampler['output'])
            require(len(values) == len(times)*len(names),'Clip shape count')
            for frame in range(len(times)):
                require(near(values[frame*len(names)+len(names)-10:(frame+1)*len(names)],expected),'Pose changes eye expression: '+clip['name'])
        eye_report[name] = {'selectedWeights':weights[-10:],'maximumAbsoluteDeltasMeters':maxima}
    result = base.validate_structure(without_eyes(doc),source,project)
    source_meshes = {n for n,i in source.names.items() if 'mesh' in source.g['nodes'][i]}
    require(source_meshes-({'Pants'} if project.get('lowerGarment') == 'skirt' else set()) <= set(doc.names),'Original attachment/garment missing')
    require(len(doc.g.get('images',[])) == len(source.g.get('images',[])), 'Texture count changed')
    normal_error = morph_normal_error = 0
    for name in result['preservedBodyMeshes']:
        _,sm = source.mesh(name); _,dm = doc.mesh(name)
        for sp,dp in zip(sm['primitives'],dm['primitives']):
            normal_error = max(normal_error,max(abs(a-b) for a,b in zip(source.accessor(sp['attributes']['NORMAL']),doc.accessor(dp['attributes']['NORMAL']))))
            for st,dt in zip(sp.get('targets',[]),dp.get('targets',[])):
                if 'NORMAL' in st:
                    morph_normal_error = max(morph_normal_error,max(abs(a-b) for a,b in zip(source.accessor(st['NORMAL']),doc.accessor(dt['NORMAL']))))
    require(normal_error < 2e-7 and morph_normal_error < 2e-7,'Original normals changed')
    result['maxOriginalNormalDifference'] = normal_error
    result['maxOriginalMorphNormalDifference'] = morph_normal_error
    result['eyes'] = eye_report
    return result


def blender_checks(doc,output):
    import bpy
    import numpy as np
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str((ROOT/'assets/human/foundation.glb').resolve()))
    def image_pixels():
        result = []
        for i in bpy.data.images:
            if not (i.packed_file or i.packed_files): continue
            values = np.rint(np.clip(np.array(i.pixels[:]),0,1)*255).astype(np.uint8).reshape(-1,4)
            raw = hashlib.sha256(values.tobytes()).hexdigest()
            # Canvas PNG serialization may clear RGB under fully transparent texels.
            # Alpha and every visible texel must still remain exactly identical.
            values[values[:,3] == 0,:3] = 0
            result.append((tuple(i.size),hashlib.sha256(values.tobytes()).hexdigest(),raw))
        return sorted(result)
    original_images = image_pixels()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(doc.path.resolve()))
    exported_images = image_pixels()
    require([(s,v) for s,v,r in exported_images] == [(s,v) for s,v,r in original_images],'Decoded visible texture pixels/alpha changed')
    raw_texture_matches = sum(a[2] == b[2] for a,b in zip(original_images,exported_images))
    rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    bones = {b.name for r in rigs for b in r.data.bones}
    require(len(bones) == 62 and set(base.AUX) <= bones,'53 body + 9 skirt bones missing')
    def mesh_for(material):
        found = [o for o in bpy.data.objects if o.type == 'MESH' and any(m and m.name == material for m in o.data.materials)]
        require(len(found) == 1,'Ambiguous material '+material)
        return found[0]
    body,iris,skirt = mesh_for('Skin'),mesh_for('Iris'),mesh_for('Skirt')
    for name in PARTS:
        ob = mesh_for('Skin' if name == 'HumanBody' else name)
        require(set(TARGETS) <= set(ob.data.shape_keys.key_blocks.keys()),'Blender missing eye shapes')
        node,mesh = doc.mesh(name)
        for key,value in zip(mesh['extras']['targetNames'],node.get('weights',mesh.get('weights',[]))):
            require(abs(ob.data.shape_keys.key_blocks[key].value-value)<1e-6,'Blender changed selected shape '+key)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()))
    for ob in bpy.data.objects:
        ob.animation_data_clear()
        if ob.type == 'MESH' and ob.data.shape_keys:
            ob.data.shape_keys.animation_data_clear()
    def vertices(ob):
        bpy.context.view_layer.update()
        evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]
    def change(ob,key):
        before = vertices(ob)
        shape = ob.data.shape_keys.key_blocks[key]
        old = shape.value
        shape.value = 0 if old>.5 else 1
        after = vertices(ob)
        delta = max((a-b).length for a,b in zip(before,after))
        shape.value = old
        require(delta>.0001,'Blender shape not editable '+key)
        return delta
    blink = change(body,'BlinkLeft')
    gaze = change(iris,'GazeRight')
    require(all(body.vertex_groups[g.group].name not in base.AUX for v in body.data.vertices for g in v.groups if g.weight>0),'Body has skirt influences')
    require(all(skirt.vertex_groups[g.group].name in base.AUX for v in skirt.data.vertices for g in v.groups if g.weight>0),'Skirt has body influences')
    return {'version':bpy.app.version_string,'uniqueBones':len(bones),'bodyBones':53,'skirtBones':9,'decodedVisibleTexturePixelsAndAlphaUnchanged':True,'rawPixelIdenticalTextures':raw_texture_matches,'totalTextures':len(original_images),'textureSerializationNote':'Hair-cap fully transparent RGB is cleared by browser canvas serialization; every visible texel and alpha value are exact.','blinkBodyEditMaxDeltaMeters':blink,'gazeIrisEditMaxDeltaMeters':gaze,'savedBlend':str(output.relative_to(ROOT)),'savedBlendBytes':output.stat().st_size,'savedBlendSha256':hashlib.sha256(output.read_bytes()).hexdigest()}


def self_test():
    base.source_hashes()
    require(eye_weights({'blinkLeft':.25,'blinkRight':.75,'gazeHorizontal':1,'gazeVertical':-1}) == [.25,.75,0,1,0,1,0,.25,0,.75],'Corrective product oracle')
    require(eye_weights({'blinkLeft':4,'blinkRight':-2,'gazeHorizontal':-2,'gazeVertical':2}) == [1,0,1,0,1,0,1,0,0,0],'Clamp oracle')
    print(json.dumps({'passed':True,'oracleCases':2,'sourceHashes':base.source_hashes()}))


def main():
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    if '--self-test' in args:
        self_test(); return
    capture_path = ROOT/'artifacts/blink-export-report.json'
    output = ROOT/'artifacts/blink-export-validation.json'
    report = {'passed':False,'sourceHashesBefore':base.source_hashes(),'verified':[],'limits':['Eye targets are refitted when identity sliders change in the app. Editing identity shapes in Blender may require a refit.','Gaze endpoints are additive linear morph approximations, not exact simultaneous rotations. Four authored static pose clips preserve the selected expression; no continuous facial animation is authored.','Sampled blink coverage checks are separate browser/unit QA, not an exhaustive intersection proof.']}
    try:
        capture = json.loads(capture_path.read_text())
        require(capture.get('passed') is True and capture.get('exportPassed') is True,'Browser export report failed')
        source = GLB(ROOT/'assets/human/foundation.glb')
        docs = {}
        for name in ['blink-neutral.glb','blink-closed.glb','blink-gaze.glb']:
            item = next(e for e in capture['exports'] if e['capture']['name'] == name)
            doc = GLB(capture_path.parent/name); docs[name] = doc
            require(doc.sha == item['capture']['sha256'] and len(doc.raw) == item['capture']['bytes'],'Capture hash mismatch')
            report['verified'].append(validate(doc,source,item['project']))
        item = next(e for e in capture['exports'] if e['capture']['name'] == 'blink-gaze.glb')
        count = 0
        for mutation in ['missingClip','missingEyeMorph','badWeight']:
            bad = copy.copy(docs['blink-gaze.glb']); bad.g = copy.deepcopy(bad.g)
            node,mesh = bad.mesh('HumanBody')
            if mutation == 'missingClip': bad.g['animations'].pop()
            elif mutation == 'missingEyeMorph': mesh['extras']['targetNames'][-1] = 'BadName'
            else:
                owner = node if 'weights' in node else mesh
                owner['weights'][-1] += .2
            try: validate(bad,source,item['project'])
            except AssertionError: count += 1
            else: raise AssertionError('Negative control accepted '+mutation)
        report['negativeControlsRejected'] = count
        if '--structure-only' not in args:
            report['blender'] = blender_checks(docs['blink-gaze.glb'],ROOT/'artifacts/blink-editable.blend')
        else: report['limits'].append('Blender editability/texture pixel comparison not run in structure-only mode.')
        report['sourceHashesAfter'] = base.source_hashes()
        report['passed'] = True
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        output.write_text(json.dumps(report,indent=2)+'\n')
        raise
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
