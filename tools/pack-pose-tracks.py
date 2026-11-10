"""Embed static pose corrective weight tracks in the standalone GLB."""
import json,struct

def pack_pose_tracks(path,correctives):
    raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0]
    gltf=json.loads(raw[20:20+length]);binary=bytearray(raw[28+length:])
    def accessor(values,count,kind):
        while len(binary)%4:binary.append(0)
        offset=len(binary);binary.extend(struct.pack('<'+'f'*len(values),*values))
        view=len(gltf['bufferViews']);gltf['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(values)*4})
        index=len(gltf['accessors']);gltf['accessors'].append({'bufferView':view,'componentType':5126,'count':count,'type':kind})
        return index
    time=accessor([0,1/24],2,'SCALAR');gltf['accessors'][time].update(min=[0],max=[1/24])
    for animation in gltf.get('animations',[]):
        target_name=correctives.get(animation['name'])
        for node_index,node in enumerate(gltf['nodes']):
            if 'mesh' not in node:continue
            mesh=gltf['meshes'][node['mesh']];names=mesh.get('extras',{}).get('targetNames',[])
            if not any(name in names for name in correctives.values()):continue
            weights=[int(name==target_name) for name in names]
            output=accessor(weights*2,len(weights)*2,'SCALAR')
            sampler=len(animation['samplers']);animation['samplers'].append({'input':time,'output':output,'interpolation':'STEP'})
            animation['channels'].append({'sampler':sampler,'target':{'node':node_index,'path':'weights'}})
    gltf['buffers'][0]['byteLength']=len(binary)
    data=json.dumps(gltf,separators=(',',':')).encode();data+=b' '*((-len(data))%4);binary+=b'\0'*((-len(binary))%4)
    path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(data)+len(binary))+struct.pack('<II',len(data),0x4e4f534a)+data+struct.pack('<II',len(binary),0x004e4942)+binary)
