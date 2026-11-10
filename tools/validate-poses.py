"""Pose regression: blender -b --python tools/validate-poses.py.

Numerical checks only. Browser visual review must use the local HTTP server.
Does not overwrite the source blend or GLB.
"""
import bpy, pathlib, runpy, math, json, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/source/foundation.blend'))
helpers = runpy.run_path(str(ROOT/'tools/pose-human.py'))
rig = bpy.data.objects['FoundationRig']
meshes = [bpy.data.objects[n] for n in ['HumanBody', 'Outfit', 'Pants']]
report = {'hingeTwistDegrees': {}, 'correctiveErrorMeters': {}}
for name in ['tpose', 'wave']:
    helpers['apply_pose'](rig, name)
    q = rig.pose.bones['lowerarm_l'].rotation_quaternion
    twist = abs(math.degrees(2*math.atan2(q.y, q.w)))
    report['hingeTwistDegrees'][name] = twist
    assert twist < .01, (name, twist)
    assert rig.pose.bones['clavicle_l'].rotation_quaternion.angle > math.radians(10)
# Validate the saved keys, not newly generated replacements that could mask stale assets.
report['validatedSavedCorrectives'] = True
for name, key_name in helpers['POSE_CORRECTIVES'].items():
    helpers['apply_pose'](rig, name)
    for ob in meshes:
        for key in ob.data.shape_keys.key_blocks:
            key.value = 0
        modifier = next(m for m in ob.modifiers if m.type == 'ARMATURE')
        modifier.use_deform_preserve_volume = True
        bpy.context.view_layer.update()
        target = [v.co.copy() for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
        modifier.use_deform_preserve_volume = False
        ob.data.shape_keys.key_blocks[key_name].value = 1
        bpy.context.view_layer.update()
        actual = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
        error = max((v.co-p).length for v,p in zip(actual, target))
        report['correctiveErrorMeters'][ob.name+'/'+name] = error
        assert error < .00001, (ob.name, name, error)
        ob.data.shape_keys.key_blocks[key_name].value = 0
# Shape controls alter vertex positions, not weights. A fixed pose corrective
# therefore has a small residual away from the base shape; measure every corner.
report['extremeShapeErrorMeters'] = {}
for name, key_name in helpers['POSE_CORRECTIVES'].items():
    helpers['apply_pose'](rig, name)
    for ob in meshes:
        keys = ob.data.shape_keys.key_blocks
        for build in ['BuildNarrow', 'BuildBroad']:
            for shoulders in ['ShouldersNarrow', 'ShouldersBroad']:
                for key in keys:
                    key.value = 0
                keys[build].value = 1
                keys[shoulders].value = 1
                modifier = next(m for m in ob.modifiers if m.type == 'ARMATURE')
                modifier.use_deform_preserve_volume = True
                bpy.context.view_layer.update()
                target = [v.co.copy() for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
                modifier.use_deform_preserve_volume = False
                keys[key_name].value = 1
                bpy.context.view_layer.update()
                actual = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
                error = max((v.co-p).length for v,p in zip(actual, target))
                report['extremeShapeErrorMeters']['/'.join([ob.name,name,build,shoulders])] = error
                assert error < .012, (ob.name, name, build, shoulders, error)
        for key in keys:
            key.value = 0
report['passed'] = True
print(json.dumps(report, indent=2))
if '--' in sys.argv:
    pathlib.Path(sys.argv[sys.argv.index('--')+1]).write_text(json.dumps(report, indent=2)+'\n')
