import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as T from '../vendor/three.module.min.js';
import {GLTFLoader} from '../vendor/loaders/GLTFLoader.js';
import {GLTFExporter} from '../vendor/exporters/GLTFExporter.js';
import {bindHairCardMesh,createHairCardGroom,HAIR_CARD_LIMIT} from '../src/hair-card-groom.js';

const close=(a,b,label='position')=>assert.ok(a.distanceTo(b)<2e-6,`${label}: ${a.toArray()} != ${b.toArray()}`);
const point=(mesh,i)=>mesh.getVertexPosition(i,new T.Vector3()).applyMatrix4(mesh.matrixWorld);
function fixture(){
  const human=new T.Group(),root=new T.Bone(),head=new T.Bone();root.name='Root';head.name='head';head.position.y=1;root.add(head);human.add(root);
  const geometry=new T.BufferGeometry();
  geometry.setAttribute('position',new T.Float32BufferAttribute([0,1,.1,.2,1,.1,0,1.2,.1],3));
  geometry.setAttribute('normal',new T.Float32BufferAttribute([0,0,1,0,0,1,0,0,1],3));
  geometry.setAttribute('uv',new T.Float32BufferAttribute([0,0,1,0,0,1],2));
  geometry.setAttribute('skinIndex',new T.Uint16BufferAttribute([0,1,0,0,0,1,0,0,0,1,0,0],4));
  geometry.setAttribute('skinWeight',new T.Float32BufferAttribute([.25,.75,0,0,.25,.75,0,0,.25,.75,0,0],4));geometry.setIndex([0,1,2]);geometry.morphTargetsRelative=true;
  geometry.morphAttributes.position=['HeadWide','HeadLong'].map((name,index)=>{const a=new T.Float32BufferAttribute(index?[0,.02,0,0,.03,0,0,.04,0]:[.01,0,0,.02,0,0,.03,0,0],3);a.name=name;return a;});
  geometry.morphAttributes.normal=['HeadWide','HeadLong'].map(name=>{const a=new T.Float32BufferAttribute(new Float32Array(9),3);a.name=name;return a;});
  const cap=new T.SkinnedMesh(geometry,new T.MeshStandardMaterial({name:'Hair'}));cap.name='HairCrop';cap.position.x=.04;cap.rotation.y=.12;human.add(cap);
  human.updateMatrixWorld(true);cap.bind(new T.Skeleton([root,head]));
  const strands=cap.clone();strands.geometry=geometry.clone();strands.material=new T.MeshStandardMaterial({name:'HairStrands'});strands.name='HairStrands';human.add(strands);human.updateMatrixWorld(true);
  const scene=new T.Group(),assetRoot=root.clone();scene.add(assetRoot);scene.updateMatrixWorld(true);
  const assetBones=[assetRoot.children[0],assetRoot],assetSkeleton=new T.Skeleton(assetBones,[cap.skeleton.boneInverses[1].clone(),cap.skeleton.boneInverses[0].clone()]);
  const transform=new T.Matrix4().makeRotationX(.27).setPosition(.3,-.4,.2),inverse=transform.clone().invert();
  for(const name of ['HairGroom','HairCardRoot']){
    const g=geometry.clone();g.applyMatrix4(inverse);
    for(const kind of ['position','normal'])g.morphAttributes[kind].reverse();
    for(const a of g.morphAttributes.position){const v=new T.Vector3();for(let i=0;i<a.count;i++){v.fromBufferAttribute(a,i).applyMatrix3(new T.Matrix3().setFromMatrix4(inverse));a.setXYZ(i,v.x,v.y,v.z);}}
    g.setAttribute('skinIndex',new T.Uint16BufferAttribute([1,0,0,0,1,0,0,0,1,0,0,0],4));
    const mesh=new T.SkinnedMesh(g,new T.MeshStandardMaterial({name,alphaTest:.38,side:T.DoubleSide}));mesh.name=name;mesh.bind(assetSkeleton,cap.bindMatrix.clone().multiply(transform));scene.add(mesh);
  }
  return{human,cap,strands,scene,root,head};
}

// Only texture decoding is replaced for Node. Meshes, skins, matrices, morphs,
// material extensions, and packed buffers use the actual bundled GLTFLoader.
async function asset(path){
  const loader=new GLTFLoader();loader.register(()=>({name:'NodeTextureFixture',loadTexture:async()=>new T.DataTexture(new Uint8Array([255,255,255,255]),1,1)}));
  const bytes=readFileSync(new URL(path,import.meta.url));
  return loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
}
const project={hair:'crop',hairColor:'#765432'};

test('bone names, nonidentity bind spaces, and reordered relative morphs transfer without changing inputs',()=>{
  const f=fixture(),authored=f.scene.getObjectByName('HairGroom'),before=authored.geometry.attributes.position.array.slice(),source=f.cap.geometry.attributes.position.array.slice();
  const mesh=bindHairCardMesh(authored,f.cap);f.cap.parent.add(mesh);
  assert.equal(mesh.skeleton,f.cap.skeleton);assert.deepEqual([...mesh.geometry.attributes.skinIndex.array],[0,1,1,1,0,1,1,1,0,1,1,1]);
  for(const name of ['HeadWide','HeadLong']){
    f.cap.morphTargetInfluences.fill(0);mesh.morphTargetInfluences.fill(0);
    f.cap.morphTargetInfluences[f.cap.morphTargetDictionary[name]]=.8;mesh.morphTargetInfluences[mesh.morphTargetDictionary[name]]=.8;
    for(const angle of [0,.4,-.3]){f.head.rotation.z=angle;f.human.position.set(.7,-.2,.9);f.human.rotation.y=.8;f.human.scale.setScalar(1.1);f.human.updateMatrixWorld(true);f.cap.skeleton.update();for(let i=0;i<3;i++)close(point(mesh,i),point(f.cap,i),name);}
  }
  assert.deepEqual(authored.geometry.attributes.position.array,before);assert.deepEqual(f.cap.geometry.attributes.position.array,source);
});

test('broken skeleton, identity targets, and weights fail instead of silently misbinding',()=>{
  {const f=fixture(),m=f.scene.getObjectByName('HairGroom');m.skeleton.bones[0].name='unknown';assert.throws(()=>bindHairCardMesh(m,f.cap),/unknown bone/);}
  {const f=fixture(),m=f.scene.getObjectByName('HairGroom');delete m.morphTargetDictionary.HeadWide;assert.throws(()=>bindHairCardMesh(m,f.cap),/missing identity target: HeadWide/);}
  {const f=fixture(),m=f.scene.getObjectByName('HairGroom');m.geometry.attributes.skinWeight.setX(0,2);assert.throws(()=>bindHairCardMesh(m,f.cap),/sum to one/);}
  {const f=fixture(),m=f.scene.getObjectByName('HairGroom');m.skeleton.boneInverses[0].elements[12]+=.5;assert.throws(()=>bindHairCardMesh(m,f.cap),/rest skeleton does not match/);}
});

test('default cards hide originals, preserve tint and named morphs, and support repeated baseline/bald switches',async()=>{
  const f=fixture(),originalGeometry=f.cap.geometry,originalMaterial=f.cap.material;
  let loads=0;const hair=await createHairCardGroom({human:f.human,loader:{loadAsync:async()=>{loads++;return{scene:f.scene};}}});
  assert.equal(loads,1);assert.equal(hair.stats.comparisonEnabled,false);assert.equal(hair.meshes.length,2);assert.ok(Number.isFinite(hair.stats.loadMilliseconds));
  f.cap.morphTargetInfluences[f.cap.morphTargetDictionary.HeadWide]=.73;hair.update(project);
  assert.equal(f.cap.visible,false);assert.equal(f.strands.visible,false);
  for(const mesh of hair.meshes){assert.equal(mesh.visible,true);assert.equal(mesh.morphTargetInfluences[mesh.morphTargetDictionary.HeadWide],.73);assert.equal(mesh.material.color.getHexString(),'765432');assert.equal(mesh.skeleton,f.cap.skeleton);}
  assert.equal(hair.mesh.castShadow,false);assert.equal(hair.mesh.receiveShadow,false);assert.equal(hair.meshes[1].castShadow,true);assert.equal(hair.meshes[1].receiveShadow,true);assert.match(hair.stats.previewLimit,/do not cast or receive studio shadows/);assert.equal(hair.mesh.material.anisotropy,.65);assert.equal(hair.mesh.material.alphaTest,.38);assert.equal(hair.mesh.material.alphaToCoverage,true);
  for(let i=0;i<3;i++)for(const mode of ['baseline','groom']){
    hair.setPreview(mode);assert.equal(f.cap.geometry,originalGeometry);assert.equal(f.cap.material,originalMaterial);
    for(const hairChoice of ['none','crop']){hair.update({...project,hair:hairChoice,hairColor:'#d4b477'});const enabled=hairChoice==='crop';assert.equal(f.cap.visible,enabled&&mode==='baseline');assert.equal(f.strands.visible,enabled&&mode==='baseline');assert.equal(hair.mesh.visible,enabled&&mode==='groom');assert.equal(hair.mesh.material.color.getHexString(),'d4b477');}
  }
  assert.throws(()=>hair.setPreview('procedural'),/compareHair:true/);assert.throws(()=>hair.setPreview('other'),/Unknown hair preview/);
  let skeletonDisposals=0;f.cap.skeleton.dispose=()=>skeletonDisposals++;hair.dispose();hair.dispose();assert.equal(skeletonDisposals,0);assert.equal(f.cap.geometry,originalGeometry);assert.equal(f.human.getObjectByName('HairGroom'),undefined);
});

test('authored physical roughness, specular, normal strength and zero anisotropy remain unchanged',async()=>{
  const f=fixture(),authored=f.scene.getObjectByName('HairGroom');authored.material=new T.MeshPhysicalMaterial({name:'HairGroom',roughness:.72,specularIntensity:.25,anisotropy:0,normalScale:new T.Vector2(.1,.1),alphaTest:.38});
  const hair=await createHairCardGroom({human:f.human,loader:{loadAsync:async()=>({scene:f.scene})}}),material=hair.mesh.material;
  assert.equal(material.roughness,.72);assert.equal(material.specularIntensity,.25);assert.equal(material.anisotropy,0);assert.deepEqual(material.normalScale.toArray(),[.1,.1]);hair.dispose();
});

test('asset errors are actionable and leave the baseline untouched',async()=>{
  const f=fixture(),original=f.cap.geometry;
  await assert.rejects(createHairCardGroom({human:f.human,loader:{loadAsync:async()=>{throw Error('HTTP 404');}}}),/hair-cards.glb.*HTTP 404/);
  assert.equal(f.cap.geometry,original);assert.equal(f.cap.visible,true);assert.equal(f.human.getObjectByName('HairGroom'),undefined);
});

test('real Blender asset binds to all retained morphs and keeps world coordinates through head pose and height',async()=>{
  const original=await asset('../assets/human/foundation.glb'),authored=await asset('../assets/human/hair-cards/hair-cards.glb'),human=original.scene,cap=human.getObjectByName('HairCrop');
  const reference=authored.scene.getObjectByName('HairGroom'),before=reference.geometry.attributes.position.array.slice();
  const hair=await createHairCardGroom({human,loader:{loadAsync:async()=>authored}});
  assert.equal(hair.stats.meshCount,2);assert.equal(hair.stats.morphCount,28);assert.ok(hair.stats.vertices<20000);assert.ok(hair.stats.triangles<25000);
  assert.equal(new Set(hair.meshes.map(m=>m.skeleton)).size,1);assert.equal(hair.mesh.skeleton.bones.length,53);
  for(const value of [0,1]){
    cap.morphTargetInfluences.fill(value);hair.update(project);
    for(const mesh of hair.meshes){assert.equal(mesh.morphTargetInfluences.length,28);assert.ok(mesh.morphTargetInfluences.every(v=>v===value));assert.ok(mesh.geometry.attributes.position.array.every(Number.isFinite));}
  }
  cap.morphTargetInfluences.fill(0);hair.update(project);human.updateMatrixWorld(true);cap.skeleton.update();authored.scene.updateMatrixWorld(true);reference.skeleton.update();
  for(let i=0;i<reference.geometry.attributes.position.count;i+=191)close(point(hair.mesh,i),point(reference,i),'real asset neutral');
  const head=cap.skeleton.bones.find(b=>b.name==='head');head.rotation.z+=.25;human.scale.setScalar(1.1);human.rotation.y=.6;human.updateMatrixWorld(true);cap.skeleton.update();
  for(let i=0;i<hair.mesh.geometry.attributes.position.count;i+=191){const p=point(hair.mesh,i);assert.ok(p.toArray().every(Number.isFinite));assert.ok(p.y>1.4&&p.y<1.9);}
  assert.deepEqual(reference.geometry.attributes.position.array,before);assert.match(HAIR_CARD_LIMIT,/Not strand simulation/);hair.dispose();
});

test('procedural generation is explicit and restores the original scalp across all three modes',async()=>{
  const original=await asset('../assets/human/foundation.glb'),authored=await asset('../assets/human/hair-cards/hair-cards.glb'),human=original.scene,cap=human.getObjectByName('HairCrop'),sourceGeometry=cap.geometry,sourceMaterial=cap.material;
  const hair=await createHairCardGroom({human,compareHair:true,loader:{loadAsync:async()=>authored}}),procedural=human.getObjectByName('HairProceduralGroom');
  assert.equal(hair.stats.comparisonEnabled,true);assert.ok(hair.stats.procedural.buildMilliseconds>0);assert.ok(procedural);
  for(let i=0;i<2;i++)for(const mode of ['procedural','groom','baseline']){
    hair.setPreview(mode);hair.update(project);assert.equal(procedural.visible,mode==='procedural');assert.equal(hair.mesh.visible,mode==='groom');assert.equal(cap.visible,mode!=='groom');
    if(mode==='procedural'){assert.notEqual(cap.geometry,sourceGeometry);assert.notEqual(cap.material,sourceMaterial);}else{assert.equal(cap.geometry,sourceGeometry);assert.equal(cap.material,sourceMaterial);}
    hair.update({...project,hair:'none'});assert.ok([cap,human.getObjectByName('HairStrands'),...hair.meshes].every(m=>!m.visible));
  }
  hair.dispose();
});

test('cards export only the active geometry with named morphs, skin and standard portable material properties',async()=>{
  class FileReader{readAsArrayBuffer(blob){blob.arrayBuffer().then(v=>{this.result=v;this.onloadend?.();});}readAsDataURL(blob){blob.arrayBuffer().then(v=>{this.result='data:application/octet-stream;base64,'+Buffer.from(v).toString('base64');this.onloadend?.();});}}
  globalThis.FileReader=FileReader;
  const f=fixture(),hair=await createHairCardGroom({human:f.human,loader:{loadAsync:async()=>({scene:f.scene})}});hair.update(project);
  const document=await new GLTFExporter().parseAsync(f.human,{onlyVisible:true});
  assert.ok(document.nodes.some(n=>n.name==='HairGroom'));assert.ok(document.nodes.some(n=>n.name==='HairCardRoot'));assert.ok(!document.nodes.some(n=>['HairCrop','HairStrands'].includes(n.name)));assert.equal(document.skins.length,2);
  const material=document.materials.find(m=>m.name==='HairGroom');assert.equal(material.alphaMode,'MASK');assert.equal(material.alphaCutoff,.38);assert.equal(material.doubleSided,true);assert.equal(material.extensions.KHR_materials_anisotropy.anisotropyStrength,.65);
  for(const mesh of document.meshes)assert.ok(mesh.extras.targetNames.includes('HeadWide'));
  hair.update({...project,hair:'none'});const bald=await new GLTFExporter().parseAsync(f.human,{onlyVisible:true});assert.ok(!bald.nodes.some(n=>/Hair/.test(n.name)));hair.dispose();
});

test('the app default imports the baked loader rather than evaluating the rejected generator',()=>{
  const renderer=readFileSync(new URL('../src/human-renderer.js',import.meta.url),'utf8'),module=readFileSync(new URL('../src/hair-card-groom.js',import.meta.url),'utf8');
  assert.match(renderer,/imported\.traverse[\s\S]*?o\.castShadow=o\.name!=='HairGroom'/);
  assert.match(renderer,/createHumanRenderer\(canvas,\{compareHair=false\}/);assert.doesNotMatch(renderer,/from ['"]\.\/hair-groom\.js/);assert.match(module,/if\(compareHair\)\{[\s\S]*?await import\('\.\/hair-groom\.js'\)/);
});
