"""Rebuild the skinned card mesh from edited Blender guide curves.
In Blender's Python console:
  exec(compile(open('/absolute/path/tools/rebake-hair-cards.py').read(), 'rebake-hair-cards.py', 'exec'))
This changes the open scene only. Save/export from Blender after reviewing it.
The original numeric authoring script is not rerun, so hand edits are preserved.
"""
import bpy, math
from mathutils import Vector
from mathutils.geometry import interpolate_bezier, barycentric_transform
from mathutils.bvhtree import BVHTree

def rebake():
    cap=bpy.data.objects['HairCrop'];old=bpy.data.objects['HairGroom'];source=cap.data;source.calc_loop_triangles()
    pts=[v.co.copy() for v in source.vertices];tri=[tuple(t.vertices) for t in source.loop_triangles];bvh=BVHTree.FromPolygons(pts,tri,all_triangles=True)
    vertices=[];faces=[];uv=[];fits=[]
    for guide in bpy.data.collections['EDITABLE Hair Guide Curves'].objects:
        control=guide.data.splines[0].bezier_points;path=[];width=[];tilts=[]
        for a,b in zip(control,control[1:]):
            samples=interpolate_bezier(a.co,a.handle_right,b.handle_left,b.co,17)
            for j,p in enumerate(samples[:-1]):
                f=j/16;path.append(guide.matrix_world@p);width.append((a.radius*(1-f)+b.radius*f)*guide['card_width']);tilts.append(a.tilt*(1-f)+b.tilt*f)
        path.append(guide.matrix_world@control[-1].co);width.append(control[-1].radius*guide['card_width']);tilts.append(control[-1].tilt)
        lengths=[0.]
        for a,b in zip(path,path[1:]):lengths.append(lengths[-1]+(b-a).length)
        first=len(vertices);tile=guide['atlas_tile'];section=[]
        for j in range(11):
            d=lengths[-1]*j/10;k=next((k for k in range(len(lengths)-1) if lengths[k+1]>=d),len(lengths)-2);f=(d-lengths[k])/(lengths[k+1]-lengths[k] or 1)
            center=path[k].lerp(path[k+1],f);tangent=(path[k+1]-path[k]).normalized();nearest,n,idx,_=bvh.find_nearest(center);ids=tri[idx]
            bary=barycentric_transform(nearest,*(pts[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
            normal=sum((source.vertices[i].normal*w for i,w in zip(ids,bary)),Vector()).normalized();across=tangent.cross(normal).normalized();tilt=tilts[k]*(1-f)+tilts[k+1]*f;across=(across*math.cos(tilt)+normal*math.sin(tilt)).normalized();w=width[k]*(1-f)+width[k+1]*f
            for c in range(3):
                s=c-1;vertices.append(center+across*(s*w/2)+normal*((1-s*s)*guide['card_width']*.11));fits.append((ids,bary));uv.append(((tile+.025+c*.475)/8,j/10))
            if j:
                for c in range(2):a=first+(j-1)*3+c;b=a+3;faces.append((a,a+1,b+1,b))
    me=bpy.data.meshes.new('Rebaked editable guide cards');me.from_pydata(vertices,[],faces);me.update();materials=list(old.data.materials);old.data=me
    for m in materials:me.materials.append(m)
    layer=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        p.use_smooth=True
        for li in p.loop_indices:layer.data[li].uv=uv[me.loops[li].vertex_index]
    old.vertex_groups.clear()
    for group in cap.vertex_groups:old.vertex_groups.new(name=group.name)
    for i,(ids,bary) in enumerate(fits):
        weights={}
        for v,w in zip(ids,bary):
            for a in source.vertices[v].groups:weights[a.group]=weights.get(a.group,0)+a.weight*w
        keep=sorted(weights.items(),key=lambda p:-p[1])[:4];total=sum(w for _,w in keep)
        for group,w in keep:
            if w>0:old.vertex_groups[group].add([i],w/total,'REPLACE')
    old.shape_key_add(name='Basis')
    for key in source.shape_keys.key_blocks[1:]:
        new=old.shape_key_add(name=key.name)
        for i,(ids,bary) in enumerate(fits):new.data[i].co=vertices[i]+sum(((key.data[v].co-pts[v])*w for v,w in zip(ids,bary)),Vector())
    old['last_bake']='Edited guide curves; original identity morphs and weights transferred';return old

if __name__=='__main__':
    result=rebake();print('Rebaked',len(result.data.vertices),'vertices from editable curves; review before saving.')
