"""Verify saved source/GLB skinning agrees, without rebuilding either artifact.

blender -b --python tools/validate-pose-roundtrip.py -- [source.blend model.glb report.json]
Reports base and posed positions at default and every build/shoulder corner.
No visual inspection or artifact writes; only the optional JSON report is written.
"""
import bpy, json, pathlib, sys
from mathutils.kdtree import KDTree
ROOT = pathlib.Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
source_path = pathlib.Path(args[0]) if args else ROOT/'assets/source/foundation.blend'
glb_path = pathlib.Path(args[1]) if len(args)>1 else ROOT/'assets/human/foundation.glb'
NAMES = ('HumanBody', 'Outfit', 'Pants')
POSES = ('relaxed', 'tpose', 'wave', 'stride')
SHAPES = ((.5,.5), (0,0), (0,1), (1,0), (1,1))
TOLERANCE = .00001
report = {'source': source_path.name, 'glb': glb_path.name, 'toleranceMeters': TOLERANCE, 'baseErrorMeters': {}, 'poseErrorMeters': {}}
def evaluated_vertices(ob):
    bpy.context.view_layer.update()
    return [ob.matrix_world @ v.co for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
def shape(ob, pose, build=.5, shoulders=.5):
    for key in ob.data.shape_keys.key_blocks:
        key.value = int(key.name == 'Pose'+pose.title())
    for control, value in [('Build',build), ('Shoulders',shoulders)]:
        ob.data.shape_keys.key_blocks[control+('Narrow' if value<.5 else 'Broad')].value = abs(value-.5)*2
bpy.ops.wm.open_mainfile(filepath=str(source_path))
rig = bpy.data.objects['FoundationRig']
meshes = {name: bpy.data.objects[name] for name in NAMES}
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
for ob in meshes.values():
    if ob.data.shape_keys.animation_data:
        ob.data.shape_keys.animation_data_clear()
    shape(ob, 'relaxed')
    next(m for m in ob.modifiers if m.type=='ARMATURE').use_deform_preserve_volume = False
base = {name: evaluated_vertices(ob) for name,ob in meshes.items()}
def weights(ob,vertex):
    return {ob.vertex_groups[g.group].name: g.weight for g in vertex.groups if g.weight>0 and ob.vertex_groups[g.group].name in rig.data.bones}
source_weights = {name: [weights(ob,v) for v in ob.data.vertices] for name,ob in meshes.items()}
report['sourceMaxInfluences'] = max(sum(g.weight>0 and ob.vertex_groups[g.group].name in rig.data.bones for g in v.groups) for ob in meshes.values() for v in ob.data.vertices)
expected = {}
for pose in POSES:
    rig.animation_data_create()
    rig.animation_data.action = bpy.data.actions[pose]
    bpy.context.scene.frame_set(0)
    for build,shoulders in SHAPES:
        for name,ob in meshes.items():
            shape(ob,pose,build,shoulders)
            expected[(pose,build,shoulders,name)] = evaluated_vertices(ob)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb_path))
rig = next(ob for ob in bpy.data.objects if ob.type=='ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
meshes = {name: next(ob for ob in bpy.data.objects if ob.type=='MESH' and ob.data.name==name) for name in NAMES}
mapping = {}
for name,ob in meshes.items():
    if ob.data.shape_keys.animation_data:
        ob.data.shape_keys.animation_data_clear()
    shape(ob,'relaxed')
    tree = KDTree(len(base[name]))
    for index,point in enumerate(base[name]):
        tree.insert(point,index)
    tree.balance()
    # The flattened hem can have coincident vertices with distinct skin weights.
    # Resolve UV splits and coincident points by weights, not nearest position alone.
    matches = []
    for vertex,point in zip(ob.data.vertices,evaluated_vertices(ob)):
        imported_weights = weights(ob,vertex)
        candidates = tree.find_range(point,.000002) or [tree.find(point)]
        def score(match):
            original = source_weights[name][match[1]]
            return (sum(abs(original.get(bone,0)-imported_weights.get(bone,0)) for bone in set(original)|set(imported_weights)),match[2])
        matches.append(min(candidates,key=score))
    mapping[name] = [index for _,index,_ in matches]
    report['baseErrorMeters'][name] = max(distance for _,_,distance in matches)
for pose in POSES:
    rig.animation_data_create()
    rig.animation_data.action = bpy.data.actions[pose+'_FoundationRig']
    bpy.context.scene.frame_set(0)
    for build,shoulders in SHAPES:
        for name,ob in meshes.items():
            shape(ob,pose,build,shoulders)
            reference = expected[(pose,build,shoulders,name)]
            error = max((point-reference[index]).length for point,index in zip(evaluated_vertices(ob),mapping[name]))
            report['poseErrorMeters'][f'{name}/{pose}/build={build}/shoulders={shoulders}'] = error
report['maxPoseErrorMeters'] = max(report['poseErrorMeters'].values())
report['passed'] = report['sourceMaxInfluences']<=4 and max(report['baseErrorMeters'].values())<TOLERANCE and report['maxPoseErrorMeters']<TOLERANCE
print(json.dumps(report,indent=2))
if len(args)>2:
    pathlib.Path(args[2]).write_text(json.dumps(report,indent=2)+'\n')
assert report['passed'], 'Saved source/GLB deformation disagrees; inspect JSON report'
