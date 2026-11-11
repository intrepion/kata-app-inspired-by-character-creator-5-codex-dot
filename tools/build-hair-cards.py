"""Original layered short groom, authored in Blender. No downloaded hair assets.
Curve guides remain editable in the .blend; the delivery is a baked skinned mesh.
Run: Blender -b --python-exit-code 1 --python tools/build-hair-cards.py
"""
import bpy, math, json, pathlib, hashlib
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'assets/human/hair-cards'; OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/source/foundation.blend'))
cap=bpy.data.objects['HairCrop']; rig=cap.parent; mesh=cap.data; mesh.calc_loop_triangles()
points=[v.co.copy() for v in mesh.vertices]; tris=[tuple(t.vertices) for t in mesh.loop_triangles]
bvh=BVHTree.FromPolygons(points,tris,all_triangles=True)
rng=np.random.default_rng(141126)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
def fit(point):
    p,n,idx,d=bvh.find_nearest(Vector(point)); ids=tris[idx]
    # Use interpolated source vertex normals so card arcs don't inherit facets.
    bary=barycentric_transform(p,*(points[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    normal=sum((mesh.vertices[i].normal*w for i,w in zip(ids,bary)),Vector()).normalized()
    return p,normal,ids,bary

def save_image(name,pixels,color=True):
    h,w=pixels.shape[:2]; im=bpy.data.images.new(name,width=w,height=h,alpha=True)
    im.colorspace_settings.name='sRGB' if color else 'Non-Color'; im.pixels.foreach_set(pixels.astype(np.float32).ravel())
    im.filepath_raw=str(OUT/(name+'.png'));im.file_format='PNG';im.save();im.pack();return im

# Original strand atlas: dense bases, loose locks, fine silhouette and hairline.
# Strand endpoints and S bends vary within each lock, not one rectangular alpha.
N=2048; W=N//8; yy=np.arange(N,dtype=np.float32); t=yy/(N-1)
atlas=np.zeros((N,N,4),np.float32); heights=np.zeros((N,N),np.float32)
for tile in range(8):
    density=[150,135,120,105,90,65,22,45][tile]
    for i in range(density):
        root=rng.uniform(.05,.95); end=rng.uniform(.72,.995); start=rng.uniform(0,.035)
        # Collective asymmetry preserves a lock; per-strand variation breaks tips.
        bend=(.045+.018*(tile%3))*np.sin(t*math.pi)+rng.uniform(-.028,.028)*np.sin(t*math.pi*2)
        center=(root+(0.5-root)*t**3*.35+bend+rng.uniform(-.03,.03)*t)*W
        width=rng.uniform(.65,1.45) * (1-smooth(.58,end,t)*.7)
        fade=smooth(start,start+.035,t)*(1-smooth(end-.07,end,t))
        tone=rng.uniform(.58,.79)*(1-.22*np.exp(-t*8))
        for dx in range(-4,5):
            x=np.rint(center).astype(int)+dx; ok=(x>=3)&(x<W-3)
            a=np.exp(-.5*((x-center)/np.maximum(width,.2))**2)*fade
            rows=np.where(ok)[0];cols=tile*W+x[ok];old=atlas[rows,cols,3];take=a[ok]>old
            rows=rows[take];cols=cols[take];av=a[ok][take]
            atlas[rows,cols,:3]=(tone[rows]*(.94+.06*np.cos(t[rows]*10)))[:,None]
            atlas[rows,cols,3]=av;heights[rows,cols]=av
    # Keep fine strand color under transparent pixels to avoid a dark mip border.
    strip=atlas[:,tile*W:(tile+1)*W];strip[:,:,:3][strip[:,:,3]<.015]=.58
image=save_image('original-strand-atlas',atlas)
dx=np.roll(heights,-1,1)-np.roll(heights,1,1); dy=np.roll(heights,-1,0)-np.roll(heights,1,0)
normal=np.dstack([-.72*dx,-.15*dy,np.ones_like(dx)]);normal/=np.linalg.norm(normal,axis=2)[...,None]
normalimage=save_image('original-strand-normal',np.dstack([normal*.5+.5,np.ones_like(dx)]),False)

# Coverage cap: rasterize scalp UV to anatomy, then original fine root stubble.
# A density taper, not a solid border, blends temples and front hairline.
uv=mesh.uv_layers.active; S=1024; coord=np.zeros((S,S,3),np.float32);valid=np.zeros((S,S),bool)
for tr in mesh.loop_triangles:
    q=np.array([uv.data[i].uv[:] for i in tr.loops]);p=np.array([points[i][:] for i in tr.vertices])
    if np.ptp(q[:,0])>.5:q[:,0][q[:,0]<.5]+=1
    for shift in [-1,0]:
        pix=(q+np.array([shift,0]))*(S-1);lo=np.maximum(np.floor(pix.min(0)).astype(int),0);hi=np.minimum(np.ceil(pix.max(0)).astype(int),S-1)
        if np.any(hi<lo):continue
        Y,X=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];a,b,c=pix;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-8:continue
        w0=((b[1]-c[1])*(X-c[0])+(c[0]-b[0])*(Y-c[1]))/den;w1=((c[1]-a[1])*(X-c[0])+(a[0]-c[0])*(Y-c[1]))/den;w2=1-w0-w1;inside=(w0>=0)&(w1>=0)&(w2>=0)
        reg=coord[lo[1]:hi[1]+1,lo[0]:hi[0]+1];reg[inside]=(w0[...,None]*p[0]+w1[...,None]*p[1]+w2[...,None]*p[2])[inside];valid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=inside
# geometric boundary distance in UV's anatomical columns
edges={}
for f in mesh.polygons:
    for a,b in f.edge_keys:
        k=tuple(sorted((tuple(round(v,6) for v in points[a]),tuple(round(v,6) for v in points[b]))));edges[k]=edges.get(k,0)+1
boundary_segments=[(Vector(e[0]),Vector(e[1])) for e,count in edges.items() if count==1]
boundary=[p for edge in boundary_segments for p in edge]
def boundary_distance(p):
    return min((p-(a+(b-a)*max(0,min(1,(p-a).dot(b-a)/(b-a).length_squared)))).length for a,b in boundary_segments)
x,y,z=coord.transpose(2,0,1);dist=np.full((S,S),1.,np.float32)
for p in boundary:dist=np.minimum(dist,np.sqrt((x-p.x)**2+(y-p.y)**2+(z-p.z)**2))
U,V=np.meshgrid(np.arange(S)/(S-1),np.arange(S)/(S-1));streak=.5+.5*np.sin(U*math.pi*2*790+V*26+np.sin(V*12)*.8)
root=np.zeros((S,S,4),np.float32);root[:,:,:3]=(.54+.10*streak)[:,:,None]
coverage=smooth(.001,.011,dist);root[:,:,3]=np.where(rng.random((S,S))<coverage,1.,0.)*valid
rootimage=save_image('original-scalp-roots',root)

# Materials use only portable PBR nodes. Browser adds matching anisotropy values.
def mat(name,im,normal=None):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(.18,.10,.065,1)
    n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Roughness'].default_value=.72;bs.inputs['Metallic'].default_value=0;bs.inputs['Specular IOR Level'].default_value=.25
    next(i for i in bs.inputs if i.name.startswith('Anisotropic') and 'Rotation' not in i.name).default_value=.50;bs.inputs['Anisotropic Rotation'].default_value=.25
    tex=n.new('ShaderNodeTexImage');tex.image=im;tex.interpolation='Linear';tint=n.new('ShaderNodeMixRGB');tint.name='Editable hair tint';tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(.067,.032,.019,1);l.new(tex.outputs['Color'],tint.inputs[1]);l.new(tint.outputs[0],bs.inputs['Base Color']);l.new(tex.outputs['Alpha'],bs.inputs['Alpha'])
    if normal:
        texn=n.new('ShaderNodeTexImage');texn.image=normal;nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.10;l.new(texn.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],bs.inputs['Normal'])
    m.surface_render_method='DITHERED';m.use_backface_culling=False;m['gltf_alpha_mode']='MASK';m['alpha_threshold']=.38
    return m
cardmat=mat('HairGroom',image,normalimage);rootmat=mat('HairCardRoot',rootimage)

# Copy the close scalp, fixing its wrap in UV without altering source .blend.
rootcap=cap.copy();rootcap.data=cap.data.copy();rootcap.name='HairCardRoot';bpy.context.collection.objects.link(rootcap);rootcap.data.materials.clear();rootcap.data.materials.append(rootmat)
for poly in rootcap.data.polygons:
    vals=[rootcap.data.uv_layers.active.data[i].uv.x for i in poly.loop_indices]
    if max(vals)-min(vals)>.5:
        for i in poly.loop_indices:
            if rootcap.data.uv_layers.active.data[i].uv.x<.5:rootcap.data.uv_layers.active.data[i].uv.x+=1

# Deliberately staggered guide layout. Three layers have distinct jobs.
# Coords are Blender Z-up; face points -Y. Side part is on character's left.
guides=bpy.data.collections.new('EDITABLE Hair Guide Curves');bpy.context.scene.collection.children.link(guides)
verts=[];faces=[];uvs=[];fits=[];card_meta=[]
def make_card(label,rootquery,direction,length,width,lift,layer,tile,tilt=0):
    requested_length=length
    def surface_at(q,strict=False):
        q=Vector(q)
        if 'side' in label:
            sign=1 if rootquery[0]>0 else -1; origin=Vector((sign*.25,q.y,q.z)); ray=Vector((-sign,0,0))
        elif 'back' in label:origin=Vector((q.x,.3,q.z));ray=Vector((0,-1,0))
        else:origin=Vector((q.x,q.y,2.0));ray=Vector((0,0,-1))
        hit,normal,idx,distance=bvh.ray_cast(origin,ray)
        return None if hit is None and strict else fit(hit if hit is not None else q)
    rootfit=surface_at(rootquery,not label.startswith('Fine'))
    if rootfit is None:return
    rp,rn,_,_=rootfit;flow=Vector(direction).normalized();side=flow.cross(rn).normalized();phase=float(rng.uniform(-.5,.5)); samples=[]
    # Stop before a guide leaves the actual scalp. Previously nearest-point
    # fallback folded whole card ends onto the boundary, producing teeth/hooks.
    peripheral='side' in label or 'back' in label
    for step in range(1,41):
        f=step/40;target=rp+flow*(length*f)+side*(math.sin(f*math.pi)*.0018*phase)
        if surface_at(target,True) is None:
            retreat=.003+(sum(map(ord,label))%17)/17*.002 if peripheral else .0015
            length=max(0,length*(step-1)/40-retreat);break
    if length<.0035:return
    steps=10;cols=3;first=len(verts)
    for j in range(steps+1):
        f=j/steps; target=rp+flow*(length*f)+side*(math.sin(f*math.pi)*.0018*phase)
        p,n,ids,w=surface_at(target)
        # Settle tips into the cut rather than leaving raised, hooked ends.
        h=.00065+layer*(1-smooth(.60,1,f))+lift*math.sin(math.pi*f)
        center=p+n*h
        tan=flow-n*flow.dot(n);tan.normalize(); across=tan.cross(n).normalized();across=(across*math.cos(tilt)+n*math.sin(tilt)).normalized()
        spread=width*(.80+.20*math.sin(f*math.pi))*(1-.97*smooth(.28,1,f))
        if not label.startswith('Fine'):spread*=max(.05,float(smooth(.001,.009,boundary_distance(p))))
        samples.append((center.copy(),spread))
        for k in range(cols):
            s=k-1;pos=center+across*(s*spread/2)+n*((1-s*s)*spread*.11)
            verts.append(tuple(pos));fits.append((ids,w.copy()));uvs.append(((tile+.025+(k/(cols-1))*.95)/8,f))
        if j:
            for k in range(cols-1):
                a=first+(j-1)*cols+k;b=a+cols;faces.append((a,a+1,b+1,b))
    cu=bpy.data.curves.new(label,'CURVE');cu.dimensions='3D';cu.resolution_u=8;sp=cu.splines.new('BEZIER');sp.bezier_points.add(4)
    for bp,(center,spread) in zip(sp.bezier_points,[samples[i] for i in [0,2,5,8,10]]):bp.co=center;bp.handle_left_type=bp.handle_right_type='AUTO';bp.radius=spread/width;bp.tilt=tilt
    ob=bpy.data.objects.new(label,cu);guides.objects.link(ob);ob.hide_render=True;ob.hide_set(True);ob['card_width']=width;ob['atlas_tile']=tile;ob['layer']=layer
    card_meta.append({'name':label,'root':list(rp),'direction':list(flow),'length':length,'requestedLength':requested_length,'trimmedAtBoundary':length<requested_length,'tipHeight':.00065,'width':width,'lift':lift,'layer':layer,'atlasTile':tile,'tilt':tilt})
# Dense staggered foundation, following backward/side-swept top growth.
for row,y0 in enumerate([-.123,-.108,-.090,-.072,-.054,-.036,-.018,.000]):
    half=.056*math.sqrt(max(.15,1-((y0+.043)/.103)**2))
    xs=np.arange(-half,half+.001,.006)
    for col,x0 in enumerate(xs):
        x0+=.003*(row%2);direction=(.30 if x0>-.03 else -.13,1,-.10 if y0>-.04 else .05)
        make_card(f'Base top {row:02d}-{col:02d}',(x0,y0,1.61),direction,.038+float(rng.uniform(-.006,.008)),.009,.0025,.0008,col%3,float(rng.uniform(-.10,.10)))
# Short side panels fan down and back; card ends differ instead of a bowl rim.
for sign in [-1,1]:
    for row,z0 in enumerate([1.544,1.526,1.508]):
        for col,y0 in enumerate(np.linspace(-.102,.025,18)):
            make_card(f'Base side {sign} {row}-{col}',(sign*.079,y0+(row%2)*.005,z0),(sign*.06,.20,-1),.025+float(rng.uniform(-.006,.004)),.008,.0012,.0004,col%3,sign*.12)
# Nape coverage cascades with the skull rather than radiating outward.
for row,z0 in enumerate([1.55,1.529,1.508]):
    for col,x0 in enumerate(np.linspace(-.053,.053,15)):
        make_card(f'Base back {row}-{col}',(x0,.065,z0),(x0*2,.1,-1),.028,.009,.0012,.0005,col%3)
# The visible top locks: asymmetric quiff with restrained, interlocking volume.
for row,y0 in enumerate([-.118,-.098,-.078,-.058,-.038,-.018]):
    for col,x0 in enumerate(np.linspace(-.047,.044,13)):
        x0+=.003*(row%2);length=.043+float(rng.uniform(-.007,.007));lift=(.010 if row<2 else .007)+float(rng.uniform(-.002,.002))
        edge=float(smooth(.025,.052,abs(x0)));lift*=(.72 if row<2 else .42)*(1-.75*edge)
        make_card(f'Shape swept lock {row}-{col}',(x0,y0,1.62),(.35+float(rng.uniform(-.15,.15)),1,-.14),length,(.007+float(rng.uniform(-.001,.001)))*(1-.35*edge),lift,.0015*(1-.75*edge),3+col%3,float(rng.uniform(-.28,.28)))
# Secondary side locks bridge the top and taper, removing a sharp cap edge.
for sign in [-1,1]:
    for row,z0 in enumerate([1.548,1.528]):
        for col,y0 in enumerate(np.linspace(-.108,.018,13)):
            make_card(f'Shape side {sign} {row}-{col}',(sign*.070,y0,z0),(sign*.10,.33,-1),.026,.006,.0025,.001,3+col%3,sign*.22)
# Fine broken fringe and sparse silhouette wisps, not a full fuzzy halo.
for col,x0 in enumerate(np.linspace(-.048,.050,17)):
    make_card(f'Fine frontal transition {col}',(x0,-.137,1.52),(.22,1,.22),.019+float(rng.uniform(-.004,.005)),.003,.004,.0002,7,float(rng.uniform(-.2,.2)))
for i in range(6):
    x0=float(rng.uniform(-.054,.052));y0=float(rng.uniform(-.075,.012));make_card(f'Silhouette wisp {i}',(x0,y0,1.61),(.45,1,-.12),.018,.0015,.0025,.0006,6,float(rng.uniform(-.45,.45)))

me=bpy.data.meshes.new('Layered card surface');me.from_pydata(verts,[],faces);me.update();obj=bpy.data.objects.new('HairGroom',me);bpy.context.collection.objects.link(obj);obj.parent=rig
for p in me.polygons:p.use_smooth=True
layer=me.uv_layers.new(name='UVMap')
for p in me.polygons:
    for li in p.loop_indices:layer.data[li].uv=uvs[me.loops[li].vertex_index]
me.materials.append(cardmat)
for g in cap.vertex_groups:obj.vertex_groups.new(name=g.name)
for i,(ids,bary) in enumerate(fits):
    weights={}
    for v,w in zip(ids,bary):
        for a in mesh.vertices[v].groups:weights[a.group]=weights.get(a.group,0)+a.weight*w
    keep=sorted(weights.items(),key=lambda p:-p[1])[:4];total=sum(v for _,v in keep)
    for group,w in keep:
        if w>0:obj.vertex_groups[group].add([i],w/total,'REPLACE')
mod=obj.modifiers.new('Original human rig','ARMATURE');mod.object=rig
obj.shape_key_add(name='Basis')
for key in mesh.shape_keys.key_blocks[1:]:
    k=obj.shape_key_add(name=key.name)
    for i,(ids,bary) in enumerate(fits):k.data[i].co=Vector(verts[i])+sum(((key.data[v].co-points[v])*w for v,w in zip(ids,bary)),Vector())
obj['original_groom']='Original layered crop; MIT; Blender authored guide curves, alpha atlas and baked cards';obj['card_count']=len(card_meta)
cap.hide_render=True;cap.hide_set(True);bpy.data.objects['HairStrands'].hide_render=True;bpy.data.objects['HairStrands'].hide_set(True)
# Retain editable guides, mesh, embedded textures and unmodified human context.
for im in [image,normalimage,rootimage]:im.pack()
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'original-short-groom.blend'),compress=True)
# Preserve an editable tint in .blend; export neutral atlas for app tint control.
for material in [cardmat,rootmat]:
    nodes=material.node_tree.nodes;links=material.node_tree.links;tint=nodes['Editable hair tint'];bs=nodes.get('Principled BSDF');texture=tint.inputs[1].links[0].from_socket;links.remove(bs.inputs['Base Color'].links[0]);links.new(texture,bs.inputs['Base Color'])
bpy.ops.object.select_all(action='DESELECT')
for o in [obj,rootcap,rig]:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.gltf(filepath=str(OUT/'hair-cards.glb'),export_format='GLB',use_selection=True,export_animations=False,export_morph=True,export_morph_normal=True,export_materials='EXPORT',export_extras=True)
# Use explicit glTF cutout material mode, independent of Blender UI naming.
import struct
glbpath=OUT/'hair-cards.glb';raw=glbpath.read_bytes();jsize=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+jsize]);binary=raw[20+jsize:]
for material in doc['materials']:
    material['alphaMode']='MASK';material['alphaCutoff']=.38;material['doubleSided']=True
encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);glbpath.write_bytes(struct.pack('<III',0x46546c67,2,20+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+binary)
manifest={'version':1,'license':'MIT original groom over retained CC0 scalp','seed':141126,'cards':len(card_meta),'vertices':len(verts),'triangles':len(faces)*2,'editableGuides':len(guides.objects),'shapeKeys':len(obj.data.shape_keys.key_blocks)-1,'references':['https://marmoset.co/posts/real-time-character-design-creation-and-presentation-breakdown/','https://marizatorska.artstation.com/blog/vq7Z/create-the-hair-cap-using-maya-and-marmoset-process-video'],'edgeRevision':'Guides stop inside scalp boundary; widths narrow near perimeter; tips settle to scalp rather than projecting/folding beyond it.','design':'Short asymmetric swept crop. Close coverage, staggered volume locks and sparse breakup. Original strand atlas; no purchased or downloaded hair assets.','guideLayout':card_meta,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.suffix in ['.png','.glb','.blend']}}
(OUT/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n');print('HAIR CARDS',json.dumps({k:manifest[k] for k in ['cards','vertices','triangles','editableGuides','shapeKeys']}))
