import bpy,json,pathlib,math,sys
from mathutils import Vector
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'assets/human'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
input_path=pathlib.Path(args[0]) if args else OUT/'foundation.glb'
report_path=pathlib.Path(args[1]) if len(args)>1 else OUT/'qa.json'
bpy.ops.import_scene.gltf(filepath=str(input_path))
# Three.js names mesh nodes, while Blender may name their animated mesh data Mesh_N.
# Materials retain stable semantic names in both the source GLB and browser export.
def role(o):
 return next((name for material,name in [('Skin','HumanBody'),('Outfit','Outfit'),('Pants','Pants'),('Hair','HairCrop')] if any(m and m.name.split('.')[0]==material for m in o.data.materials)),o.data.name)
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and role(o)=='HumanBody');meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
report={'blender':bpy.app.version_string,'source':input_path.name,'bones':len(rig.data.bones),'meshes':{},'animations':[a.name for a in bpy.data.actions]}
for o in meshes:
 sums=[sum(g.weight for g in v.groups) for v in o.data.vertices]
 report['meshes'][o.name]={'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'uvLayers':len(o.data.uv_layers),'morphs':[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],'unweightedVertices':sum(x<.98 for x in sums),'materials':[m.name for m in o.data.materials]}
def vertices():
 bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());return [v.co.copy() for v in ev.data.vertices]
rig.animation_data_clear();base=vertices();body.data.shape_keys.key_blocks['JawBroad'].value=1;changed=vertices();report['morphEditMaxDelta']=max((a-b).length for a,b in zip(base,changed));body.data.shape_keys.key_blocks['JawBroad'].value=0
base=vertices();b=rig.pose.bones['lowerarm_l'];b.rotation_mode='XYZ';b.rotation_euler.x+=.5;changed=vertices();report['boneEditMaxDelta']=max((a-b).length for a,b in zip(base,changed));b.rotation_euler.x-=.5
# glTF UV seam splits are welded by position for connected-surface checks.
for o in meshes:
 if role(o) not in ['HairCrop','Outfit','Pants']:continue
 groups={};index=[]
 for v in o.data.vertices:
  key=tuple(round(x,5) for x in v.co);index.append(groups.setdefault(key,len(groups)))
 adj={i:set() for i in groups.values()}
 for e in o.data.edges:
  a,b=(index[i] for i in e.vertices);adj[a].add(b);adj[b].add(a)
 unseen=set(adj);sizes=[]
 while unseen:
  stack=[unseen.pop()];count=0
  while stack:
   a=stack.pop();count+=1
   for b in adj[a]&unseen:unseen.remove(b);stack.append(b)
  sizes.append(count)
 report['meshes'][o.name]['connectedSurfaceSizes']=sorted(sizes,reverse=True)
report['embeddedImages']=[{'name':im.name,'width':im.size[0],'height':im.size[1]} for im in bpy.data.images if im.size[0]>0 and im.name!='Render Result']
report['passed']=report['bones']>=50 and report['morphEditMaxDelta']>.001 and report['boneEditMaxDelta']>.01 and all(v['uvLayers'] and v['unweightedVertices']==0 for v in report['meshes'].values()) and len(report['animations'])>=4 and all(len(v.get('connectedSurfaceSizes',[1]))==1 for v in report['meshes'].values())
report_path.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['passed']
