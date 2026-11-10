"""Original deterministic region-aware skin maps. No downloads or source mesh edits.
Run Blender -b --python-exit-code 1 --python tools/build-skin.py.
The CC0 MakeHuman diffuse is retained as the base. Original detail is MIT.
"""
import bpy, pathlib, json, hashlib
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'assets/human/skin'; OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/source/foundation.blend'))
body=bpy.data.objects['HumanBody']; mesh=body.data; mesh.calc_loop_triangles(); n=2048
xyz=np.zeros((n,n,3),np.float32); valid=np.zeros((n,n),bool)
# Rasterize the real UV chart so masks follow anatomy, not guessed atlas circles.
for tri in mesh.loop_triangles:
    p=np.array([mesh.vertices[i].co[:] for i in tri.vertices])
    if p[:,2].max()<1.28: continue
    uv=np.array([mesh.uv_layers.active.data[i].uv[:] for i in tri.loops])*(n-1)
    lo=np.maximum(np.floor(uv.min(0)).astype(int),0); hi=np.minimum(np.ceil(uv.max(0)).astype(int),n-1)
    if np.any(hi<lo): continue
    yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]; a,b,c=uv
    den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-10:continue
    w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
    w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den; w2=1-w0-w1
    inside=(w0>=-1e-5)&(w1>=-1e-5)&(w2>=-1e-5)
    region=xyz[lo[1]:hi[1]+1,lo[0]:hi[0]+1]; region[inside]=(w0[...,None]*p[0]+w1[...,None]*p[1]+w2[...,None]*p[2])[inside]
    valid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=inside
# Dilate coordinates into UV gutters to avoid black seams with bilinear/mipmap filtering.
for _ in range(12):
    accum=np.zeros_like(xyz); count=np.zeros((n,n),np.float32)
    for axis,step in [(0,1),(0,-1),(1,1),(1,-1)]:
        v=np.roll(valid,step,axis); accum+=np.roll(xyz,step,axis)*v[...,None];count+=v
    new=(~valid)&(count>0);xyz[new]=accum[new]/count[new,None];valid|=new
x,y,z=xyz.transpose(2,0,1); ax=np.abs(x)
def smooth(a,b,v):
    t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
def spot(cx,cy,cz,sx,sy,sz):return np.exp(-.5*((ax-cx)/sx)**2-.5*((y-cy)/sy)**2-.5*((z-cz)/sz)**2)*valid
face=smooth(1.30,1.38,z)*(1-smooth(-.04,.025,y))*valid
cheek=spot(.046,-.112,1.427,.021,.035,.022)
nose=spot(0,-.154,1.448,.016,.033,.022)
forehead=spot(.015,-.103,1.504,.045,.04,.035)
lips=spot(0,-.137,1.389,.025,.019,.007)
eye=spot(.028,-.121,1.450,.019,.019,.009)
ear=spot(.074,-.018,1.437,.015,.036,.031)
chin=spot(0,-.105,1.365,.036,.035,.019)
rng=np.random.default_rng(701126)
def blur(a,passes):
    for _ in range(passes): a=(a+np.roll(a,1,0)+np.roll(a,-1,0)+np.roll(a,1,1)+np.roll(a,-1,1))/5
    return a
# Stochastic depressions rather than a repeated dot grid. Region-dependent pore size/strength.
seeds=np.maximum(rng.random((n,n)).astype(np.float32)-.94,0)/.06
pores=blur(seeds,1); fine=blur(rng.random((n,n)).astype(np.float32)-.5,1)
broad=blur(rng.random((n,n)).astype(np.float32)-.5,18); broad/=max(float(broad.std()),1e-8)
height=(-pores*.31+fine*.024)*(face*(.4+.65*cheek+.8*nose+.35*forehead)*(1-.78*lips)*(1-.7*eye))
# Original body normal retained outside the portrait region.
old=bpy.data.images['portrait_skin_normal']; oldarr=np.array(old.pixels[:],np.float32).reshape(1024,1024,4)
normal=np.repeat(np.repeat(oldarr,2,0),2,1).copy(); dx=np.roll(height,-1,1)-np.roll(height,1,1); dy=np.roll(height,-1,0)-np.roll(height,1,0)
normal[:,:,:3]=normal[:,:,:3]*(1-face[...,None])+np.dstack([.5-dx*1.8,.5-dy*1.8,np.ones_like(dx)])*face[...,None]
# glTF normal map uses OpenGL +Y convention; Blender and Three agree.
base=np.array(bpy.data.images['skin.png'].pixels[:],np.float32).reshape(n,n,4)
color=base.copy(); blush=np.clip(.65*cheek+.4*nose+.7*ear,0,1)
color[:,:,:3]*=np.dstack([1-.018*face+.025*blush,1-.038*face-.035*blush,1-.025*face-.025*blush])
color[:,:,:3]*=(1+(broad*.0035)*face)[...,None]
color[:,:,0]*=1-.025*eye;color[:,:,2]*=1+.012*eye
rough=np.clip(.60+.035*face-.18*nose-.10*forehead+.06*cheek-.16*lips+.035*chin+fine*.065*face,.30,.73)
# Single-channel thin-tissue mask: ears strongest, nose/face modest, body zero.
thin=np.clip(.72*ear+.17*nose+.025*face,0,.82)
def save(name,a,color_space=False):
    if a.ndim==2:a=np.dstack([a,a,a,np.ones_like(a)])
    im=bpy.data.images.new(name,width=n,height=n,alpha=True); im.colorspace_settings.name='sRGB' if color_space else 'Non-Color'
    im.pixels.foreach_set(np.clip(a,0,1).astype(np.float32).ravel());im.filepath_raw=str(OUT/(name+'.png'));im.file_format='PNG';im.save();bpy.data.images.remove(im)
for name,a,cs in [('skin-color',color,True),('skin-normal',normal,False),('skin-roughness',rough,False),('skin-thin',thin,False)]:save(name,a,cs)
# Remove incidental profiles from linear data maps (raw pixels unchanged).
import struct
for file in OUT.glob('*.png'):
    if file.name=='skin-color.png':continue
    raw=file.read_bytes(); out=raw[:8]; offset=8
    while offset<len(raw):
        size=struct.unpack_from('>I',raw,offset)[0]; tag=raw[offset+4:offset+8]; chunk=raw[offset:offset+12+size];offset+=12+size
        if tag not in [b'iCCP',b'sRGB',b'gAMA',b'cHRM']:out+=chunk
    file.write_bytes(out)
report={'version':1,'resolution':[n,n],'seed':701126,'source':'Existing CC0 MakeHuman skin.png; original MIT procedural region details','sourceGLBSha256':hashlib.sha256((ROOT/'assets/human/foundation.glb').read_bytes()).hexdigest(),'portable':['baseColor','normal','roughness'],'webOnly':['thin-tissue backlight approximation; not volumetric SSS'],'files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(OUT.glob('*.png'))},'regions':{k:{'pixels':int((v>.3).sum()),'meanRoughness':float(rough[v>.3].mean())} for k,v in [('nose',nose),('cheeks',cheek),('forehead',forehead),('lips',lips),('ears',ear)]}}
(OUT/'provenance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
