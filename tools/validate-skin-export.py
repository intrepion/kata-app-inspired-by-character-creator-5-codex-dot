"""Verify the actual browser-exported skin GLBs, Blender material and editable rig.
Blender -b --python-exit-code 1 --python tools/validate-skin-export.py
"""
import importlib.util,json,pathlib,hashlib
import bpy,numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('expression',ROOT/'tools/validate-expression-export.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
base,GLB,require=ex.base,ex.GLB,ex.require
capture=json.loads((ROOT/'artifacts/skin-export-report.json').read_text());require(capture['passed'] and capture['exportPassed'],'Failed browser run')
source=GLB(ROOT/'assets/human/foundation.glb'); report={'passed':False,'structure':[],'sourceHashesBefore':base.source_hashes()}
for item in capture['exports']:
    doc=GLB(ROOT/'artifacts'/item['capture']['name']);require(doc.sha==item['capture']['sha256'],'Browser capture hash mismatch')
    report['structure'].append(ex.validate(doc,source,item['project']))
    if item['mode']=='regional':
        mat=next(m for m in doc.g['materials'] if m['name']=='Skin');require('not exported' in mat['extras']['skinTransferLimit'],'Missing shader transfer caveat')
        require(not any(k in mat.get('extensions',{}) for k in ['KHR_materials_transmission','KHR_materials_volume']),'False scattering substitute')
        require(mat['normalTexture']['scale']==.55,'Normal strength changed')
    if item['capture']['name']=='skin-expression.glb':chosen=doc
report['blender']=base.blender_checks(chosen,ROOT/'artifacts/skin-editable.blend')
skin=bpy.data.materials['Skin'];bs=next(n for n in skin.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
require(bs.inputs['Subsurface Weight'].default_value==0 and not bs.inputs['Subsurface Weight'].is_linked,'Unexpected imported SSS')
require(bs.inputs['Transmission Weight'].default_value==0,'Unexpected imported transmission')
report['blender']['subsurfaceWeight']=float(bs.inputs['Subsurface Weight'].default_value);report['blender']['transmissionWeight']=float(bs.inputs['Transmission Weight'].default_value)
# Find textures by their glTF image name and compare visible data to authored PNGs.
texture_results={}
for filename,channel in [('skin-color.png',None),('skin-normal.png',None),('skin-roughness.png',1)]:
    def upstream_images(socket,seen=None):
        seen=set() if seen is None else seen; found=[]
        for link in socket.links:
            node=link.from_node
            if node.name in seen:continue
            seen.add(node.name)
            if node.type=='TEX_IMAGE':found.append(node.image)
            else:
                for inp in node.inputs:found.extend(upstream_images(inp,seen))
        return found
    socket=bs.inputs['Base Color' if filename=='skin-color.png' else 'Normal' if filename=='skin-normal.png' else 'Roughness']
    matches=upstream_images(socket)
    require(len(matches)==1,'Ambiguous imported image '+filename+': '+str([(n.name,n.image.name) for n in skin.node_tree.nodes if n.type=='TEX_IMAGE']))
    actual=matches[0];expected=bpy.data.images.load(str(ROOT/'assets/human/skin'/filename),check_existing=False);expected.colorspace_settings.name=actual.colorspace_settings.name
    require(tuple(actual.size)==tuple(expected.size)==(2048,2048),'Texture resolution changed')
    a=np.array(actual.pixels[:],np.float32).reshape(-1,4);b=np.array(expected.pixels[:],np.float32).reshape(-1,4)
    delta=np.abs(a[:,channel]-b[:,channel]) if channel is not None else np.abs(a-b)
    maximum=float(delta.max());require(maximum<2/255,'Exported skin pixels changed '+filename+': '+str(maximum))
    texture_results[filename]={'maximumPixelDifference':maximum,'colorSpace':actual.colorspace_settings.name,'resolution':[2048,2048]};bpy.data.images.remove(expected)
report['blender']['skinTexturePixels']=texture_results
# Prove expression, brow, blink and gaze targets still edit evaluated geometry.
def obj(material):return next(o for o in bpy.data.objects if o.type=='MESH' and any(m and m.name==material for m in o.data.materials))
def points(ob):
    bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());return [ev.matrix_world@v.co for v in ev.data.vertices]
edits={}
for material,key in [('Skin','Smile'),('Skin','Frown'),('Skin','BrowRaise'),('Brows','BrowFurrow'),('Skin','BlinkLeft'),('Iris','GazeRight')]:
    ob=obj(material);shape=ob.data.shape_keys.key_blocks[key];old=shape.value;before=points(ob);shape.value=0 if old>.5 else 1;after=points(ob);shape.value=old;delta=max((a-b).length for a,b in zip(before,after));require(delta>.0001,'Uneditable target '+key);edits[material+'/'+key]=delta
report['blender']['editableTargetDeltaMeters']=edits;report['sourceHashesAfter']=base.source_hashes();require(report['sourceHashesBefore']==report['sourceHashesAfter'],'Source was modified')
report['passed']=True;report['limit']='Only PBR textures transfer. Browser thin-tissue backlight is not present in Blender; imported Principled Subsurface and Transmission Weight remain zero.'
(ROOT/'artifacts/skin-export-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
