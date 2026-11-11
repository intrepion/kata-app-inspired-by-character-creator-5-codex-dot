import * as T from '../vendor/three.module.min.js';
import {GLTFLoader} from '../vendor/loaders/GLTFLoader.js';

export const HAIR_CARD_URL=new URL('../assets/human/hair-cards/hair-cards.glb',import.meta.url);
export const HAIR_CARD_LIMIT='Original Blender-authored static mesh cards with baked alpha textures and ordinary PBR materials. Not strand simulation; alpha-tested edges depend on the receiving renderer.';
export const HAIR_CARD_PREVIEW_LIMIT='Fine hair cards do not cast or receive studio shadows in this preview, avoiding coarse shadow-map artifacts. The scalp cap still casts shadows; exported geometry and materials are unchanged, and other viewers choose their own shadow settings.';
const materialsOf=mesh=>Array.isArray(mesh.material)?mesh.material:[mesh.material];
const nearlyEqual=(a,b)=>a.elements.every((v,i)=>Math.abs(v-b.elements[i])<1e-4);

// Bring an authored mesh into the retained scalp's bind space. glTF joint arrays
// are exporter-specific, so joint indices must never be copied by position.
export function bindHairCardMesh(authored,cap){
  if(!authored?.isSkinnedMesh||!cap?.isSkinnedMesh)throw Error('Hair cards require skinned meshes and the original HairCrop skeleton');
  const geometry=authored.geometry,joints=geometry.attributes.skinIndex,weights=geometry.attributes.skinWeight;
  if(!joints||!weights||joints.itemSize!==4||weights.itemSize!==4||joints.count!==geometry.attributes.position.count||weights.count!==joints.count)throw Error('Hair cards have invalid skin attributes');
  const targets=new Map();
  cap.skeleton.bones.forEach((bone,index)=>{if(targets.has(bone.name))throw Error('Duplicate target bone: '+bone.name);targets.set(bone.name,index);});
  const mapping=authored.skeleton.bones.map(bone=>targets.get(bone.name)),used=new Set();
  for(let i=0;i<joints.count;i++){
    let sum=0;
    for(let c=0;c<4;c++){
      const weight=weights.getComponent(i,c),joint=joints.getComponent(i,c);sum+=weight;
      if(!Number.isFinite(weight)||weight<0)throw Error('Hair cards have invalid skin weights');
      if(weight===0)continue;
      if(!Number.isInteger(joint)||mapping[joint]===undefined)throw Error('Hair cards reference an unknown bone: '+(authored.skeleton.bones[joint]?.name??joint));
      used.add(joint);
    }
    if(Math.abs(sum-1)>1e-3)throw Error('Hair card weights must sum to one');
  }
  let transform;
  for(const joint of used){
    const sourceInverse=authored.skeleton.boneInverses[joint],targetInverse=cap.skeleton.boneInverses[mapping[joint]];
    if(!sourceInverse||!targetInverse)throw Error('Hair cards are missing inverse bind matrices');
    const correction=cap.bindMatrix.clone().invert().multiply(targetInverse.clone().invert()).multiply(sourceInverse).multiply(authored.bindMatrix);
    if(!correction.elements.every(Number.isFinite))throw Error('Hair cards have invalid bind matrices');
    if(transform&&!nearlyEqual(transform,correction))throw Error('Hair card rest skeleton does not match the foundation');
    transform=correction;
  }
  if(!transform)throw Error('Hair cards have no weighted vertices');
  for(const name of Object.keys(cap.morphTargetDictionary||{}))if(authored.morphTargetDictionary?.[name]===undefined)throw Error('Hair cards are missing identity target: '+name);

  const mesh=authored.clone(false);mesh.geometry=geometry.clone();
  mesh.material=Array.isArray(authored.material)?authored.material.map(m=>m.clone()):authored.material.clone();
  const remapped=new Uint16Array(joints.count*4);
  for(let i=0;i<joints.count;i++)for(let c=0;c<4;c++)remapped[i*4+c]=mapping[joints.getComponent(i,c)]??0;
  mesh.geometry.setAttribute('skinIndex',new T.Uint16BufferAttribute(remapped,4));
  // BufferGeometry.applyMatrix4 does not transform morph attributes. Relative
  // position deltas use only the linear part, never the object translation.
  mesh.geometry.applyMatrix4(transform);
  const linear=new T.Matrix3().setFromMatrix4(transform),normalMatrix=new T.Matrix3().getNormalMatrix(transform),v=new T.Vector3(),base=new T.Vector3();
  for(const attr of mesh.geometry.morphAttributes.position||[])for(let i=0;i<attr.count;i++){
    v.fromBufferAttribute(attr,i);
    if(geometry.morphTargetsRelative)v.applyMatrix3(linear);else v.applyMatrix4(transform);
    attr.setXYZ(i,v.x,v.y,v.z);
  }
  for(const attr of mesh.geometry.morphAttributes.normal||[])for(let i=0;i<attr.count;i++){
    v.fromBufferAttribute(attr,i);
    if(geometry.morphTargetsRelative){
      base.fromBufferAttribute(geometry.attributes.normal,i);v.add(base).applyNormalMatrix(normalMatrix);
      base.fromBufferAttribute(mesh.geometry.attributes.normal,i);v.sub(base);
    }else v.applyNormalMatrix(normalMatrix);
    attr.setXYZ(i,v.x,v.y,v.z);
  }
  mesh.geometry.computeBoundingBox();mesh.geometry.computeBoundingSphere();
  mesh.position.copy(cap.position);mesh.quaternion.copy(cap.quaternion);mesh.scale.copy(cap.scale);mesh.updateMatrix();
  mesh.bindMode=cap.bindMode;mesh.bind(cap.skeleton,cap.bindMatrix);
  mesh.morphTargetDictionary={...authored.morphTargetDictionary};mesh.morphTargetInfluences=[...(authored.morphTargetInfluences||[])];
  mesh.userData={...mesh.userData,role:'hair',hairCards:{version:1,static:true,license:'MIT',transferLimit:HAIR_CARD_LIMIT}};
  mesh.castShadow=mesh.name!=='HairGroom';mesh.receiveShadow=mesh.name!=='HairGroom';mesh.frustumCulled=false;
  return mesh;
}

/** Load only baked geometry in the app. The rejected procedural comparison is
 * deliberately behind an explicit option, including its expensive generator. */
export async function createHairCardGroom({human,compareHair=false,loader=new GLTFLoader(),assetURL=HAIR_CARD_URL,maxAnisotropy=1}){
  const cap=human.getObjectByName('HairCrop'),strands=human.getObjectByName('HairStrands');
  if(!cap?.isSkinnedMesh||!strands)throw Error('Hair cards require the retained HairCrop and HairStrands');
  const original={geometry:cap.geometry,material:cap.material,capVisible:cap.visible,strandsVisible:strands.visible};
  const started=performance.now();let loaded;
  try{loaded=await loader.loadAsync(String(assetURL));}
  catch(error){throw new Error('The Blender hair cards could not be loaded. Check assets/human/hair-cards/hair-cards.glb. '+error.message);}
  loaded.scene.updateMatrixWorld(true);
  const authored=['HairGroom','HairCardRoot'].map(name=>loaded.scene.getObjectByName(name));
  const importedSkeletons=new Set(),importedGeometry=new Set(),importedMaterials=new Set();
  loaded.scene.traverse(o=>{if(o.skeleton)importedSkeletons.add(o.skeleton);if(o.geometry)importedGeometry.add(o.geometry);if(o.material)materialsOf(o).forEach(m=>importedMaterials.add(m));});
  let cards=[];
  try{for(const mesh of authored)cards.push(bindHairCardMesh(mesh,cap));}
  catch(error){
    cards.forEach(mesh=>{mesh.geometry.dispose();materialsOf(mesh).forEach(m=>m.dispose());});
    const textures=new Set();importedMaterials.forEach(m=>Object.values(m).forEach(t=>{if(t?.isTexture)textures.add(t);}));textures.forEach(t=>t.dispose());
    throw error;
  }finally{
    importedSkeletons.forEach(s=>s.dispose());importedGeometry.forEach(g=>g.dispose());importedMaterials.forEach(m=>m.dispose());
  }
  for(const mesh of cards){
    if(mesh.name==='HairGroom'){
      const portable=material=>{
        const hasAnisotropy=typeof material.anisotropy==='number';
        if(!material.isMeshPhysicalMaterial){const physical=new T.MeshPhysicalMaterial();T.MeshStandardMaterial.prototype.copy.call(physical,material);material.dispose();material=physical;}
        if(!hasAnisotropy)material.anisotropy=.65;
        material.alphaTest=.38;material.alphaToCoverage=true;
        return material;
      };
      mesh.material=Array.isArray(mesh.material)?mesh.material.map(portable):portable(mesh.material);
    }
    for(const material of materialsOf(mesh)){
      material.userData={...material.userData,baseColor:material.color.clone(),role:'hairColor'};material.envMapIntensity=.65;
      if(material.alphaTest>0)material.alphaToCoverage=true;
      for(const texture of Object.values(material))if(texture?.isTexture)texture.anisotropy=maxAnisotropy;
    }
    cap.parent.add(mesh);
  }
  const loadMilliseconds=performance.now()-started;
  let procedural;
  if(compareHair){
    const {createHairGroom}=await import('./hair-groom.js');
    procedural=createHairGroom({human});procedural.mesh.name='HairProceduralGroom';
  }
  const meshes=[...cards,...(procedural?[procedural.mesh]:[])];
  let preview='groom',lastProject,disposed=false;
  const stats={asset:String(assetURL),source:'Blender-authored baked cards',previewLimit:HAIR_CARD_PREVIEW_LIMIT,meshCount:cards.length,vertices:cards.reduce((n,m)=>n+m.geometry.attributes.position.count,0),triangles:cards.reduce((n,m)=>n+(m.geometry.index?.count||m.geometry.attributes.position.count)/3,0),morphCount:Object.keys(cards[0].morphTargetDictionary).length,loadMilliseconds,comparisonEnabled:!!procedural,procedural:procedural?.stats};
  function update(project){
    lastProject=project;
    if(procedural){procedural.setPreview(preview==='procedural'?'groom':'baseline');procedural.update(project);}
    // Restore the untouched source before either baseline or the authored cards.
    if(preview!=='procedural'){cap.geometry=original.geometry;cap.material=original.material;}
    const enabled=project.hair!=='none';cap.visible=enabled&&preview!=='groom';strands.visible=enabled&&preview==='baseline';
    for(const mesh of cards){
      mesh.visible=enabled&&preview==='groom';
      for(const material of materialsOf(mesh))material.color.set(project.hairColor);
      for(const [name,index]of Object.entries(mesh.morphTargetDictionary))mesh.morphTargetInfluences[index]=cap.morphTargetInfluences?.[cap.morphTargetDictionary[name]]||0;
    }
    for(const mesh of [cap,strands])for(const material of materialsOf(mesh))material.color.set(project.hairColor);
  }
  // Never show all three hair versions during the first render.
  cap.visible=false;strands.visible=false;if(procedural)procedural.mesh.visible=false;
  human.updateMatrixWorld(true);
  return{meshes,mesh:cards[0],stats,update,setPreview(mode){
    if(!['baseline','procedural','groom'].includes(mode))throw Error('Unknown hair preview');
    if(mode==='procedural'&&!procedural)throw Error('Procedural comparison requires createHumanRenderer(canvas, {compareHair:true})');
    preview=mode;if(lastProject)update(lastProject);
  },dispose(){
    if(disposed)return;disposed=true;
    procedural?.dispose();
    cap.geometry=original.geometry;cap.material=original.material;cap.visible=original.capVisible;strands.visible=original.strandsVisible;
    const textures=new Set(),materials=new Set();
    for(const mesh of meshes){mesh.removeFromParent();mesh.geometry.dispose();materialsOf(mesh).forEach(m=>{materials.add(m);Object.values(m).forEach(t=>{if(t?.isTexture)textures.add(t);});});}
    textures.forEach(t=>t.dispose());materials.forEach(m=>m.dispose());
  }};
}
