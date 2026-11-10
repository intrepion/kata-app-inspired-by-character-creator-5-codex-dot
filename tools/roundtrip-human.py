"""Verify the exact UI-exported Botanist/Fern artifact, never a regenerated substitute."""
import bpy,json,pathlib,hashlib,math
from mathutils import Vector
ROOT=pathlib.Path(__file__).resolve().parents[1];PATH=ROOT/'artifacts/Fern-app-export.glb';REPORT=ROOT/'docs/BLENDER-ROUNDTRIP.json'
def clear():
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 for a in list(bpy.data.actions):bpy.data.actions.remove(a)
def verts(o):
 bpy.context.view_layer.update();e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());return [e.matrix_world@v.co for v in e.data.vertices]
def bounds(v):return {'min':[min(x[i] for x in v) for i in range(3)],'max':[max(x[i] for x in v) for i in range(3)]}
clear();bpy.ops.import_scene.gltf(filepath=str(PATH));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=bpy.data.objects['HumanBody']
report={'artifact':str(PATH.relative_to(ROOT)),'sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'blender':bpy.app.version_string,'boneCount':len(rig.data.bones),'actions':[a.name for a in bpy.data.actions],'initialActiveAction':rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None,'hairAbsent':not any(o.name.startswith('HairCrop') for o in bpy.context.scene.objects),'morphValues':{k.name:k.value for k in body.data.shape_keys.key_blocks if k.name!='Basis'},'objectScales':{o.name:list(o.scale) for o in bpy.context.scene.objects if o.type in ['ARMATURE','EMPTY','MESH'] and o.name!='Icosphere'},'images':[{'name':i.name,'size':list(i.size)} for i in bpy.data.images if i.type=='IMAGE' and i.size[0]>0]}
initial=verts(body);report['initialBodyBounds']=bounds(initial)
report['leftHandWorldPosition']=list(rig.matrix_world@rig.pose.bones['hand_l'].head)
report['rightHandWorldPosition']=list(rig.matrix_world@rig.pose.bones['hand_r'].head)
report['waveRaisedHandVerified']=report['leftHandWorldPosition'][2]>report['rightHandWorldPosition'][2]+.25
# Store the exact untouched import before temporary edit tests.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'artifacts/Fern-roundtrip.blend'))
# Temporarily edit a target from its imported value, then restore it.
k=body.data.shape_keys.key_blocks['JawBroad'];saved=k.value;k.value=.8;changed=verts(body);report['jawEditMaxWorldDeltaMeters']=max((a-b).length for a,b in zip(initial,changed));k.value=saved
# Test local forearm edit with no frame advance, preserving imported pose.
b=rig.pose.bones['lowerarm_l'];saved=b.matrix_basis.copy();b.rotation_mode='XYZ';b.rotation_euler.x+=.35;changed=verts(body);report['forearmEditMaxWorldDeltaMeters']=max((a-c).length for a,c in zip(initial,changed));b.matrix_basis=saved
# Height must be effective on the skinned geometry, not only stored as an unused parent property.
root=bpy.data.objects.get('Fern');report['heightScaleStored']=list(root.scale) if root else None
before=verts(body);root.scale=(1,1,1);unscaled=verts(body);report['effectiveHeightScale']=((max(v.z for v in before)-min(v.z for v in before))/(max(v.z for v in unscaled)-min(v.z for v in unscaled)))
# Compare app import against the original GLB with the same morphs and wave action.
app_bounds=report['initialBodyBounds'];clear();bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/human/foundation.glb'));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=bpy.data.objects['HumanBody']
rig.animation_data.action=next(a for a in bpy.data.actions if a.name.startswith('wave'));bpy.context.scene.frame_set(0)
for k in body.data.shape_keys.key_blocks:
 if k.name in report['morphValues']:k.value=report['morphValues'][k.name]
source_wave=verts(body);expected=[v*.97 for v in source_wave];report['referenceWaveBoundsAt097']=bounds(expected)
report['referenceBoundsMaxErrorMeters']=max(abs(app_bounds[key][i]-report['referenceWaveBoundsAt097'][key][i]) for key in ['min','max'] for i in range(3))
expected_morph={'BuildNarrow':.2,'ShouldersNarrow':.2,'JawNarrow':.2,'EyesLarge':.2}
report['checks']={'waveActionSelectedOnImport':bool(report['initialActiveAction'] and report['initialActiveAction'].startswith('wave')),'53Bones':report['boneCount']==53,'hairNone':report['hairAbsent'],'morphValues':all(abs(report['morphValues'][k]-v)<1e-5 for k,v in expected_morph.items()),'wavePose':report['waveRaisedHandVerified'],'heightStored':all(abs(s-.97)<1e-5 for s in report['heightScaleStored']),'heightEffective':abs(report['effectiveHeightScale']-.97)<1e-4,'referenceGeometry':report['referenceBoundsMaxErrorMeters']<.002,'editableJaw':report['jawEditMaxWorldDeltaMeters']>.001,'editableForearm':report['forearmEditMaxWorldDeltaMeters']>.02,'skinAndEyeImages':sum(i['size'][0]>=1024 for i in report['images'])>=2}
report['passed']=all(report['checks'].values());REPORT.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['passed']
