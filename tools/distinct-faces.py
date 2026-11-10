"""Original MIT face proportions layered on the licensed, retained portrait foundation.
Deterministic shared-space deltas keep fitted face parts together, without replacing
anatomy, UVs, materials, weights, old shape keys or waist/pose fixes. Run after portrait-human.py.
"""
import bpy, pathlib, json, math, runpy, struct
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source'; OUT=ROOT/'assets/human'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'foundation.blend'))
rig=bpy.data.objects['FoundationRig']
rig.animation_data_clear()
for action in list(bpy.data.actions):
 if action.name.split('.')[0] in ['relaxed','tpose','wave','stride']:bpy.data.actions.remove(action)
for bone in rig.pose.bones:bone.matrix_basis.identity()
CONTROL_NAMES={
 'headWidth':['HeadNarrow','HeadWide'], 'headHeight':['HeadShort','HeadLong'],
 'cheeks':['CheeksLean','CheeksFull'], 'chin':['ChinShort','ChinLong'],
 'noseWidth':['NoseWingsNarrow','NoseWingsWide'], 'noseProjection':['NoseRetracted','NoseProjected'],
 'eyeSpacing':['EyesClose','EyesWide'], 'browHeight':['BrowsLow','BrowsHigh'],
 'lips':['LipsThin','LipsFull'],
}

def smooth(a,b,t):
 u=np.clip((t-a)/(b-a),0,1);return u*u*(3-2*u)
def bell(t,center,width):return np.exp(-((t-center)/width)**2)
def delta(control,co):
 x,y,z=co.T; ax=np.abs(x); side=np.sign(x); result=np.zeros_like(co)
 head=smooth(1.33,1.40,z)
 front=1-smooth(-.095,-.055,y)
 if control=='headWidth':result[:,0]=x*.16*head
 elif control=='headHeight':result[:,2]=(z-1.445)*.16*head
 elif control=='cheeks':
  w=bell(ax,.048,.026)*bell(z,1.425,.031)*front
  result[:,0]=side*.006*w;result[:,1]=-.0045*w
 elif control=='chin':
  w=bell(x,0,.044)*smooth(1.33,1.355,z)*(1-smooth(1.36,1.399,z))*front
  result[:,2]=-.010*w;result[:,1]=-.004*w
 elif control=='noseWidth':
  w=bell(x,0,.027)*bell(z,1.435,.023)*(1-smooth(-.127,-.102,y))
  result[:,0]=x*.24*w
 elif control=='noseProjection':
  w=(1-smooth(.014,.040,ax))*smooth(1.400,1.420,z)*(1-smooth(1.452,1.480,z))*(1-smooth(-.10,-.02,y))
  result[:,1]=-.010*w
 elif control=='eyeSpacing':
  w=smooth(0,.020,ax)*(1-smooth(.052,.079,ax))*(1-smooth(.020,.043,np.abs(z-1.460)))*front
  result[:,0]=side*.0055*w
 elif control=='browHeight':
  w=smooth(.003,.014,ax)*(1-smooth(.058,.078,ax))*bell(z,1.483,.014)*front
  result[:,2]=.008*w
 elif control=='lips':
  w=bell(x,0,.029)*bell(z,1.403,.012)*(1-smooth(-.130,-.108,y))
  result[:,2]=(z-1.403)*.65*w;result[:,1]=-.0045*w;result[:,0]=x*.12*w
 else:raise ValueError(control)
 result*=smooth(1.33,1.35,z)[:,None]
 return result

# All pieces share the same continuous warp. There are no independent approximate
# eye or brow placement offsets in runtime and every exported shape remains editable.
for name in ['HumanBody','Eyes','Iris','Cornea','Brows','Lashes','HairCrop','HairStrands']:
 ob=bpy.data.objects[name]
 if not ob.data.shape_keys:ob.shape_key_add(name='Basis')
 for key in ob.data.shape_keys.key_blocks:key.value=0
 basis=ob.data.shape_keys.key_blocks[0]
 co=np.empty(len(basis.data)*3,dtype=np.float64);basis.data.foreach_get('co',co);co=co.reshape(-1,3)
 for control,names in CONTROL_NAMES.items():
  d=delta(control,co)
  for sign,keyname in zip([-1,1],names):
   old=ob.data.shape_keys.key_blocks.get(keyname)
   if old:ob.shape_key_remove(old)
   key=ob.shape_key_add(name=keyname,from_mix=False);key.value=0;key.data.foreach_set('co',(co+sign*d).ravel())
 ob.data.update()
pose_tools=runpy.run_path(str(ROOT/'tools/pose-human.py'));pose_tools['build_poses'](rig)
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.objects:
 if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
for ob in bpy.data.objects:
 if ob.type=='MESH' and ob.data.shape_keys:
  for key in ob.data.shape_keys.key_blocks:key.value=0
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'foundation.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'foundation.glb'),export_format='GLB',use_selection=True,export_apply=False,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_skins=True,export_morph=True,export_yup=True)
runpy.run_path(str(ROOT/'tools/pack-pose-tracks.py'))['pack_pose_tracks'](OUT/'foundation.glb',pose_tools['POSE_CORRECTIVES'])
manifest=json.loads((OUT/'manifest.json').read_text());manifest['morphs'].update(CONTROL_NAMES);manifest['distinctFaces']={'version':1,'controls':list(CONTROL_NAMES),'license':'MIT original shared-space deformation fields; retained anatomy CC0','neutral':.5};(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Retain the existing scalp alpha cutoff, which Blender exports as blend by default.
p=OUT/'foundation.glb';raw=p.read_bytes();n=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+n]);binary=bytearray(raw[28+n:])
# Blender adds color-profile chunks to generated packed roughness PNGs when
# roundtripping this source. Roughness is linear data, not color. Retain its
# original pixel payload and metadata contract without recompressing it.
for im in gltf.get('images',[]):
 if 'roughness' not in im.get('name','').lower():continue
 view=gltf['bufferViews'][im['bufferView']];offset=view.get('byteOffset',0);data=bytes(binary[offset:offset+view['byteLength']])
 if not data.startswith(b'\x89PNG\r\n\x1a\n'):continue
 clean=bytearray(data[:8]);at=8
 while at<len(data):
  length=struct.unpack_from('>I',data,at)[0];end=at+length+12
  if data[at+4:at+8] not in [b'sRGB',b'gAMA',b'cHRM']:clean.extend(data[at:end])
  at=end
 binary[offset:offset+view['byteLength']]=clean+b'\0'*(view['byteLength']-len(clean));view['byteLength']=len(clean)
for m in gltf['materials']:
 if m['name']=='Hair':m['alphaMode']='MASK';m['alphaCutoff']=.5
chunk=json.dumps(gltf,separators=(',',':')).encode();chunk+=b' '*((-len(chunk))%4)
p.write_bytes(struct.pack('<III',0x46546c67,2,28+len(chunk)+len(binary))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+struct.pack('<II',len(binary),0x004e4942)+binary)
print('DISTINCT_FACES_DONE')
