import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {portraitSnapshot,assertPortraitPreserved} from './portrait-neutral-snapshot.mjs';
const baseline=JSON.parse(await readFile(new URL('./portrait-neutral-preserved.json',import.meta.url)));
const current=portraitSnapshot(await readFile(new URL('../assets/human/foundation.glb',import.meta.url)));
test('distinct faces preserve the approved portrait neutral geometry, old morphs, materials and embedded images',()=>{
  assert.equal(baseline.commit,'3a5fb77');
  assert.equal(Object.keys(baseline.snapshot.meshes).length,10);
  assert.equal(Object.keys(baseline.snapshot.images).length,8);
  assertPortraitPreserved(current,baseline.snapshot);
});
test('bundled new shape keys default to neutral zero weights',()=>{
  for (const [name,mesh] of Object.entries(current.meshes)) for (const [target,weight] of Object.entries(mesh.weights)) {
    if (!Object.hasOwn(baseline.snapshot.meshes[name].weights,target)) assert.equal(weight,0,`${name}/${target} neutral weight`);
  }
});
test('preservation guard rejects changed geometry, old morphs, weights, material and image data',()=>{
  const changes=[
    s=>s.meshes.Brows.primitives[0].attributes.POSITION.sha256='changed',
    s=>s.meshes.Brows.primitives[0].targets.EyesLarge.POSITION.sha256='changed',
    s=>s.meshes.Brows.weights.EyesLarge=1,
    s=>s.materials.Cornea.alphaMode='OPAQUE',
    s=>s.images.portrait_iris.sha256='changed',
    s=>delete s.meshes.Iris
  ];
  for (const change of changes) {
    const broken=structuredClone(baseline.snapshot);change(broken);
    assert.throws(()=>assertPortraitPreserved(broken,baseline.snapshot));
  }
});
test('preservation guard permits new zero-weight targets but rejects non-neutral additions',()=>{
  const extended=structuredClone(baseline.snapshot);
  extended.meshes.Iris.weights.NewFace=0;
  extended.meshes.Iris.primitives[0].targets.NewFace={POSITION:{sha256:'new'}};
  assert.doesNotThrow(()=>assertPortraitPreserved(extended,baseline.snapshot));
  extended.meshes.Iris.weights.NewFace=1;
  assert.throws(()=>assertPortraitPreserved(extended,baseline.snapshot));
});
