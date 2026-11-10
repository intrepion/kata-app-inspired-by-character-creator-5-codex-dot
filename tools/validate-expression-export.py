"""Independent expression GLB validation; optional headless Blender reimport.
python3 tools/validate-expression-export.py --self-test
Blender -b --python-exit-code 1 --python tools/validate-expression-export.py --
Accepts --capture-report PATH, --output-report PATH, and --structure-only.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('eye_validator', ROOT/'tools/validate-eye-export.py')
eye = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eye)
base, GLB, require, near = eye.base, eye.GLB, eye.require, eye.near
TARGETS = ['Smile','Frown','BrowRaise','BrowFurrow']
PARTS = ['HumanBody','Brows']


def expression_weights(project):
    values = [max(0,min(1,project.get(key,0))) for key in ['smile','frown','browRaise','browFurrow']]
    s,f,r,b = values
    return [max(0,s-f),max(0,f-s),max(0,r-b),max(0,b-r)]


def effective_project(project):
    result = dict(project)
    squint = .12*expression_weights(project)[0]
    for key in ['blinkLeft','blinkRight']:
        blink = max(0,min(1,project.get(key,0)))
        result[key] = blink+squint*(1-blink)
    return result


def without_expressions(doc):
    result = copy.copy(doc)
    result.g = copy.deepcopy(doc.g)
    result.cache = dict(doc.cache)
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
        for owner in [node,mesh]:
            if 'weights' in owner:
                owner['weights'] = [owner['weights'][i] for i in keep]
        mesh['extras']['targetNames'] = [names[i] for i in keep]
    return result


def validate(doc,source,project):
    expected = expression_weights(project)
    details = {}
    for name in PARTS:
        node,mesh = doc.mesh(name)
        names = mesh['extras']['targetNames']
        require(names[-4:] == TARGETS and len(set(names)) == len(names),'Missing/duplicate expression targets: '+name)
        weights = node.get('weights',mesh.get('weights',[]))
        require(len(weights) == len(names) and near(weights[-4:],expected),'Wrong selected expression weights: '+name)
        maxima = {}
        for primitive in mesh['primitives']:
            positions = doc.accessor(primitive['attributes']['POSITION'])
            require(len(primitive['targets']) == len(names),'Expression target dimensions')
            for target_name,target in zip(TARGETS,primitive['targets'][-4:]):
                delta = doc.accessor(target['POSITION'])
                normal = doc.accessor(target['NORMAL'])
                require(len(delta) == len(normal) == len(positions),'Expression attribute dimensions')
                maximum = max(abs(x) for x in delta)
                maxima[target_name] = maximum
                require(maximum < .05,'Expression movement exceeds 5cm: '+target_name)
                # Expressions must not move neck, body, back of skull, or clothing.
                for i in range(0,len(delta),3):
                    if positions[i+1] < 1.30 or positions[i+2] < .05:
                        require(delta[i:i+3] == [0,0,0],'Expression moves outside face: '+name+'/'+target_name)
                if name == 'HumanBody' or target_name.startswith('Brow'):
                    require(maximum > .0001,'Empty expression: '+name+'/'+target_name)
        for clip in doc.g['animations']:
            sampler = base.channels(doc,clip)[(name,'weights')]
            times,values = doc.accessor(sampler['input']),doc.accessor(sampler['output'])
            require(len(values) == len(times)*len(names),'Expression clip dimensions')
            for frame in range(len(times)):
                require(near(values[(frame+1)*len(names)-4:(frame+1)*len(names)],expected),'Pose changes expression: '+clip['name'])
        details[name] = {'selectedWeights':weights[-4:],'maximumAbsoluteDeltasMeters':maxima}
    result = eye.validate(without_expressions(doc),source,effective_project(project))
    result['expressions'] = details
    return result


def blender_checks(doc,output):
    # Includes texture pixel equivalence, existing blink/gaze editability and rig checks.
    result = eye.blender_checks(doc,output)
    import bpy
    def obj(material):
        matches = [o for o in bpy.data.objects if o.type == 'MESH' and any(m and m.name == material for m in o.data.materials)]
        require(len(matches) == 1,'Ambiguous imported material '+material)
        return matches[0]
    def vertices(ob):
        bpy.context.view_layer.update()
        evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]
    edits = {}
    for name in PARTS:
        ob = obj('Skin' if name == 'HumanBody' else name)
        node,mesh = doc.mesh(name)
        blocks = ob.data.shape_keys.key_blocks
        require(set(TARGETS) <= set(blocks.keys()),'Blender lost expression targets')
        for target,value in zip(mesh['extras']['targetNames'],node.get('weights',mesh.get('weights',[]))):
            require(abs(blocks[target].value-value) < 1e-6,'Blender changed selected target '+target)
        for target in (TARGETS if name == 'HumanBody' else TARGETS[2:]):
            shape = blocks[target]; old = shape.value
            before = vertices(ob)
            shape.value = 0 if old > .5 else 1
            after = vertices(ob)
            delta = max((a-b).length for a,b in zip(before,after))
            shape.value = old
            require(delta > .0001,'Imported expression is not editable: '+name+'/'+target)
            edits[name+'/'+target] = delta
    result['expressionEditMaximumDeltaMeters'] = edits
    return result


def self_test():
    require(expression_weights({}) == [0,0,0,0],'Neutral oracle')
    require(expression_weights(dict(smile=.8,frown=.3,browRaise=.1,browFurrow=.7)) == [.5,0,0,.6],'Opposition oracle')
    require(expression_weights(dict(smile=3,frown=-2,browRaise=-1,browFurrow=4)) == [1,0,0,1],'Clamp oracle')
    require(near([effective_project(dict(smile=1,blinkLeft=.5))['blinkLeft']],[.56]),'Squint oracle')
    print(json.dumps({'passed':True,'oracleCases':4,'sourceHashes':base.source_hashes()}))


def main():
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--structure-only',action='store_true')
    parser.add_argument('--capture-report',default=str(ROOT/'artifacts/expression-export-report.json'))
    parser.add_argument('--output-report',default=str(ROOT/'artifacts/expression-export-validation.json'))
    options = parser.parse_args(args)
    if options.self_test: self_test(); return
    capture_path,output = Path(options.capture_report),Path(options.output_report)
    report = {'passed':False,'verified':[],'sourceHashesBefore':base.source_hashes(),'limits':['Identity-fitted expression endpoints need refitting after external identity edits.','Four static pose clips retain selected expression weights; no speech, jaw rig, or continuous facial animation is authored.','Numerical locality checks are not an exhaustive collision proof.']}
    try:
        capture = json.loads(capture_path.read_text())
        require(capture.get('passed') is True and capture.get('exportPassed',True) is True,'Browser capture failed')
        source = GLB(ROOT/'assets/human/foundation.glb')
        docs = []
        require(len(capture['exports']) >= 3,'At least neutral and two expression exports required')
        for item in capture['exports']:
            doc = GLB(capture_path.parent/item['capture']['name'])
            require(doc.sha == item['capture']['sha256'] and len(doc.raw) == item['capture']['bytes'],'Capture hash/size mismatch')
            report['verified'].append(validate(doc,source,item['project']))
            docs.append((doc,item['project']))
        neutral = [p for d,p in docs if not any(expression_weights(p))]
        require(neutral,'Missing neutral export')
        doc,project = next((d,p) for d,p in docs if any(expression_weights(p)))
        rejected = []
        for mutation in ['missingClip','badName','badWeight','bodyTopology']:
            bad = copy.copy(doc); bad.g = copy.deepcopy(doc.g); bad.cache = dict(doc.cache)
            node,mesh = bad.mesh('HumanBody')
            if mutation == 'missingClip': bad.g['animations'].pop()
            elif mutation == 'badName': mesh['extras']['targetNames'][-1] = 'BadName'
            elif mutation == 'badWeight': (node if 'weights' in node else mesh)['weights'][-1] += .2
            else:
                index = mesh['primitives'][0]['indices']
                values = list(bad.accessor(index)); values[0] += 1; bad.cache[index] = values
            try: validate(bad,source,project)
            except AssertionError: rejected.append(mutation)
            else: raise AssertionError('Negative control accepted: '+mutation)
        report['negativeControlsRejected'] = rejected
        if not options.structure_only:
            doc,project = next((d,p) for d,p in docs if p.get('lowerGarment') == 'skirt' and any(expression_weights(p)))
            report['blender'] = blender_checks(doc,capture_path.parent/'expression-editable.blend')
        else: report['limits'].append('Blender reimport and texture checks not run in structure-only mode.')
        report['sourceHashesAfter'] = base.source_hashes()
        report['passed'] = True
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        output.write_text(json.dumps(report,indent=2)+'\n')
        raise
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__': main()
