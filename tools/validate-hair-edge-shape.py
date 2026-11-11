"""Check the actual Blender source's card-tip clearance and editability metadata."""
import bpy,json,pathlib,hashlib
from mathutils.bvhtree import BVHTree
ROOT=pathlib.Path(__file__).resolve().parents[1];path=ROOT/'assets/human/hair-cards/original-short-groom.blend';before=hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(path));cap=bpy.data.objects['HairCrop'];cap.data.calc_loop_triangles();bvh=BVHTree.FromPolygons([v.co for v in cap.data.vertices],[tuple(t.vertices) for t in cap.data.loop_triangles],all_triangles=True)
mesh=bpy.data.objects['HairGroom'].data;guides=bpy.data.collections['EDITABLE Hair Guide Curves'];p=json.loads((ROOT/'assets/human/hair-cards/provenance.json').read_text());assert len(mesh.vertices)==len(guides.objects)*33
ends=[mesh.vertices[i*33+j].co.copy() for i in range(len(guides.objects)) for j in [30,31,32]]
def check_tips(points):
    distances=[bvh.find_nearest(v)[3] for v in points]
    assert max(distances)<.0015,'A card tip floats farther than 1.5 mm off its scalp'
    return max(distances)
maximum=check_tips(ends);broken=[v.copy() for v in ends];broken[0].z+=.03
try:check_tips(broken)
except AssertionError:negative=True
else:raise AssertionError('Floating-tip negative control was not rejected')
assert len(mesh.shape_keys.key_blocks)==29;assert all('card_width' in g and 'atlas_tile' in g for g in guides.objects);assert hashlib.sha256(path.read_bytes()).hexdigest()==before
result={'passed':True,'cards':len(guides.objects),'vertices':len(mesh.vertices),'maxTipDistanceMeters':maximum,'tipLimitMeters':.0015,'boundaryTrimmedGuides':sum(g.get('trimmedAtBoundary',False) for g in p['guideLayout']),'negativeFloatingTipRejected':negative,'identityKeys':28,'sourceUnchanged':True};(ROOT/'artifacts/hair-edge-shape.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
