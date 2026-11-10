"""Independently verify exact browser exports, then reimport/edit them headlessly.

Blender -b --python-exit-code 1 --python tools/validate-skirt-export.py --
  [artifacts/skirt-report.json artifacts/skirt-export-validation.json]
Plain Python supports --structure-only and --self-test. Never opens a GUI or
modifies either foundation source. Saves a separate, untouched imported .blend.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
BODY_HASH = '642dc95643eca689266fce489bc87ac65377529af77c2e522c0326d87a9d79ab'
BLEND_HASH = '504164e65309c940446375fc28d7116baa0f83dfdd5425d50852c2d4ae5e40e5'
AUX = ['skirt_anchor'] + [f'skirt_panel_{i:02}' for i in range(1, 9)]
POSES = ['relaxed', 'stride', 'tpose', 'wave']


def require(value, message):
    if not value:
        raise AssertionError(message)


def near(a, b, tolerance=2e-6):
    return len(a) == len(b) and all(math.isfinite(x) and abs(x-y) <= tolerance for x, y in zip(a, b))


class GLB:
    def __init__(self, path):
        self.path = Path(path)
        self.raw = self.path.read_bytes()
        require(struct.unpack_from('<III', self.raw) == (0x46546c67, 2, len(self.raw)), 'Invalid GLB header')
        chunks, offset = {}, 12
        while offset < len(self.raw):
            length, kind = struct.unpack_from('<II', self.raw, offset)
            chunks[kind] = self.raw[offset+8:offset+8+length]
            offset += 8 + length
        self.g = json.loads(chunks[0x4e4f534a])
        self.binary = chunks[0x004e4942]
        self.sha = hashlib.sha256(self.raw).hexdigest()
        self.cache = {}
        self.names = {n['name']: i for i, n in enumerate(self.g['nodes']) if 'name' in n}
        self.parents = {child: i for i, n in enumerate(self.g['nodes']) for child in n.get('children', [])}

    def accessor(self, index):
        if index in self.cache:
            return self.cache[index]
        a = self.g['accessors'][index]
        components = {'SCALAR':1, 'VEC2':2, 'VEC3':3, 'VEC4':4, 'MAT4':16}[a['type']]
        fmt, size = {5120:('b',1), 5121:('B',1), 5122:('h',2), 5123:('H',2), 5125:('I',4), 5126:('f',4)}[a['componentType']]
        values = [0] * (a['count'] * components)
        if 'bufferView' in a:
            view = self.g['bufferViews'][a['bufferView']]
            start = view.get('byteOffset', 0) + a.get('byteOffset', 0)
            stride = view.get('byteStride', components*size)
            for i in range(a['count']):
                values[i*components:(i+1)*components] = struct.unpack_from('<'+fmt*components, self.binary, start+i*stride)
        if 'sparse' in a:
            sp = a['sparse']; iv = self.g['bufferViews'][sp['indices']['bufferView']]; vv = self.g['bufferViews'][sp['values']['bufferView']]
            it, iw = {5121:('B',1), 5123:('H',2), 5125:('I',4)}[sp['indices']['componentType']]
            for i in range(sp['count']):
                target = struct.unpack_from('<'+it, self.binary, iv.get('byteOffset',0)+sp['indices'].get('byteOffset',0)+i*iw)[0]
                values[target*components:(target+1)*components] = struct.unpack_from('<'+fmt*components, self.binary, vv.get('byteOffset',0)+sp['values'].get('byteOffset',0)+i*components*size)
        if a.get('normalized') and a['componentType'] != 5126:
            maximum = {5120:127,5121:255,5122:32767,5123:65535,5125:4294967295}[a['componentType']]
            values = [max(-1, v/maximum) for v in values]
        require(all(math.isfinite(x) for x in values), 'Nonfinite accessor')
        self.cache[index] = values
        return values

    def mesh(self, name):
        node = self.g['nodes'][self.names[name]]
        return node, self.g['meshes'][node['mesh']]

    def joints(self, skin):
        return [self.g['nodes'][i]['name'] for i in skin['joints']]


def weight_check(weights, joints, joint_count, max_influences):
    require(len(weights) == len(joints) and len(weights) % 4 == 0, 'Invalid weight dimensions')
    max_count, error = 0, 0
    for i in range(0, len(weights), 4):
        w, j = weights[i:i+4], joints[i:i+4]
        require(all(math.isfinite(x) and x >= 0 for x in w), 'Invalid weight')
        require(all(int(x) == x and 0 <= x < joint_count for x in j), 'Invalid joint index')
        error = max(error, abs(sum(w)-1))
        max_count = max(max_count, sum(x > 0 for x in w))
    require(error < 1e-6, 'Weights are not normalized')
    require(max_count <= max_influences, 'Too many influences')
    return {'maxWeightSumError': error, 'maxInfluences': max_count, 'vertices': len(weights)//4}


def quat_xyz(x, y, z):
    c1, c2, c3 = [math.cos(v/2) for v in (x,y,z)]
    s1, s2, s3 = [math.sin(v/2) for v in (x,y,z)]
    return [s1*c2*c3+c1*s2*s3, c1*s2*c3-s1*c2*s3, c1*c2*s3+s1*s2*c3, c1*c2*c3-s1*s2*s3]


def aux_quaternion(pose, swing, panel):
    angle = panel/8*math.pi*2
    lift = .16*abs(math.sin(angle)) if pose == 'stride' else .015
    return quat_xyz(-lift*math.sin(angle), 0, lift*math.cos(angle)+max(-.12,min(.12,swing)))


def channels(doc, clip):
    return {(doc.g['nodes'][c['target']['node']]['name'], c['target']['path']): clip['samplers'][c['sampler']] for c in clip['channels']}


def validate_structure(doc, source, project):
    g = doc.g; skirt_enabled = project.get('lowerGarment', 'trousers') == 'skirt'
    original = source.joints(source.g['skins'][0]); original_set = set(original)
    require(len(original_set) == 53, 'Source body skeleton changed')
    all_joints = {name for skin in g['skins'] for name in doc.joints(skin)}
    require(all_joints == original_set | (set(AUX) if skirt_enabled else set()), 'Unexpected/missing body or auxiliary bones')
    require(('Skirt' in doc.names) == skirt_enabled and ('Pants' in doc.names) != skirt_enabled, 'Optional garment export mismatch')
    if not skirt_enabled:
        require(not any(n.get('name','').startswith('skirt_') for n in g['nodes']), 'Hidden auxiliary nodes were exported')
    for name in original:
        source_parent = source.parents.get(source.names[name]); actual_parent = doc.parents.get(doc.names[name])
        wanted = source.g['nodes'][source_parent].get('name') if source_parent is not None else None
        if wanted in original_set:
            require(actual_parent == doc.names[wanted], 'Original body parenting changed: '+name)
    source_ibm = source.accessor(source.g['skins'][0]['inverseBindMatrices'])
    bind_error = 0
    for skin in g['skins']:
        names = doc.joints(skin)
        if names and names[0] in original_set:
            require(names == original, 'Original skin joint order changed')
            actual = doc.accessor(skin['inverseBindMatrices'])
            require(near(actual, source_ibm), 'Original inverse bind/rest matrices changed')
            bind_error = max(bind_error, max(abs(a-b) for a,b in zip(actual,source_ibm)))
    preserved = []
    weight_difference = 0
    for name, node_id in source.names.items():
        if name not in doc.names or 'mesh' not in source.g['nodes'][node_id]:
            continue
        sn, sm = source.mesh(name); dn, dm = doc.mesh(name)
        require(set(doc.joints(g['skins'][dn['skin']])) == original_set, 'Body mesh has garment influences: '+name)
        require(len(sm['primitives']) == len(dm['primitives']), 'Primitive count changed: '+name)
        for sp, dp in zip(sm['primitives'],dm['primitives']):
            # GLTFLoader renormalizes Float32 weights; permit at most two ulps.
            weight_difference = max(weight_difference, max(abs(a-b) for a,b in zip(source.accessor(sp['attributes']['WEIGHTS_0']),doc.accessor(dp['attributes']['WEIGHTS_0']))))
            for semantic in ('POSITION','TEXCOORD_0','JOINTS_0','WEIGHTS_0'):
                require(near(source.accessor(sp['attributes'][semantic]),doc.accessor(dp['attributes'][semantic]),2e-7 if semantic == 'WEIGHTS_0' else 1e-7), 'Original '+semantic+' changed: '+name)
            require(source.accessor(sp['indices']) == doc.accessor(dp['indices']), 'Original topology changed: '+name)
            require(sm.get('extras',{}).get('targetNames',[]) == dm.get('extras',{}).get('targetNames',[]), 'Body morph names changed: '+name)
            for st,dt in zip(sp.get('targets',[]),dp.get('targets',[])):
                require(near(source.accessor(st['POSITION']),doc.accessor(dt['POSITION']),1e-7), 'Original morph geometry changed: '+name)
        preserved.append(name)
    require('HumanBody' in preserved and 'Outfit' in preserved, 'Body or shirt absent')
    require(sorted(a['name'] for a in g['animations']) == POSES, 'Four static pose clips required')
    require(g['animations'][0]['name'] == project['pose'], 'Selected pose must be first exported clip')
    animation_samples = 0
    for clip in g['animations']:
        actual = channels(doc,clip); expected_clip = next(c for c in source.g['animations'] if c['name'] == clip['name']); expected = channels(source,expected_clip)
        for key,sampler in expected.items():
            if key[0] not in original_set:
                continue
            require(key in actual, 'Original bone pose channel missing: '+str(key))
            require(near(source.accessor(sampler['input']),doc.accessor(actual[key]['input'])), 'Original pose times changed')
            require(near(source.accessor(sampler['output']),doc.accessor(actual[key]['output'])), 'Original pose transforms changed: '+str(key))
            animation_samples += len(doc.accessor(actual[key]['output']))
        aux_keys = {key for key in actual if key[0] in AUX}
        require(aux_keys == ({(name,'rotation') for name in AUX[1:]} if skirt_enabled else set()), 'Wrong auxiliary animation tracks')
        for panel,name in enumerate(AUX[1:] if skirt_enabled else []):
            sample = actual[(name,'rotation')]; times = doc.accessor(sample['input']); values = doc.accessor(sample['output']); wanted = aux_quaternion(clip['name'],project.get('skirtSwing',0),panel)
            require(len(times) == 2 and times[0] == 0 and times[1] > 0 and sample.get('interpolation') == 'STEP', 'Auxiliary clip is not static STEP')
            require(near(values,wanted+wanted), 'Incorrect authored auxiliary pose: '+name)
        for name in preserved + (['Skirt'] if skirt_enabled else []):
            node,mesh = doc.mesh(name); names = mesh.get('extras',{}).get('targetNames',[])
            weights = node.get('weights',mesh.get('weights',[0]*len(names)))
            sample = actual[(name,'weights')]; times = doc.accessor(sample['input']); values = doc.accessor(sample['output'])
            require(len(values) == len(times)*len(names), 'Morph sample dimensions')
            for frame in range(len(times)):
                expected_weights = [float(target == 'Pose'+clip['name'].title()) if target.startswith('Pose') else value for target,value in zip(names,weights)]
                require(near(values[frame*len(names):(frame+1)*len(names)],expected_weights), 'Appearance changes between poses: '+name)
    skirt_report = None
    if skirt_enabled:
        require(doc.parents[doc.names[AUX[0]]] == doc.names['pelvis'], 'Skirt anchor not child of pelvis')
        require(all(doc.parents[doc.names[name]] == doc.names[AUX[0]] for name in AUX[1:]), 'Skirt panel parenting changed')
        node,mesh = doc.mesh('Skirt'); skin = g['skins'][node['skin']]
        require(doc.joints(skin) == AUX, 'Skirt has body or unrelated joints')
        require(mesh['extras']['targetNames'] == ['BuildNarrow','BuildBroad'], 'Skirt fit morphs missing')
        weights = node.get('weights',mesh.get('weights',[0,0])); build = project['build']
        require(near(weights,[max(0,(.5-build)*2),max(0,(build-.5)*2)]), 'Exported skirt build differs from project')
        require(len(mesh['primitives']) == 1, 'Unexpected skirt primitives')
        primitive = mesh['primitives'][0]; attrs = primitive['attributes']
        require({'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'} <= attrs.keys(), 'Skirt attributes missing')
        skirt_report = weight_check(doc.accessor(attrs['WEIGHTS_0']),doc.accessor(attrs['JOINTS_0']),9,3)
        require(all(0 <= value <= 1 for value in doc.accessor(attrs['TEXCOORD_0'])), 'Invalid skirt UVs')
        for target in primitive['targets']:
            require(len(doc.accessor(target['POSITION'])) == len(doc.accessor(attrs['POSITION'])), 'Skirt target dimensions')
    return {'file':doc.path.name,'sha256':doc.sha,'bytes':len(doc.raw),'bodyBones':53,'auxiliaryBones':9 if skirt_enabled else 0,'preservedBodyMeshes':preserved,'maxOriginalBindMatrixError':bind_error,'maxBodyWeightRoundingDifference':weight_difference,'bodyPoseSamplesCompared':animation_samples,'clips':[a['name'] for a in g['animations']],'skirt':skirt_report}


def source_hashes():
    hashes = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT/'assets/human/foundation.glb',ROOT/'assets/source/foundation.blend')}
    require(hashes['assets/human/foundation.glb'] == BODY_HASH, 'foundation.glb bytes changed')
    require(hashes['assets/source/foundation.blend'] == BLEND_HASH, 'foundation.blend bytes changed')
    return hashes


def self_test():
    source_hashes(); source = GLB(ROOT/'assets/human/foundation.glb')
    require(len(source.joints(source.g['skins'][0])) == 53, 'Source joint count')
    weight_check([.2,.3,.5,0],[0,1,2,0],9,3)
    cases = [([.2,.3,.4,0],[0,1,2,0]), ([1,0,0,0],[9,0,0,0]), ([.25]*4,[0,1,2,3]), ([float('nan'),0,0,1],[0,1,2,0]), ([-.1,.1,1,0],[0,1,2,0])]
    for weights,joints in cases:
        try:
            weight_check(weights,joints,9,3)
        except AssertionError:
            pass
        else:
            raise AssertionError('Weight mutation was not rejected')
    require(not near([0],[1]), 'Matrix comparator negative control')
    print(json.dumps({'passed':True,'negativeControls':len(cases)+1,'sourceHashes':source_hashes()}))


def exported_fit_checks(doc):
    """Evaluate GLB skinning independently of Three.js and Blender's importer.

    A discrete radial clearance check, not a triangle-collision or cloth solver.
    Body triangles are selected in bind space to exclude hands and forearms.
    """
    import numpy as np
    g = doc.g
    def array(accessor, columns):
        return np.array(doc.accessor(accessor),dtype=np.float64).reshape(-1,columns)
    def matrix(node):
        if 'matrix' in node:
            return np.array(node['matrix'],dtype=np.float64).reshape(4,4).T
        x,y,z,w = node.get('rotation',[0,0,0,1])
        m = np.eye(4)
        m[:3,:3] = [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
        m[:3,:3] *= np.array(node.get('scale',[1,1,1]))
        m[:3,3] = node.get('translation',[0,0,0])
        return m
    mesh_data = {}
    for name in ['HumanBody','Outfit','Skirt']:
        node,mesh = doc.mesh(name); primitive = mesh['primitives'][0]; attrs = primitive['attributes']; skin = g['skins'][node['skin']]
        base = array(attrs['POSITION'],3); triangles = array(primitive['indices'],3).astype(int)
        if name == 'HumanBody':
            points = base[triangles]
            triangles = triangles[np.all((points[:,:,1] < .99) & (np.abs(points[:,:,0]) < .24),axis=1)]
        elif name == 'Outfit':
            triangles = triangles[np.all(base[triangles][:,:,1] < 1.06,axis=1)]
        mesh_data[name] = {'base':base,'triangles':triangles,'targets':{target:array(delta['POSITION'],3) for target,delta in zip(mesh['extras']['targetNames'],primitive['targets'])},'weights':array(attrs['WEIGHTS_0'],4),'joints':array(attrs['JOINTS_0'],4).astype(int),'skin':skin,'ibm':array(skin['inverseBindMatrices'],16).reshape(-1,4,4).transpose(0,2,1)}
    angles = np.arange(0,360,5)*np.pi/180
    cos, sin = np.cos(angles),np.sin(angles)
    def radii(points, triangles, height):
        tri = points[triangles]; edge_start = tri; edge_end = np.roll(tri,-1,axis=1)
        dy = edge_end[:,:,1]-edge_start[:,:,1]
        with np.errstate(divide='ignore',invalid='ignore'):
            t = (height-edge_start[:,:,1])/dy
        valid = (np.abs(dy)>1e-10)&(t>=0)&(t<1)
        keep = valid.sum(axis=1) == 2
        if not keep.any():
            return np.full(len(angles),np.nan)
        safe_t = np.where(valid[keep],t[keep],0)
        intersections = edge_start[keep]+safe_t[:,:,None]*(edge_end[keep]-edge_start[keep])
        line = intersections[valid[keep]].reshape(-1,2,3)
        x,z = line[:,0,0,None],line[:,0,2,None]; dx,dz = (line[:,1,0]-line[:,0,0])[:,None],(line[:,1,2]-line[:,0,2])[:,None]
        den = cos*dz-sin*dx
        with np.errstate(divide='ignore',invalid='ignore'):
            r = (x*dz-z*dx)/den; along = (x*sin-z*cos)/den
        hits = (np.abs(den)>1e-10)&(r>0)&(along>=-1e-7)&(along<=1+1e-7)
        result = np.max(np.where(hits,r,-np.inf),axis=0)
        result[~np.isfinite(result)] = np.nan
        return result
    minimum_body,minimum_waist = math.inf,math.inf
    body_worst = waist_worst = None
    samples = cases = missing = 0
    for pose in POSES:
        clip = next(c for c in g['animations'] if c['name'] == pose)
        posed = copy.deepcopy(g['nodes'])
        for channel in clip['channels']:
            path = channel['target']['path']
            if path == 'weights':
                continue
            sampler = clip['samplers'][channel['sampler']]
            posed[channel['target']['node']][path] = doc.accessor(sampler['output'])[:4 if path == 'rotation' else 3]
        for build in [0,.25,.5,.75,1]:
            for swing in [-.12,0,.12]:
                for shoulders in [0,1]:
                    cases += 1
                    for i,name in enumerate(AUX[1:]):
                        posed[doc.names[name]]['rotation'] = aux_quaternion(pose,swing,i)
                    worlds = {}
                    def world(index):
                        if index not in worlds:
                            local = matrix(posed[index]); parent = doc.parents.get(index)
                            worlds[index] = world(parent)@local if parent is not None else local
                        return worlds[index]
                    positions = {}
                    for name,data in mesh_data.items():
                        vertices = data['base'].copy()
                        for target,delta in data['targets'].items():
                            weight = {'BuildNarrow':max(0,1-2*build),'BuildBroad':max(0,2*build-1),'ShouldersNarrow':max(0,1-2*shoulders),'ShouldersBroad':max(0,2*shoulders-1)}.get(target,float(target == 'Pose'+pose.title()))
                            if weight:
                                vertices += delta*weight
                        homogeneous = np.column_stack([vertices,np.ones(len(vertices))])
                        transforms = np.array([world(index) for index in data['skin']['joints']])@data['ibm']
                        result = np.zeros_like(homogeneous)
                        for influence in range(4):
                            result += np.einsum('nij,nj->ni',transforms[data['joints'][:,influence]],homogeneous)*data['weights'][:,influence,None]
                        positions[name] = result[:,:3]
                    label = {'pose':pose,'build':build,'shoulders':shoulders,'swing':swing}
                    for height in [.65,.7,.75,.8,.85,.9,.935]:
                        inner = radii(positions['HumanBody'],mesh_data['HumanBody']['triangles'],height)
                        outer = radii(positions['Skirt'],mesh_data['Skirt']['triangles'],height)
                        valid = np.isfinite(inner)&np.isfinite(outer)
                        missing += int((np.isfinite(inner)&~np.isfinite(outer)).sum())
                        samples += int(valid.sum())
                        delta = np.where(valid,outer-inner,np.inf); index = int(delta.argmin())
                        if delta[index] < minimum_body:
                            minimum_body = float(delta[index]); body_worst = {**label,'y':height,'angleDegrees':index*5}
                    for height in [.96,.965]:
                        inner = radii(positions['Skirt'],mesh_data['Skirt']['triangles'],height)
                        outer = radii(positions['Outfit'],mesh_data['Outfit']['triangles'],height)
                        valid = np.isfinite(inner)&np.isfinite(outer)
                        missing += int((~valid).sum()); samples += int(valid.sum())
                        delta = np.where(valid,outer-inner,np.inf); index = int(delta.argmin())
                        if delta[index] < minimum_waist:
                            minimum_waist = float(delta[index]); waist_worst = {**label,'y':height,'angleDegrees':index*5}
    result = {'method':'Independent NumPy evaluation of exported GLB morphs, pose channels, joint matrices and weights; radial horizontal sections every 5 degrees','cases':cases,'samples':samples,'missingSections':missing,'minimumBodyClearanceMeters':minimum_body,'minimumShirtOverSkirtClearanceMeters':minimum_waist,'worstBodySample':body_worst,'worstWaistSample':waist_worst,'passed':minimum_body>=.001 and minimum_waist>=.0002 and missing==0}
    require(result['passed'], 'Exported sampled fit failed: '+json.dumps(result))
    return result


def blender_checks(doc, output_blend):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(doc.path.resolve()))
    rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    bone_names = {b.name for r in rigs for b in r.data.bones}
    require(set(AUX) <= bone_names and len(bone_names) == 62, 'Blender lost imported bones')
    def object_for(name):
        material = {'HumanBody':'Skin','HairCrop':'Hair'}.get(name,name)
        matches = [o for o in bpy.data.objects if o.type == 'MESH' and any(m and m.name == material for m in o.data.materials)]
        require(len(matches) == 1, 'Ambiguous Blender mesh: '+name)
        return matches[0]
    body, skirt = object_for('HumanBody'), object_for('Skirt')
    require(skirt.data.uv_layers and skirt.data.shape_keys, 'Imported skirt missing UVs/morphs')
    require({k.name for k in skirt.data.shape_keys.key_blocks} == {'Basis','BuildNarrow','BuildBroad'}, 'Imported skirt morph names')
    require(all(skirt.vertex_groups[g.group].name in AUX for v in skirt.data.vertices for g in v.groups if g.weight > 0), 'Imported skirt body weights')
    require(all(body.vertex_groups[g.group].name not in AUX for v in body.data.vertices for g in v.groups if g.weight > 0), 'Imported body skirt weights')
    active_actions = [r.animation_data.action.name for r in rigs if r.animation_data and r.animation_data.action]
    require(any(name.startswith(doc.g['animations'][0]['name']) for name in active_actions), 'Blender selected pose differs from export')
    packed_images = [image.name for image in bpy.data.images if image.packed_file or image.packed_files]
    require(len(packed_images) >= len(doc.g.get('images',[])), 'Blender import did not retain embedded images')
    for name,ob in [('HumanBody',body),('Skirt',skirt)]:
        node,mesh = doc.mesh(name)
        for target,value in zip(mesh['extras']['targetNames'],node.get('weights',mesh.get('weights',[]))):
            require(abs(ob.data.shape_keys.key_blocks[target].value-value) < 1e-6, 'Blender changed selected shape: '+target)
    # Save before experimental edits: the editable delivered file is the actual import.
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend.resolve()))
    for ob in bpy.data.objects:
        ob.animation_data_clear()
        if ob.type == 'MESH' and ob.data.shape_keys:
            ob.data.shape_keys.animation_data_clear()
    def vertices(ob):
        bpy.context.view_layer.update()
        evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]
    def max_delta(a,b):
        require(len(a) == len(b), 'Evaluated topology changed')
        return max((x-y).length for x,y in zip(a,b))
    initial_body, initial_skirt = vertices(body), vertices(skirt)
    skirt_rig = next(r for r in rigs if AUX[1] in r.pose.bones)
    panel = skirt_rig.pose.bones[AUX[1]]; saved = panel.matrix_basis.copy()
    panel.rotation_mode = 'XYZ'; panel.rotation_euler.x += .35
    skirt_delta, body_delta = max_delta(initial_skirt,vertices(skirt)), max_delta(initial_body,vertices(body))
    require(skirt_delta > .005, 'Auxiliary bone does not deform skirt')
    require(body_delta == 0, 'Auxiliary bone moves the body')
    panel.matrix_basis = saved
    head = body.data.shape_keys.key_blocks['HeadWide']; old = head.value
    head.value = 1 if old < .5 else 0
    head_delta = max_delta(initial_body,vertices(body)); require(head_delta > .005, 'Imported head morph not editable'); head.value = old
    body_rig = next(r for r in rigs if 'lowerarm_l' in r.pose.bones)
    arm = body_rig.pose.bones['lowerarm_l']; saved = arm.matrix_basis.copy()
    arm.rotation_mode = 'XYZ'; arm.rotation_euler.x += .5
    arm_delta, skirt_arm_delta = max_delta(initial_body,vertices(body)), max_delta(initial_skirt,vertices(skirt))
    require(arm_delta > .01, 'Original body bone not editable')
    require(skirt_arm_delta < 1e-6, 'Arm edit unexpectedly moves skirt')
    arm.matrix_basis = saved
    return {'blenderVersion':bpy.app.version_string,'armatures':len(rigs),'uniqueBones':len(bone_names),'savedBlend':str(output_blend.relative_to(ROOT)),'savedBlendBytes':output_blend.stat().st_size,'savedBlendSha256':hashlib.sha256(output_blend.read_bytes()).hexdigest(),'initialActiveActions':active_actions,'packedImages':len(packed_images),'editAuxBoneSkirtMaxDeltaMeters':skirt_delta,'editAuxBoneBodyMaxDeltaMeters':body_delta,'editHeadWideMaxDeltaMeters':head_delta,'editForearmBodyMaxDeltaMeters':arm_delta,'editForearmSkirtMaxDeltaMeters':skirt_arm_delta}


def main():
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture_report',nargs='?',default=str(ROOT/'artifacts/skirt-report.json'))
    parser.add_argument('output_report',nargs='?',default=str(ROOT/'artifacts/skirt-export-validation.json'))
    parser.add_argument('--self-test',action='store_true'); parser.add_argument('--structure-only',action='store_true')
    options = parser.parse_args(args)
    if options.self_test:
        self_test(); return
    report_path, output = Path(options.capture_report), Path(options.output_report)
    report = {'passed':False,'sourceHashesBefore':source_hashes(),'verified':[],'limits':['Only authored static poses are tested. No cloth simulation or arbitrary-motion guarantee.','No exhaustive self-collision or continuously varying body/pose/sway collision proof.']}
    try:
        capture_report = json.loads(report_path.read_text())
        require(capture_report.get('passed') is True, 'Browser report did not pass')
        require(all(c.get('passed') for c in capture_report.get('checks',[])), 'Browser checks failed')
        source = GLB(ROOT/'assets/human/foundation.glb'); documents = {}
        for filename in ['skirt-stride.glb','skirt-neutral.glb','skirt-trousers.glb']:
            capture = next(e for e in capture_report['exports'] if e.get('capture',{}).get('name') == filename)
            doc = GLB(report_path.parent/filename); documents[filename] = doc
            require(capture['capture']['sha256'] == doc.sha and capture['capture']['bytes'] == len(doc.raw), 'Browser capture hash/size mismatch: '+filename)
            report['verified'].append(validate_structure(doc,source,capture['project']))
        # Guard against a validator that silently accepts a missing garment bone/clip.
        negative = copy.copy(documents['skirt-neutral.glb']); negative.g = copy.deepcopy(negative.g)
        negative.g['animations'].pop()
        neutral_project = next(e['project'] for e in capture_report['exports'] if e['capture']['name'] == 'skirt-neutral.glb')
        try:
            validate_structure(negative,source,neutral_project)
        except AssertionError:
            report['missingClipNegativeControl'] = True
        else:
            raise AssertionError('Missing clip negative control unexpectedly passed')
        if not options.structure_only:
            report['exportedFit'] = exported_fit_checks(documents['skirt-neutral.glb'])
            report['blender'] = blender_checks(documents['skirt-stride.glb'], report_path.parent/'skirt-editable.blend')
        else:
            report['limits'].append('Independent exported fit and Blender reimport/editability not run in structure-only mode.')
        report['sourceHashesAfter'] = source_hashes()
        report['passed'] = True
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
        output.write_text(json.dumps(report,indent=2)+'\n')
        raise
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
