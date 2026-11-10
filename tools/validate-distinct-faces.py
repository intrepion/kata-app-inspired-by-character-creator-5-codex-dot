"""Numerical source/GLB face-shape roundtrip for all fitted face parts.
No browser or GUI file opening. Optional output path follows --.
"""
import bpy, pathlib, json, sys
from mathutils.kdtree import KDTree
from mathutils import Vector
ROOT=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'assets/human/manifest.json').read_text())
new_names=[n for c in manifest['distinctFaces']['controls'] for n in manifest['morphs'][c]]
names=['HumanBody','Eyes','Iris','Cornea','Brows','Lashes','HairCrop','HairStrands']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/source/foundation.blend'))
expected={}
for name in names:
 ob=bpy.data.objects[name];keys=ob.data.shape_keys.key_blocks
 assert all(k.value==0 for k in keys),('non-neutral source',name)
 expected[name]={'basis':[v.co.copy() for v in keys[0].data], 'shapes':{key:[v.co.copy() for v in keys[key].data] for key in new_names}}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/human/foundation.glb'))
report={'passed':True,'toleranceMeters':.000002,'meshes':{}}
for name in names:
 ob=next(o for o in bpy.data.objects if o.type=='MESH' and o.data.name==('high-poly' if name=='Eyes' else name));keys=ob.data.shape_keys.key_blocks;source=expected[name]
 tree=KDTree(len(source['basis']))
 for i,co in enumerate(source['basis']):tree.insert(co,i)
 tree.balance();matches=[tree.find(v.co)[1] for v in keys[0].data]
 err=max((v.co-source['basis'][i]).length for v,i in zip(keys[0].data,matches))
 maximum=max((v.co-source['shapes'][key][i]).length for key in new_names for v,i in zip(keys[key].data,matches))
 report['meshes'][name]={'baseMaxErrorMeters':err,'faceShapeMaxErrorMeters':maximum,'editableNewTargets':len(new_names)}
 assert err<report['toleranceMeters'] and maximum<report['toleranceMeters'],(name,err,maximum)
print(json.dumps(report,indent=2))
if '--' in sys.argv:pathlib.Path(sys.argv[sys.argv.index('--')+1]).write_text(json.dumps(report,indent=2)+'\n')
