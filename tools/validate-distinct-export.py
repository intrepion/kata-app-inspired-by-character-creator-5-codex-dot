"""Check the exact browser-captured GLB and numerically reimport/edit in Blender.
Usage: blender -b --python-exit-code 1 --python tools/validate-distinct-export.py --
  export.glb browser-report.json output-report.json
Does not modify the source/export. Writes only the numerical JSON report.
"""
import bpy, pathlib, sys, json, struct, hashlib, copy, datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
a=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
path=pathlib.Path(a[0]) if a else ROOT/'artifacts/portrait-extreme.glb'
report_path=pathlib.Path(a[1]) if len(a)>1 else ROOT/'artifacts/distinct-software-report.json'
out=pathlib.Path(a[2]) if len(a)>2 else ROOT/'artifacts/distinct-export-validation.json'
raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
assert struct.unpack_from('<III',raw)==(0x46546c67,2,len(raw))
n=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+n]);binary=raw[28+n:]
r=json.loads(report_path.read_text());capture=next(e for e in r['exports'] if e.get('capture',{}).get('name')==path.name)
assert capture['capture']['sha256']==sha and capture['capture']['bytes']==len(raw),'Capture hash/size mismatch'
auto=r['autoRun'];assert auto['passed']
start=datetime.datetime.fromisoformat(auto['startedAt'].replace('Z','+00:00')).timestamp()
finish=datetime.datetime.fromisoformat(auto['finishedAt'].replace('Z','+00:00')).timestamp()
assert finish>=start,'Invalid browser run timestamps'
# Copying/unzipping a capture can change mtime without changing its identity.
mtime_within_run=start-2<=path.stat().st_mtime<=finish+2
manifest=json.loads((ROOT/'assets/human/manifest.json').read_text());expected=capture['project']
targets=[t for c in manifest['distinctFaces']['controls'] for t in manifest['morphs'][c]]
assert len(targets)==len(set(targets))==18
required=['HumanBody','Eyes','Iris','Cornea','Brows','Lashes']+(['HairCrop','HairStrands'] if expected['hair']!='none' else [])
def accessor(index):
 a=g['accessors'][index];components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
 fmt,width={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}[a['componentType']];values=[0]*(a['count']*components)
 if 'bufferView' in a:
  v=g['bufferViews'][a['bufferView']];off=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',width*components)
  for i in range(a['count']):values[i*components:(i+1)*components]=struct.unpack_from('<'+fmt*components,binary,off+i*stride)
 if 'sparse' in a:
  s=a['sparse'];iv=g['bufferViews'][s['indices']['bufferView']];vv=g['bufferViews'][s['values']['bufferView']];it,iw={5121:('B',1),5123:('H',2),5125:('I',4)}[s['indices']['componentType']]
  for i in range(s['count']):
   at=struct.unpack_from('<'+it,binary,iv.get('byteOffset',0)+s['indices'].get('byteOffset',0)+i*iw)[0]
   values[at*components:(at+1)*components]=struct.unpack_from('<'+fmt*components,binary,vv.get('byteOffset',0)+s['values'].get('byteOffset',0)+i*width*components)
 return values

def structure(doc):
 nodes={node['name']:(i,node) for i,node in enumerate(doc['nodes']) if 'mesh' in node}
 assert sorted(clip['name'] for clip in doc['animations'])==['relaxed','stride','tpose','wave']
 assert len({j for skin in doc['skins'] for j in skin['joints']})==53
 for name in required:
  _,node=nodes[name];mesh=doc['meshes'][node['mesh']];names=mesh.get('extras',{}).get('targetNames',[])
  assert set(targets)<=set(names),name+' missing target'
  for p in mesh['primitives']:
   assert {'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}<=p['attributes'].keys()
   assert len(p['targets'])==len(names) and all('POSITION' in t for t in p['targets'])
   assert 'material' in p and doc['materials'][p['material']]
 assert len(doc['images'])>=8 and all('bufferView' in image and 'uri' not in image for image in doc['images'])
 assert doc['animations'][0]['name']==expected['pose']
 return nodes
nodes=structure(g)
for mutation in ['target','clip']:
 broken=copy.deepcopy(g)
 if mutation=='clip':broken['animations'].pop()
 else:broken['meshes'][nodes['Iris'][1]['mesh']]['extras']['targetNames'].remove(targets[0])
 try:structure(broken)
 except (AssertionError,KeyError):pass
 else:raise AssertionError('Negative control passed: '+mutation)
checked=0
for name in required:
 ni,node=nodes[name];mesh=g['meshes'][node['mesh']];names=mesh['extras']['targetNames'];weights=node.get('weights',mesh.get('weights',[0]*len(names)))
 for control,pair in manifest['morphs'].items():
  if not isinstance(pair,list):continue
  for side,target in enumerate(pair):
   if target not in names:continue
   wanted=max(0,(.5-expected.get(control,.5))*2) if side==0 else max(0,(expected.get(control,.5)-.5)*2)
   assert abs(weights[names.index(target)]-wanted)<1e-6,(name,target,'current weight')
 for clip in g['animations']:
  channels=[c for c in clip['channels'] if c['target'].get('node')==ni and c['target']['path']=='weights'];assert len(channels)==1
  sampler=clip['samplers'][channels[0]['sampler']];times=accessor(sampler['input']);values=accessor(sampler['output'])
  assert sampler.get('interpolation','LINEAR') in ['STEP','LINEAR'] and len(values)==len(times)*len(names)
  for frame in range(len(times)):
   for index,target in enumerate(names):
    wanted=float(target=='Pose'+clip['name'].title()) if target.startswith('Pose') else weights[index]
    assert abs(values[frame*len(names)+index]-wanted)<1e-6,(name,clip['name'],target,'appearance changed')
    checked+=1
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(path))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');assert len(rig.data.bones)==53
objects={}
for name in required:
 # Blender uses Mesh_N names for animated browser exports; material roles stay stable.
 material_name={'HumanBody':'Skin','HairCrop':'Hair'}.get(name,name)
 matches=[o for o in bpy.data.objects if o.type=='MESH' and any(m and m.name==material_name for m in o.data.materials)]
 assert len(matches)==1,(name,'ambiguous imported material role')
 ob=matches[0];objects[name]=ob
 assert ob.data.uv_layers and ob.data.materials
 assert set(targets)<={key.name for key in ob.data.shape_keys.key_blocks}
 assert any(mod.type=='ARMATURE' and mod.object==rig for mod in ob.modifiers)
 assert all(sum(group.weight for group in vertex.groups)>.98 for vertex in ob.data.vertices),(name,'unweighted vertex')
 ob.animation_data_clear();ob.data.shape_keys.animation_data_clear()
rig.animation_data_clear()
for name,ob in objects.items():
 _,node=nodes[name];mesh=g['meshes'][node['mesh']];names=mesh['extras']['targetNames'];weights=node.get('weights',mesh.get('weights',[0]*len(names)))
 for target,weight in zip(names,weights):ob.data.shape_keys.key_blocks[target].value=weight

def vertices(ob):
 bpy.context.view_layer.update()
 return [ob.matrix_world@v.co for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
for ob in objects.values():
 ob.data.shape_keys.key_blocks['HeadNarrow'].value=0;ob.data.shape_keys.key_blocks['HeadWide'].value=0
before={name:vertices(ob) for name,ob in objects.items()}
for ob in objects.values():ob.data.shape_keys.key_blocks['HeadWide'].value=1
morph_deltas={name:max((a-b).length for a,b in zip(vertices(ob),before[name])) for name,ob in objects.items()}
assert morph_deltas['HumanBody']>.005 and all(value>1e-5 for value in morph_deltas.values()),morph_deltas
body=objects['HumanBody'];before=vertices(body)
bone=rig.pose.bones['lowerarm_l'];bone.rotation_mode='XYZ';bone.rotation_euler.x+=.5
after=vertices(body);bone_delta=max((a-b).length for a,b in zip(before,after));assert bone_delta>.01,bone_delta
report={'passed':True,'source':str(path.resolve()),'sha256':sha,'bytes':len(raw),'browserSoftware':auto.get('software'),'mtimeWithinBrowserRun':mtime_within_run,'browserStartedAt':auto['startedAt'],'browserFinishedAt':auto['finishedAt'],'bones':len(rig.data.bones),'clips':[clip['name'] for clip in g['animations']],'targets':targets,'fittedMeshes':required,'fixedAppearanceSamplesChecked':checked,'embeddedImages':len(g['images']),'editHeadWideMaxDeltaMeters':morph_deltas,'boneEditMaxDeltaMeters':bone_delta,'negativeControlsPassed':['missing fitted target','missing clip']}
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
