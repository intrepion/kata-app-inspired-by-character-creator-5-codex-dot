"""Build the Persona foundation using pinned MPFB CC0 assets. Run through rebuild-human.sh."""
import bpy,sys,os,json,gzip,math,pathlib
from mathutils import Vector,Quaternion
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'assets/human'; SOURCE=ROOT/'assets/source'
OUT.mkdir(parents=True,exist_ok=True);SOURCE.mkdir(parents=True,exist_ok=True)
MPFB=pathlib.Path(os.environ.get('MPFB_SOURCE','/tmp/persona-mpfb')); MH=pathlib.Path(os.environ.get('MH_SOURCE','/tmp/persona-mh'))
sys.path.insert(0,str(MPFB/'src'));import mpfb
bpy.utils.extension_path_user=lambda *a,**k:str(pathlib.Path(os.environ.get('BLENDER_USER_RESOURCES','/tmp/persona-home'))/'mpfb')
bpy.context.preferences.addons.new().module='mpfb';mpfb.register()
from mpfb.services.humanservice import HumanService
from mpfb.services.targetservice import TargetService
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
macro=TargetService.get_default_macro_info_dict();macro.update(gender=.65,age=.4,muscle=.55,weight=.45)
h=HumanService.create_human(macro_detail_dict=macro);rig=HumanService.add_builtin_rig(h,'game_engine');rig.name='FoundationRig'
eyes=HumanService.add_mhclo_asset(str(MH/'makehuman/data/eyes/high-poly/high-poly.mhclo'),h,asset_type='Eyes',subdiv_levels=0)
eyes.name='Eyes';eyes.data.materials[0].name='Eyes'
# Freeze macro mix while retaining the complete helper geometry and source vertex indices.
k=h.shape_key_add(name='FrozenAdult',from_mix=True); coords=[v.co.copy() for v in k.data];h.shape_key_clear()
for v,c in zip(h.data.vertices,coords):v.co=c
for mod in list(h.modifiers):
 if mod.type!='ARMATURE':h.modifiers.remove(mod)
h.data.update()
h.shape_key_add(name='Basis')
morphs={'build':['BuildNarrow','BuildBroad'],'shoulders':['ShouldersNarrow','ShouldersBroad'],'jaw':['JawNarrow','JawBroad'],'nose':['NoseNarrow','NoseBroad'],'eyes':['EyesSmall','EyesLarge']}
paths={'build':['torso/torso-scale-horiz','torso/torso-scale-depth'],'shoulders':['torso/measure-shoulder-dist'],'jaw':['chin/chin-width'],'nose':['nose/nose-width1','nose/nose-width2','nose/nose-width3'],'eyes':['eyes/l-eye-scale','eyes/r-eye-scale']}
for control,names in morphs.items():
 for side,name in enumerate(names):
  key=h.shape_key_add(name=name)
  for p in paths[control]:
   filename=MPFB/'src/mpfb/data/targets'/(p+('-incr' if side else '-decr')+'.target.gz')
   for line in gzip.open(filename,'rt'):
    if line.startswith('#') or not line.strip():continue
    i,x,y,z=line.split();key.data[int(i)].co+=Vector((float(x),-float(z),float(y)))*.055
# Extract a body or fitted garment from shared topology, keeping exact weights, UVs, and morphs.
def extract(name,predicate,offset=0):
 faces=[p for p in h.data.polygons if predicate(p)]
 ids=sorted({i for p in faces for i in p.vertices}); imap={v:i for i,v in enumerate(ids)}
 me=bpy.data.meshes.new(name);me.from_pydata([h.data.vertices[i].co+h.data.vertices[i].normal*offset for i in ids],[],[[imap[i] for i in p.vertices] for p in faces]);me.update()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);ob.parent=rig
 uv=me.uv_layers.new(name='UVMap')
 for dst,p in zip(me.polygons,faces):
  for a,b in zip(dst.loop_indices,p.loop_indices):uv.data[a].uv=h.data.uv_layers.active.data[b].uv
 for bone in rig.data.bones:
  vg=ob.vertex_groups.new(name=bone.name);src=h.vertex_groups.get(bone.name)
  if src:
   for old,new in imap.items():
    w=next((g.weight for g in h.data.vertices[old].groups if g.group==src.index),0)
    if w>0:vg.add([new],w,'REPLACE')
 for sk in h.data.shape_keys.key_blocks:
  nk=ob.shape_key_add(name=sk.name)
  for new,old in enumerate(ids):nk.data[new].co=sk.data[old].co+h.data.vertices[old].normal*offset
 mod=ob.modifiers.new('Weighted Skeleton','ARMATURE');mod.object=rig
 for p in me.polygons:p.use_smooth=True
 return ob
bodygroup=h.vertex_groups['body'].index;tights=h.vertex_groups['helper-tights'].index;hairgroup=h.vertex_groups['helper-hair'].index
has=lambda p,g:all(any(x.group==g for x in h.data.vertices[i].groups) for i in p.vertices)
body=extract('HumanBody',lambda p:has(p,bodygroup))
# Separate fitted sports top and trousers use the CC0 clothing helper topology, not body-face recoloring.
shirt=extract('Outfit',lambda p:has(p,tights) and p.center.z> .94 and p.center.z<1.43 and abs(p.center.x)<.28,.012)
pants=extract('Pants',lambda p:has(p,tights) and p.center.z<=.975 and p.center.z>.13 and abs(p.center.x)<.30,.01)
body_height=max(v.co.z for v in body.data.vertices)
hair=extract('HairCrop',lambda p:has(p,bodygroup) and p.center.z>body_height-.096-.35*p.center.y,.006)
# Smooth deliberate garment and hair boundary loops without altering their interior topology.
def clean_boundary(ob,iterations=10):
 counts={}
 for p in ob.data.polygons:
  for edge in p.edge_keys:counts[edge]=counts.get(edge,0)+1
 neighbors={}
 for (a,b),count in counts.items():
  if count==1:neighbors.setdefault(a,[]).append(b);neighbors.setdefault(b,[]).append(a)
 for key in ob.data.shape_keys.key_blocks:
  for _ in range(iterations):
   updates={i:key.data[i].co.lerp(sum((key.data[j].co for j in ns),Vector())/len(ns),.35) for i,ns in neighbors.items()}
   for i,co in updates.items():key.data[i].co=co
 for v,k in zip(ob.data.vertices,ob.data.shape_keys.key_blocks[0].data):v.co=k.co
 ob.data.update()
for ob in [shirt,pants,hair]:clean_boundary(ob)
# A level overlapping waistband removes staircase cut edges.
for sk in shirt.data.shape_keys.key_blocks:
 for v in sk.data:
  if v.co.z<.985:v.co.z=.955
for v,k in zip(shirt.data.vertices,shirt.data.shape_keys.key_blocks[0].data):v.co=k.co
bpy.data.objects.remove(h,do_unlink=True)
def material(name,color,rough=.65,texture=None):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=rough
 if texture:
  im=bpy.data.images.load(str(texture));im.pack();tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;m.node_tree.links.new(tex.outputs['Color'],n.inputs['Base Color'])
 return m
skinpath=SOURCE/'skin.png'
body.data.materials.append(material('Skin',(.65,.42,.29),.62,skinpath if skinpath.exists() else None))
shirt.data.materials.append(material('Outfit',(.045,.17,.18),.85));pants.data.materials.append(material('Pants',(.035,.045,.065),.9));hair.data.materials.append(material('Hair',(.035,.018,.012),.85))
# Pose bones by world-axis rotations mapped into each bone's local rest basis.
def rotate(name,axis,degrees):
 bone=rig.pose.bones[name];local=bone.bone.matrix_local.to_3x3().inverted()@Vector(axis);bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion(local,math.radians(degrees))
poses={'relaxed':{},'tpose':{'upperarm_l':((0,1,0),-45),'upperarm_r':((0,1,0),45),'lowerarm_l':((0,0,1),-35),'lowerarm_r':((0,0,1),35)},'wave':{'upperarm_l':((0,1,0),-105),'lowerarm_l':((1,0,0),-65),'hand_l':((0,1,0),12)},'stride':{'thigh_l':((1,0,0),-20),'thigh_r':((1,0,0),18),'calf_r':((1,0,0),-18),'upperarm_l':((1,0,0),20),'upperarm_r':((1,0,0),-20)}}
def aim(name,direction):
 bpy.context.view_layer.update();b=rig.pose.bones[name]
 q=(b.tail-b.head).rotation_difference(Vector(direction));m=(q.to_matrix().to_4x4()@b.matrix);m.translation=b.head;b.matrix=m
 bpy.context.view_layer.update()
for name,changes in poses.items():
 rig.animation_data_clear()
 for b in rig.pose.bones:b.rotation_mode='QUATERNION';b.rotation_quaternion=(1,0,0,0)
 for bone,(axis,deg) in changes.items():rotate(bone,axis,deg)
 if name=='tpose':
  for suffix,sign in [('l',1),('r',-1)]:
   aim('upperarm_'+suffix,(sign,0,0));aim('lowerarm_'+suffix,(sign,0,0));aim('hand_'+suffix,(sign,0,0))
 if name=='wave':
  aim('upperarm_l',(.8,0,.5));aim('lowerarm_l',(0,0,1));aim('hand_l',(0,0,1))
 for frame in [0,1]:
  for b in rig.pose.bones:b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name)
 action=rig.animation_data.action;action.name=name;action.use_fake_user=True
 track=rig.animation_data.nla_tracks.new();track.name=name;strip=track.strips.new(name,0,action);track.mute=True
rig.animation_data.action=None
for b in rig.pose.bones:b.rotation_quaternion=(1,0,0,0)
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for ob in [rig,body,eyes,shirt,pants,hair]:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
for im in bpy.data.images:
 if im.source=='FILE':im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'foundation.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'foundation.glb'),export_format='GLB',use_selection=True,export_apply=False,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_skins=True,export_morph=True,export_yup=True)
manifest={'model':'foundation.glb','units':'meters','up':'+Y','front':'+Z','morphs':morphs,'materials':{'skin':'Skin','outfit':'Outfit','pants':'Pants','hairColor':'Hair'},'hairMeshes':['HairCrop'],'skinReference':'#b88a6a','faceTargetY':round(body_height-.105,3),'poses':list(poses),'source':'../source/foundation.blend','license':'CC0-1.0 (see docs/ASSET-LICENSES.md)'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('FOUNDATION_BUILD_DONE',[(o.name,len(o.data.vertices)) for o in [body,eyes,shirt,pants,hair]])
