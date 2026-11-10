import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';import {createHash} from 'node:crypto';
// Hashes were decoded from the approved waist/pose baseline d8a302a, not from
// the portrait build. Sparse and interleaved accessors compare actual values.
test('portrait preserves all 93 approved body, garment, weight and morph buffers',async()=>{
  const baseline=JSON.parse(await readFile(new URL('./foundation-preserved.json',import.meta.url))),file=await readFile(new URL('../assets/human/foundation.glb',import.meta.url));
  const length=file.readUInt32LE(12),gltf=JSON.parse(file.subarray(20,20+length)),binary=file.subarray(28+length),actual={};
  function hash(index){const a=gltf.accessors[index],components={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16}[a.type],width={5121:1,5123:2,5125:4,5126:4}[a.componentType],size=components*width,out=Buffer.alloc(a.count*size);
    if(a.bufferView!==undefined){const view=gltf.bufferViews[a.bufferView],offset=(view.byteOffset||0)+(a.byteOffset||0),stride=view.byteStride||size;for(let i=0;i<a.count;i++)binary.copy(out,i*size,offset+i*stride,offset+i*stride+size);}
    if(a.sparse){const s=a.sparse,indices=gltf.bufferViews[s.indices.bufferView],values=gltf.bufferViews[s.values.bufferView],io=(indices.byteOffset||0)+(s.indices.byteOffset||0),vo=(values.byteOffset||0)+(s.values.byteOffset||0),iw={5121:1,5123:2,5125:4}[s.indices.componentType];for(let i=0;i<s.count;i++){const index=binary.readUIntLE(io+i*iw,iw);binary.copy(out,index*size,vo+i*size,vo+(i+1)*size);}}
    return createHash('sha256').update(out).digest('hex');}
  for(const mesh of gltf.meshes.filter(m=>['HumanBody','Outfit','Pants'].includes(m.name)))mesh.primitives.forEach((p,i)=>{for(const attr of ['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'])actual[`${mesh.name}/${i}/${attr}`]=hash(p.attributes[attr]);p.targets.forEach((target,j)=>{for(const attr in target)actual[`${mesh.name}/${i}/${mesh.extras.targetNames[j]}/${attr}`]=hash(target[attr]);});});
  assert.equal(Object.keys(baseline.buffers).length,93);assert.deepEqual(actual,baseline.buffers);
});
