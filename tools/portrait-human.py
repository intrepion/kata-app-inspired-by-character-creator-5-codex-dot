"""Original procedural portrait detail layered onto the retained licensed foundation.
No external downloads. Run with Blender: blender -b --python tools/portrait-human.py.
Idempotent: replaces named portrait attachments and textures; body/garments remain untouched.
"""
import bpy, math, pathlib, json, random, runpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
ROOT=pathlib.Path(__file__).resolve().parents[1]; SOURCE=ROOT/'assets/source'; OUT=ROOT/'assets/human'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'foundation.blend'))
rig=bpy.data.objects['FoundationRig'];body=bpy.data.objects['HumanBody'];cap=bpy.data.objects['HairCrop'];eyes=bpy.data.objects['Eyes']
for name in ['Brows','Lashes','Iris','Cornea','HairStrands']:
 if bpy.data.objects.get(name):bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
for data in list(bpy.data.meshes):
 if data.users==0 and data.name.split('.')[0] in ['Brows','Lashes','Iris','Cornea','HairStrands']:bpy.data.meshes.remove(data)
# Always evaluate fitting on the authored neutral rest surface.
rig.animation_data_clear()
for action in list(bpy.data.actions):
 if action.name.split('.')[0] in ['relaxed','tpose','wave','stride']:bpy.data.actions.remove(action)
for bone in rig.pose.bones:bone.matrix_basis.identity()
for ob in [body,cap]:
 if ob.data.shape_keys:
  for k in ob.data.shape_keys.key_blocks:k.value=0
rng=np.random.default_rng(24011)
def image(name,array,color=False):
 a=np.asarray(array,dtype=np.float32)
 if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
 if a.shape[2]==3:a=np.concatenate([a,np.ones((*a.shape[:2],1),np.float32)],axis=2)
 old=bpy.data.images.get(name)
 if old:bpy.data.images.remove(old)
 im=bpy.data.images.new(name,width=a.shape[1],height=a.shape[0],alpha=True)
 im.colorspace_settings.name='sRGB' if color else 'Non-Color';im.pixels.foreach_set(a.ravel());im.filepath_raw=str(SOURCE/(name+'.png'));im.file_format='PNG';im.save();im.pack();return im
def texture(mat,im,input_name):
 bs=mat.node_tree.nodes.get('Principled BSDF');n=mat.node_tree.nodes.new('ShaderNodeTexImage');n.image=im;mat.node_tree.links.new(n.outputs['Color'],bs.inputs[input_name]);return n
def material(name,color=(1,1,1),rough=.6):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;m.node_tree.nodes.clear();bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface']);bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;return m
# Seeded, restrained pore detail. The authored diffuse skin is retained unchanged.
n=1024;noise=rng.random((n,n));smooth=(noise+np.roll(noise,1,0)+np.roll(noise,1,1))/3
height=(smooth-.5)*.10;dx=np.roll(height,-1,1)-np.roll(height,1,1);dy=np.roll(height,-1,0)-np.roll(height,1,0)
normal=np.stack([.5-dx,.5-dy,np.ones((n,n))],axis=2)
skin=bpy.data.materials['Skin'];bs=skin.node_tree.nodes.get('Principled BSDF')
# Remove previous generated maps on reruns, retaining only the original diffuse texture.
for node in list(skin.node_tree.nodes):
 if node.type in ['NORMAL_MAP'] or (node.type=='TEX_IMAGE' and node.image and node.image.name.startswith('portrait_')):skin.node_tree.nodes.remove(node)
normaltex=skin.node_tree.nodes.new('ShaderNodeTexImage');normaltex.image=image('portrait_skin_normal',normal)
norm=skin.node_tree.nodes.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=.32;skin.node_tree.links.new(normaltex.outputs['Color'],norm.inputs['Color']);skin.node_tree.links.new(norm.outputs['Normal'],bs.inputs['Normal'])
texture(skin,image('portrait_skin_roughness',np.clip(.58+(smooth-.5)*.18,.45,.72)),'Roughness');bs.inputs['IOR'].default_value=1.4
# Original anisotropic strand atlas; the scalp and ribbon hair share a neutral tintable map.
y,x=np.mgrid[0:512,0:512]/512
stripes=np.sin(2*math.pi*(x*137+.7*np.sin(y*9)+.2*np.sin(x*31+y*15)))
strand=np.clip(.55+.055*stripes+.055*rng.normal(size=(512,512)),.19,.95)
hairmat=material('Hair',rough=.68);hairimage=image('portrait_hair',strand,color=True);texture(hairmat,hairimage,'Base Color')
strandmat=material('HairStrands',rough=.67);texture(strandmat,hairimage,'Base Color')
texture(hairmat,image('portrait_hair_roughness',.53+.13*(1-strand)),'Roughness')
hairmat.use_backface_culling=False
cap.data.materials.clear();cap.data.materials.append(hairmat)
# Bring the scalp underlay close to skin instead of retaining a 6 mm helmet.
scalp_bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[tuple(p.vertices) for p in body.data.polygons])
for vertex in cap.data.vertices:
 point,normal,_,_=scalp_bvh.find_nearest(vertex.co);delta=point+normal*.0012-vertex.co
 for key in cap.data.shape_keys.key_blocks:key.data[vertex.index].co+=delta
 vertex.co+=delta
cap.data.update()
for loop in cap.data.loops:
 co=cap.data.vertices[loop.vertex_index].co;cap.data.uv_layers.active.data[loop.index].uv=(math.atan2(co.x,-(co.y+.04))/(2*math.pi)+.5,(co.z-1.44)/.14)
# A dithered taper at the actual boundary breaks the hard cap edge.
edges={}
for poly in cap.data.polygons:
 for e in poly.edge_keys:edges[e]=edges.get(e,0)+1
boundary=sorted({i for e,c in edges.items() if c==1 for i in e})
points=sorted((math.atan2(cap.data.vertices[i].co.x,-(cap.data.vertices[i].co.y+.04))/(2*math.pi)+.5,cap.data.vertices[i].co.z) for i in boundary)
bu=np.array([u for u,z in points]);bz=np.array([z for u,z in points])
edge=np.interp(x,np.concatenate([bu-1,bu,bu+1]),np.tile(bz,3))
coverage=np.clip((1.44+y*.14-edge)/.017,0,1)
alpha=(rng.random(coverage.shape)<coverage).astype(float)
capimage=image('portrait_hair_cap',np.dstack([strand,strand,strand,alpha]),color=True)
tex=texture(hairmat,capimage,'Base Color');hairmat.node_tree.links.new(tex.outputs['Alpha'],hairmat.node_tree.nodes.get('Principled BSDF').inputs['Alpha']);hairmat.surface_render_method='DITHERED'
browmat=material('Brows',rough=.85);texture(browmat,image('portrait_brow',np.clip(strand*.85,.1,.8),color=True),'Base Color')
lashmat=material('Lashes',(.025,.018,.014),.7)
# Spatial fits and full inherited morph deltas keep brows/lashes attached to eyelids.
verts=[v.co.copy() for v in body.data.vertices];faces=[tuple(p.vertices) for p in body.data.polygons]
bvh=BVHTree.FromPolygons(verts,faces);kd=KDTree(len(verts))
for i,v in enumerate(verts):kd.insert(v,i)
kd.balance()
def fit(x,z,offset=.0007):
 co,no,idx,d=bvh.ray_cast(Vector((x,-.6,z)),Vector((0,1,0)))
 if co is None:raise ValueError(('Missing facial fit',x,z))
 return co+no*offset

def mesh(name,coords,faces,uvs,mat,morph=True,donor=body):
 me=bpy.data.meshes.new(name);me.from_pydata(coords,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);ob.parent=rig;me.materials.append(mat)
 uv=me.uv_layers.new(name='UVMap')
 for poly in me.polygons:
  poly.use_smooth=True
  for li in poly.loop_indices:uv.data[li].uv=uvs[me.loops[li].vertex_index]
 # Smooth inverse-distance transfer from nearby source vertices avoids snapping at crossings.
 local=KDTree(len(donor.data.vertices))
 for v in donor.data.vertices:local.insert(v.co,v.index)
 local.balance();influences=[]
 for co in coords:
  near=local.find_n(Vector(co),3);ws=[1/max(d,.00015)**2 for _,_,d in near];total=sum(ws);influences.append([(j,w/total) for (_,j,_),w in zip(near,ws)])
 groups={g.index:ob.vertex_groups.new(name=g.name) for g in donor.vertex_groups}
 for i,near in enumerate(influences):
  weights={}
  for j,w in near:
   for g in donor.data.vertices[j].groups:
    if donor.vertex_groups[g.group].name in rig.data.bones:weights[g.group]=weights.get(g.group,0)+g.weight*w
  keep=sorted(weights.items(),key=lambda x:-x[1])[:4];s=sum(w for _,w in keep)
  for g,w in keep:groups[g].add([i],w/s,'REPLACE')
 if morph and donor.data.shape_keys:
  ob.shape_key_add(name='Basis');basis=donor.data.shape_keys.key_blocks[0]
  for sk in list(donor.data.shape_keys.key_blocks)[1:]:
   nk=ob.shape_key_add(name=sk.name)
   for i,near in enumerate(influences):nk.data[i].co=Vector(coords[i])+sum(((sk.data[j].co-basis.data[j].co)*w for j,w in near),Vector())
 mod=ob.modifiers.new('Weighted Skeleton','ARMATURE');mod.object=rig;return ob

def ribbons(paths,widths):
 coords=[];faces=[];uv=[]
 for path,width in zip(paths,widths):
  start=len(coords)
  for j,p in enumerate(path):
   tangent=(path[min(j+1,len(path)-1)]-path[max(0,j-1)]).normalized();side=tangent.cross(Vector((0,-1,.4))).normalized()*width*(1-.88*j/(len(path)-1))
   coords.extend([p-side,p+side]);uv.extend([(0,j/(len(path)-1)),(1,j/(len(path)-1))])
   if j:faces.append((start+2*j-2,start+2*j-1,start+2*j+1,start+2*j))
 return coords,faces,uv
r=random.Random(2411);paths=[];widths=[]
for sign in [-1,1]:
 for i in range(200):
  t=r.random();x=.012+t*.043;z=1.4775+.006*math.sin(t*math.pi)-.004*t+(r.random()-.5)*.003
  path=[]
  for j in range(4):
   u=j/3;path.append(fit(sign*(x+u*.0035),z+u*(.0025-.004*t),.0006))
  paths.append(path);widths.append(.00012+r.random()*.00007)
mesh('Brows',*ribbons(paths,widths),browmat)
# Explicit upper/lower lid rim landmarks from the retained source topology.
upper=[(-.0146,-.1308,1.459),(-.020, -.1336,1.4673),(-.0286,-.1339,1.4663),(-.0361,-.1317,1.4665),(-.0428,-.126,1.462)]
lower=[(-.015,-.131,1.457),(-.0242,-.1303,1.4511),(-.029,-.1297,1.4507),(-.038,-.1265,1.4518),(-.0428,-.126,1.459)]
paths=[];widths=[]
for sign in [-1,1]:
 for row,points in enumerate([upper,lower]):
  for i in range(35 if row==0 else 20):
   t=(i+.5)/(35 if row==0 else 20)*(len(points)-1);a=int(t);p=Vector(points[a]).lerp(Vector(points[min(a+1,4)]),t-a);p.x=abs(p.x)*sign;p.y-=.0005
   length=(.0024 if row==0 else .0014)*( .65+.35*math.sin(i*.8))
   paths.append([p+Vector((sign*length*u*.35,-length*u,.001*u*u*(1 if row==0 else -.5))) for u in [0,.33,.67,1]])
   widths.append(.00009 if row==0 else .00006)
mesh('Lashes',*ribbons(paths,widths),lashmat)
# Dense, tapered short strands rise above the textured scalp rather than a smooth helmet.
paths=[];widths=[]
cap.data.calc_loop_triangles();triangles=list(cap.data.loop_triangles)
areas=[(cap.data.vertices[t.vertices[1]].co-cap.data.vertices[t.vertices[0]].co).cross(cap.data.vertices[t.vertices[2]].co-cap.data.vertices[t.vertices[0]].co).length for t in triangles]
for tri in r.choices(triangles,weights=areas,k=3000):
 a,b,c=[cap.data.vertices[i] for i in tri.vertices];u=math.sqrt(r.random());v=r.random();p=a.co*(1-u)+b.co*u*(1-v)+c.co*u*v;no=(a.normal*(1-u)+b.normal*u*(1-v)+c.normal*u*v).normalized()
 top=max(0,min(1,(p.z-1.51)/.035));length=(.002+r.random()*.003)*(1-top)+(.014+r.random()*.014)*top;flow=Vector((.7+r.uniform(-.25,.25),.75,.12));flow=(flow-no*flow.dot(no)).normalized()
 paths.append([p+no*(length*(.55*math.sin(t*math.pi*.8)+.1*t))+flow*(length*t) for t in [0,.25,.5,.75,1]])
 widths.append(.00012+r.random()*.00013)
mesh('HairStrands',*ribbons(paths,widths),strandmat,donor=cap)
# Procedural iris with radial fibers, limbal ring and pupil, no baked-in catchlight.
n=512;y,x=np.mgrid[0:n,0:n];u=(x+.5)/n*2-1;v=(y+.5)/n*2-1;rad=np.sqrt(u*u+v*v);angle=np.arctan2(v,u)
fiber=.52+.14*np.sin(angle*91+rad*23)+.09*np.sin(angle*173-rad*47)+.06*rng.normal(size=(n,n));fiber=np.clip(fiber,.18,.9)
fiber*=np.clip((1-rad)*14,.15,1);fiber=np.where(rad<.31,.012,fiber);iris=material('Iris',rough=.42);texture(iris,image('portrait_iris',fiber,color=True),'Base Color')
# Sclera stays neutral; iris tint never multiplies the whites.
sclera=material('Eyes',(.72,.70,.66),.3);eyes.data.materials.clear();eyes.data.materials.append(sclera)
cornea=material('Cornea',(1,1,1),.035);bs=cornea.node_tree.nodes.get('Principled BSDF');bs.inputs['Alpha'].default_value=.13;bs.inputs['Coat Weight'].default_value=1;bs.inputs['Coat Roughness'].default_value=.025;bs.inputs['IOR'].default_value=1.38;cornea.surface_render_method='DITHERED'
for name,mat,extra in [('Iris',iris,0),('Cornea',cornea,.00018)]:
 co=[];fa=[];uv=[]
 for sign in [-1,1]:
  center=Vector((sign*.0302,-.1328-extra,1.4622));start=len(co);co.append(center+Vector((0,-.00065,0)));uv.append((.5,.5))
  for ring in range(1,9):
   radius=.0057*ring/8
   for k in range(48):
    a=k*2*math.pi/48;co.append(center+Vector((math.cos(a)*radius,-.00065*(1-(ring/8)**2),math.sin(a)*radius)));uv.append((.5+math.cos(a)*ring/16,.5+math.sin(a)*ring/16))
  for k in range(48):fa.append((start,start+1+(k+1)%48,start+1+k))
  for ring in range(1,8):
   for k in range(48):
    a=start+1+(ring-1)*48+k;b=start+1+(ring-1)*48+(k+1)%48;c=start+1+ring*48+(k+1)%48;d=start+1+ring*48+k;fa.append((a,b,c,d))
 mesh(name,co,[tuple(reversed(f)) for f in fa],uv,mat,morph=False,donor=eyes)
# Restore authored clips and pose correction packing; no base body/garment reconstruction.
pose_tools=runpy.run_path(str(ROOT/'tools/pose-human.py'));poses=pose_tools['build_poses'](rig)
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.objects:
 if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'foundation.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'foundation.glb'),export_format='GLB',use_selection=True,export_apply=False,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_skins=True,export_morph=True,export_yup=True)
runpy.run_path(str(ROOT/'tools/pack-pose-tracks.py'))['pack_pose_tracks'](OUT/'foundation.glb',pose_tools['POSE_CORRECTIVES'])
man=json.loads((OUT/'manifest.json').read_text());man['materials']['hairColor']=['Hair','HairStrands','Brows'];man['materials']['eyeColor']='Iris';man['hairMeshes']=['HairCrop','HairStrands'];man['license']='CC0-1.0 foundation + MIT original portrait additions (see docs/ASSET-LICENSES.md)';man['faceTargetZ']=.045;man['portrait']={'version':1,'originalDetails':['normal','roughness','hair','brows','lashes','iris','cornea'],'license':'MIT (generated original detail); existing foundation CC0'};(OUT/'manifest.json').write_text(json.dumps(man,indent=2)+'\n')
import struct
path=OUT/'foundation.glb';data=path.read_bytes();length=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+length]);binary=data[20+length:]
for m in gltf['materials']:
 if m['name']=='Hair':m['alphaMode']='MASK';m['alphaCutoff']=.5
chunk=json.dumps(gltf,separators=(',',':')).encode();chunk+=b' '*((-len(chunk))%4)
path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(chunk)+len(binary))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+binary)
print('PORTRAIT_DONE')
