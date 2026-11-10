import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

// Compare decoded accessor bytes, not packing offsets or sparse encoding.
export function portraitSnapshot(file) {
  assert.equal(file.readUInt32LE(0), 0x46546c67);
  assert.equal(file.readUInt32LE(4), 2);
  assert.equal(file.readUInt32LE(8), file.length);
  const length = file.readUInt32LE(12);
  const gltf = JSON.parse(file.subarray(20, 20 + length));
  const binary = file.subarray(28 + length);
  function accessor(index) {
    const a = gltf.accessors[index];
    const components = {SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16}[a.type];
    const width = {5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[a.componentType];
    assert.ok(components && width, 'Supported accessor layout');
    const size = components * width, decoded = Buffer.alloc(a.count * size);
    if (a.bufferView !== undefined) {
      const view = gltf.bufferViews[a.bufferView];
      const offset = (view.byteOffset || 0) + (a.byteOffset || 0), stride = view.byteStride || size;
      for (let i=0;i<a.count;i++) binary.copy(decoded,i*size,offset+i*stride,offset+i*stride+size);
    }
    if (a.sparse) {
      const s=a.sparse, iv=gltf.bufferViews[s.indices.bufferView], vv=gltf.bufferViews[s.values.bufferView];
      const iw={5121:1,5123:2,5125:4}[s.indices.componentType];
      for (let i=0;i<s.count;i++) {
        const at=binary.readUIntLE((iv.byteOffset||0)+(s.indices.byteOffset||0)+i*iw,iw);
        const from=(vv.byteOffset||0)+(s.values.byteOffset||0)+i*size;
        assert.ok(at<a.count, 'Sparse index in bounds');
        binary.copy(decoded,at*size,from,from+size);
      }
    }
    return {type:a.type,componentType:a.componentType,count:a.count,normalized:a.normalized||false,sha256:hash(decoded)};
  }
  function image(index) {
    const {bufferView,...metadata}=gltf.images[index];
    assert.notEqual(bufferView,undefined,'Image must remain embedded');
    const view=gltf.bufferViews[bufferView], offset=view.byteOffset||0;
    return {...metadata,bytes:view.byteLength,sha256:hash(binary.subarray(offset,offset+view.byteLength))};
  }
  function texture(index) {
    const {source,sampler,...rest}=gltf.textures[index];
    return {...rest,image:image(source),sampler:sampler===undefined?null:gltf.samplers[sampler]};
  }
  // Material texture indices may shift when new morph buffers are exported.
  function material(value,key='') {
    if (Array.isArray(value)) return value.map(v=>material(v));
    if (!value || typeof value!=='object') return value;
    return Object.fromEntries(Object.entries(value).map(([k,v])=>[
      k, k==='index' && /Texture$/.test(key) ? texture(v) : material(v,k)
    ]));
  }
  const result={meshes:{},materials:{},images:{}};
  for (const m of gltf.meshes) {
    assert.ok(m.name && !result.meshes[m.name], 'Unique mesh names');
    const names=m.extras?.targetNames||[];
    result.meshes[m.name]={
      weights:Object.fromEntries(names.map((name,i)=>[name,m.weights?.[i]??0])),
      primitives:m.primitives.map(p=>({
        mode:p.mode??4,
        material:p.material===undefined?null:gltf.materials[p.material].name,
        indices:p.indices===undefined?null:accessor(p.indices),
        attributes:Object.fromEntries(Object.entries(p.attributes).map(([key,index])=>[key,accessor(index)])),
        targets:Object.fromEntries((p.targets||[]).map((t,i)=>[names[i],Object.fromEntries(Object.entries(t).map(([key,index])=>[key,accessor(index)]))]))
      }))
    };
  }
  for (const m of gltf.materials) result.materials[m.name]=material(m);
  gltf.images.forEach((im,i)=>{assert.ok(im.name&&!result.images[im.name],'Unique image names');result.images[im.name]=image(i);});
  return result;
}

export function assertPortraitPreserved(actual,baseline) {
  assert.deepEqual(Object.keys(actual.meshes).sort(),Object.keys(baseline.meshes).sort(),'Neutral mesh inventory');
  assert.deepEqual(actual.materials,baseline.materials,'Material definitions and resolved textures');
  assert.deepEqual(actual.images,baseline.images,'Embedded image bytes');
  for (const [name,mesh] of Object.entries(baseline.meshes)) {
    const current=actual.meshes[name];
    assert.equal(current.primitives.length,mesh.primitives.length,name+' primitive count');
    for (const [target,weight] of Object.entries(mesh.weights)) assert.equal(current.weights[target],weight,`${name}/${target} original weight`);
    for (const [target,weight] of Object.entries(current.weights)) assert.equal(weight,mesh.weights[target]??0,`${name}/${target} neutral weight`);
    mesh.primitives.forEach((p,i)=>{
      const {targets,...neutral}=p, {targets:currentTargets,...currentNeutral}=current.primitives[i];
      assert.deepEqual(currentNeutral,neutral,`${name}/${i} neutral attributes, indices and material`);
      for (const [target,attributes] of Object.entries(targets)) assert.deepEqual(currentTargets[target],attributes,`${name}/${i}/${target} original morph`);
    });
  }
}
