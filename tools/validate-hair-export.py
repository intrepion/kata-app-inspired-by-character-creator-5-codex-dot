"""Validate captured browser groom GLBs, actual Blender import/edit/re-export.
Blender -b --python-exit-code 1 --python tools/validate-hair-export.py
"""
import bpy,importlib.util,json,pathlib,hashlib,math,copy
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('expression',ROOT/'tools/validate-expression-export.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
base,GLB,require=ex.base,ex.GLB,ex.require
capture=json.loads((ROOT/'artifacts/hair-export-report.json').read_text());require(capture['passed'] and capture['exportPassed'],'Browser acceptance/export incomplete')
source=GLB(ROOT/'assets/human/foundation.glb');report={'passed':False,'sourceHashesBefore':base.source_hashes(),'structure':[]}
for item in capture['exports']:
    doc=GLB(ROOT/'artifacts'/item['capture']['name']);require(doc.sha==item['capture']['sha256'],'Captured hash mismatch')
    stripped=ex.eye.without_eyes(ex.without_expressions(doc))
    preserved_source=copy.copy(source);preserved_source.names={n:i for n,i in source.names.items() if not (n=='HairCrop' and item['mode']=='groom')}
    record=base.validate_structure(stripped,preserved_source,item['project'])
    expected_meshes={'HumanBody','Outfit','Eyes','Iris','Cornea','Brows','Lashes','Skirt' if item['project'].get('lowerGarment')=='skirt' else 'Pants'}
    require(expected_meshes<=set(doc.names),'Original non-hair attachment missing')
    for name in ['HumanBody','Brows']:
        node,mesh=doc.mesh(name);names=mesh['extras']['targetNames'];require(names[-4:]==ex.TARGETS,'Expression keys lost');weights=node.get('weights',mesh.get('weights',[]));require(base.near(weights[-4:],ex.expression_weights(item['project'])),'Expression weights changed')
    for name in ex.eye.PARTS:
        node,mesh=doc.mesh(name);names=mesh['extras']['targetNames'];weights=node.get('weights',mesh.get('weights',[]));expected=ex.eye.eye_weights(ex.effective_project(item['project']));require(base.near([weights[names.index(n)] for n in ex.eye.TARGETS],expected),'Eye weights changed')
    if item['project']['hair']=='none':require(not any('Hair' in name for name in doc.names),'Bald export contains hair')
    elif item['mode']=='groom':
        require('HairGroom' in doc.names and 'HairStrands' not in doc.names,'Wrong visible groom')
        root_node,root_mesh=doc.mesh('HairCrop');root=root_mesh['primitives'][0];original=source.mesh('HairCrop')[1]['primitives'][0];ids=source.accessor(original['indices'])
        for semantic in ['POSITION','NORMAL','JOINTS_0','WEIGHTS_0']:
            a=source.accessor(original['attributes'][semantic]);b=doc.accessor(root['attributes'][semantic]);size=4 if semantic in ['JOINTS_0','WEIGHTS_0'] else 3;expected=[a[i*size+k] for i in ids for k in range(size)];require(base.near(b,expected,2e-7),'Root seam changed '+semantic)
        for old,new in zip(original['targets'],root['targets']):
            a=source.accessor(old['POSITION']);b=doc.accessor(new['POSITION']);require(base.near(b,[a[i*3+k] for i in ids for k in range(3)],1e-7),'Root seam changed an identity target')
        uv=doc.accessor(root['attributes']['TEXCOORD_0']);require(all(max(uv[i:i+6:2])-min(uv[i:i+6:2])<.5 for i in range(0,len(uv),6)),'Rear UV seam still crosses frontal mask')
        node,mesh=doc.mesh('HairGroom');names=mesh['extras']['targetNames'];require(names==source.mesh('HairCrop')[1]['extras']['targetNames'],'Groom lost original identity keys')
        p=mesh['primitives'][0];attrs=p['attributes'];require(set(['POSITION','NORMAL','TEXCOORD_0','COLOR_0','JOINTS_0','WEIGHTS_0'])<=attrs.keys(),'Missing portable groom attributes')
        w=doc.accessor(attrs['WEIGHTS_0']);j=doc.accessor(attrs['JOINTS_0']);record['groomWeights']=base.weight_check(w,j,53,4)
        require(len(doc.accessor(attrs['POSITION']))//3<55000,'Groom vertex budget exceeded')
        require(all(math.isfinite(v) for a in attrs.values() for v in doc.accessor(a)),'Nonfinite hair attribute')
        weights=node.get('weights',mesh.get('weights',[]));require(len(weights)==28,'Missing current identity weights')
        for key,value in item['project'].items():
            if key not in capture['renderer']['morphs']:continue
            for side,name in enumerate(capture['renderer']['morphs'][key]):
                expected=max(0,(.5-value)*2) if side==0 else max(0,(value-.5)*2)
                require(abs(weights[names.index(name)]-expected)<1e-6,'Wrong groom identity weight '+name)
        for clip in doc.g['animations']:
            sampler=base.channels(doc,clip)[('HairGroom','weights')];times=doc.accessor(sampler['input']);values=doc.accessor(sampler['output']);require(len(values)==len(times)*28,'Groom pose key dimensions')
            for frame in range(len(times)):require(base.near(values[frame*28:(frame+1)*28],weights),'Pose changes groom identity')
        material=next(m for m in doc.g['materials'] if m['name']=='HairGroom');extension=material['extensions']['KHR_materials_anisotropy'];require(abs(extension['anisotropyStrength']-.7)<1e-7,'Directional highlight strength missing')
        record['groom']={'vertices':len(w)//4,'triangles':len(doc.accessor(p['indices']))//3,'targets':names,'anisotropy':extension}
    report['structure'].append(record)
    if item['capture']['name']=='hair-extreme.glb':chosen=doc
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(chosen.path))
armatures=[o for o in bpy.data.objects if o.type=='ARMATURE'];bones={b.name for o in armatures for b in o.data.bones};require(len(bones)==62,'Lost body/skirt bones in Blender')
hair=next((o for o in bpy.data.objects if o.type=='MESH' and any(m and m.name=='HairGroom' for m in o.data.materials)),None);require(hair is not None,'Blender lost hair mesh');require(len(hair.data.shape_keys.key_blocks)==29,'Blender lost editable groom keys');require(any(m.type=='ARMATURE' for m in hair.modifiers),'Hair is not skinned')
for keys in bpy.data.shape_keys:keys.animation_data_clear()
for ob in armatures:ob.animation_data_clear()
def points(ob):
    bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());return [ev.matrix_world@v.co for v in ev.data.vertices]
edits={}
for name,key in [('HairGroom','HeadWide'),('HairGroom','HeadLong'),('HumanBody','Smile'),('HumanBody','BlinkLeft'),('Brows','BrowRaise')]:
    ob=bpy.data.objects.get(name)
    if ob is None or ob.type!='MESH':ob=next(o for o in bpy.data.objects if o.type=='MESH' and any(m and m.name==('Skin' if name=='HumanBody' else name) for m in o.data.materials))
    shape=ob.data.shape_keys.key_blocks[key];old=shape.value;before=points(ob);shape.value=0 if old>.5 else 1;after=points(ob);shape.value=old;movement=max((a-b).length for a,b in zip(before,after));require(movement>.0001,'Uneditable '+name+'/'+key);edits[name+'/'+key]=movement
arm=next(o for o in armatures if 'head' in o.pose.bones);head=arm.pose.bones['head'];old=head.rotation_mode;head.rotation_mode='XYZ';angle=head.rotation_euler.copy();before=points(hair);head.rotation_euler.z+=.12;after=points(hair);head.rotation_euler=angle;head.rotation_mode=old;movement=max((a-b).length for a,b in zip(before,after));require(movement>.002,'Head bone does not move groom');edits['HairGroom/headBone']=movement
mat=bpy.data.materials['HairGroom'];bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');anisotropy=next(i for i in bs.inputs if i.name.startswith('Anisotropic') and 'Rotation' not in i.name);require(abs(anisotropy.default_value-.7)<1e-6,'Blender did not import anisotropy strength');require(any(n.type=='VERTEX_COLOR' or n.type=='ATTRIBUTE' for n in mat.node_tree.nodes),'Blender lost per-fiber color variation')
report['blender']={'version':bpy.app.version_string,'bones':len(bones),'hairVertices':len(hair.data.vertices),'shapeKeys':list(hair.data.shape_keys.key_blocks.keys()),'editableMovementMeters':edits,'anisotropyInput':anisotropy.name,'anisotropyValue':anisotropy.default_value,'images':[{'name':im.name,'size':list(im.size)} for im in bpy.data.images if im.size[0]>0]}
blend=ROOT/'artifacts/hair-editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));roundtrip=ROOT/'artifacts/hair-blender-roundtrip.glb';bpy.ops.export_scene.gltf(filepath=str(roundtrip),export_format='GLB',export_skins=True,export_morph=True,export_animations=False)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(roundtrip));hair2=next((o for o in bpy.data.objects if o.type=='MESH' and any(m and m.name=='HairGroom' for m in o.data.materials)),None);require(hair2 is not None and len(hair2.data.shape_keys.key_blocks)==29,'Blender re-export lost groom targets');require(len(hair2.data.vertices)==report['blender']['hairVertices'],'Blender re-export changed groom vertices');bs2=next(n for n in bpy.data.materials['HairGroom'].node_tree.nodes if n.type=='BSDF_PRINCIPLED');an2=next(i for i in bs2.inputs if i.name.startswith('Anisotropic') and 'Rotation' not in i.name);require(abs(an2.default_value-.7)<1e-6,'Blender re-export lost anisotropy');report['blender']['reexportReimportPassed']=True;report['blender']['roundtripSha256']=hashlib.sha256(roundtrip.read_bytes()).hexdigest();report['blender']['editableBlendSha256']=hashlib.sha256(blend.read_bytes()).hexdigest()
report['sourceHashesAfter']=base.source_hashes();require(report['sourceHashesAfter']==report['sourceHashesBefore'],'Source modified');report['passed']=True;(ROOT/'artifacts/hair-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
