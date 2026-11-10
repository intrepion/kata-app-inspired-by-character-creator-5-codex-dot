import * as THREE from '../vendor/three.module.min.js';
import {GLTFLoader} from '../vendor/loaders/GLTFLoader.js';
import {applyPoseCorrectives,exportPoseClips,bindPoseClipsToUUID} from './pose-morphs.js';
import {createHumanSoftwareRenderer} from './human-software-renderer.js';
import {GLTFExporter} from '../vendor/exporters/GLTFExporter.js';
import {measureBodyEnvelope,bodyCameraFrame,portraitCameraFrame} from './human-framing.js';
import {ranges} from './project.js';
import {createSkirtRig} from './skirt-rig.js';
import {createEyeRig} from './eye-rig.js';

/** A locally bundled CC0 foundation with original MIT portrait and skirt additions. No network/CDN fallback. */
export async function createHumanRenderer(canvas) {
  let renderer, rendererMode='webgl';
  try {
    const context=canvas.getContext('webgl2',{antialias:true,alpha:true,preserveDrawingBuffer:true});
    if(!context)throw new Error('WebGL 2 unavailable');
    renderer = new THREE.WebGLRenderer({canvas, context, antialias:true, alpha:true, preserveDrawingBuffer:true});
  } catch {
    try{renderer=createHumanSoftwareRenderer(canvas);rendererMode='software';}
    catch{throw new Error('This browser cannot create a graphics or Canvas 2D preview. Projects can still be opened and saved.');}
  }
  renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(29, 1, .01, 40);
  const orbit = new THREE.Group();
  scene.add(orbit);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x777777, .85));
  const key = new THREE.DirectionalLight(0xffffff, 2.5);
  key.position.set(-2.8, 4.8, 4.2); key.castShadow=true;
  key.shadow.mapSize.set(1024,1024);
  Object.assign(key.shadow.camera,{left:-2,right:2,top:2,bottom:-2,near:.1,far:12});
  key.shadow.bias=-.0002; key.shadow.normalBias=.015; scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, .9); fill.position.set(3,2,3);scene.add(fill);
  // Neutral studio cards provide actual reflected highlights, not painted eye dots.
  let studioEnvironment;
  if(rendererMode==='webgl'){
    const studio=new THREE.Scene();studio.background=new THREE.Color(.18,.18,.18);
    for(const [x,y,z,w,h,power] of [[-2,3,3,2,3,4],[3,2,2,1,2,2]]){
      const card=new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({color:new THREE.Color(power,power,power),side:THREE.DoubleSide}));
      card.position.set(x,y,z);card.lookAt(0,1,0);studio.add(card);
    }
    const pmrem=new THREE.PMREMGenerator(renderer);studioEnvironment=pmrem.fromScene(studio,.05);scene.environment=studioEnvironment.texture;
    studio.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});pmrem.dispose();
  }
  const floor = new THREE.Mesh(new THREE.CircleGeometry(3,64),new THREE.ShadowMaterial({opacity:.13}));
  floor.name='StudioShadow';
  floor.rotation.x=-Math.PI/2; floor.position.y=.002; floor.receiveShadow=true;scene.add(floor);
  const ring = new THREE.Mesh(new THREE.RingGeometry(.53,.535,80),new THREE.MeshBasicMaterial({color:0xbbbdb0,transparent:true,opacity:.45,side:THREE.DoubleSide}));
  ring.name='StudioRing';
  ring.rotation.x=-Math.PI/2;ring.position.y=.001;scene.add(ring);
  let gltf, manifest;
  try {
    const response = await fetch(new URL('../assets/human/manifest.json',import.meta.url));
    if(!response.ok) throw new Error(`Asset manifest: HTTP ${response.status}`);
    manifest=await response.json();
    gltf=await new GLTFLoader().loadAsync(new URL(manifest.model || 'foundation.glb',response.url).href);
  } catch(error) {
    renderer.dispose();
    throw new Error(`The human model could not be loaded. Check that the complete assets folder is served with this app. ${error.message}`);
  }
  const human = gltf.scene;
  human.name='PersonaForgeHuman'; orbit.add(human);
  const meshes=[],bones=new Map(),rest=new Map();
  human.traverse(object=>{
    if(object.isBone){bones.set(object.name,object);rest.set(object.name,{quaternion:object.quaternion.clone(),position:object.position.clone(),scale:object.scale.clone()});}
    if(object.isMesh){object.castShadow=true;object.receiveShadow=true;object.frustumCulled=false;meshes.push(object);
      for(const material of Array.isArray(object.material)?object.material:[object.material]){
        material.userData.baseColor=material.color.clone();material.envMapIntensity=.65;
        if(material.name==='Cornea'){material.depthWrite=false;}
        if(material.map)material.map.anisotropy=Math.min(renderer.capabilities.getMaxAnisotropy(),8);
      }
    }
  });
  if(!meshes.some(mesh=>mesh.isSkinnedMesh) || !bones.size){renderer.dispose();throw new Error('The bundled model is missing its editable skin and skeleton.');}
  const skirt=createSkirtRig({human,pants:human.getObjectByName('Pants'),pelvis:bones.get('pelvis')});
  meshes.push(skirt.mesh);
  const eyeRig=createEyeRig({human,manifest});
  const visibleTriangleCount=()=>meshes.filter(mesh=>mesh.visible).reduce((count,mesh)=>count+(mesh.geometry.index?.count||mesh.geometry.attributes.position.count)/3,0);
  const mixer=new THREE.AnimationMixer(human);
  const clips=new Map(gltf.animations.map(clip=>[clip.name.toLowerCase(),clip]));
  const bodyEnvelopes=new Map();
  let current, lost=false, lastYaw=.32,lastFocus='body';
  canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();lost=true;canvas.dispatchEvent(new CustomEvent('previewerror',{detail:'The graphics context was lost. Save your project, then reload to restore the preview.'}));});
  function applyPose(name){
    mixer.stopAllAction();
    for(const[boneName,bone]of bones){const saved=rest.get(boneName);bone.quaternion.copy(saved.quaternion);bone.position.copy(saved.position);bone.scale.copy(saved.scale);}
    const clip=clips.get(name);
    if(clip){const action=mixer.clipAction(clip);action.reset().play();mixer.setTime(0);}
    else for(const[boneName,value]of Object.entries(manifest.poses?.[name] || {})){
      const bone=bones.get(boneName);if(!bone)continue;
      const quaternion=new THREE.Quaternion(...(value.quaternion || value));
      if(manifest.posesRelative)bone.quaternion.multiply(quaternion);else bone.quaternion.copy(quaternion);
    }
  }
  function roleFor(material){
    for(const[role,names]of Object.entries(manifest.materials || {}))if((Array.isArray(names)?names:[names]).includes(material.name))return role;
    return ({skin:'skin',outfit:'outfit',pants:'pants',hair:'hairColor'})[material.name.toLowerCase()];
  }
  function update(project){
    current=structuredClone(project);
    human.scale.setScalar(project.height);
    applyPose(project.pose);
    for(const mesh of meshes){
      if(mesh.morphTargetInfluences){mesh.morphTargetInfluences.fill(0);
        for(const[control,mapping]of Object.entries(manifest.morphs || {})){
          const value=project[control]??.5;
          if(Array.isArray(mapping)){
            const name=mapping[value<.5?0:1], index=mesh.morphTargetDictionary?.[name];
            if(index!==undefined)mesh.morphTargetInfluences[index]=Math.abs(value-.5)*2;
          }else{
            const index=mesh.morphTargetDictionary?.[mapping];
            if(index!==undefined)mesh.morphTargetInfluences[index]=value;
          }
        }
      }
      applyPoseCorrectives(mesh,manifest.poseCorrectives,project.pose);
      const isHair=(manifest.hairMeshes || ['Hair']).includes(mesh.name)||mesh.userData.role==='hair';
      if(isHair)mesh.visible=project.hair!=='none';
      for(const material of Array.isArray(mesh.material)?mesh.material:[mesh.material]){
        const role=roleFor(material);if(!role||!project[role])continue;
        material.color.set(project[role]);
        if(role==='skin'&&manifest.skinReference){
          const reference=new THREE.Color(manifest.skinReference);
          material.color.r/=Math.max(reference.r,.01);material.color.g/=Math.max(reference.g,.01);material.color.b/=Math.max(reference.b,.01);
          material.color.multiply(material.userData.baseColor);
          for(const channel of ['r','g','b'])material.color[channel]=Math.min(1,material.color[channel]);
        }
      }
    }
    skirt.update(project);
    eyeRig.update(project);
    // Cache a reference for this pose, never the current height/body shape.
    if(!bodyEnvelopes.has(project.pose)){
      const savedYaw=orbit.rotation.y;
      human.scale.setScalar(1);orbit.rotation.y=0;
      orbit.updateMatrixWorld(true);
      meshes.forEach(mesh=>mesh.skeleton?.update());
      try{bodyEnvelopes.set(project.pose,measureBodyEnvelope(meshes,manifest.morphs||{},ranges.height[1]));}
      finally{human.scale.setScalar(project.height);orbit.rotation.y=savedYaw;}
    }
    orbit.updateMatrixWorld(true);
  }
  function render(yaw=lastYaw,focus=lastFocus){
    if(lost)throw new Error('Graphics context lost. Save your project and reload.');
    lastYaw=yaw;lastFocus=focus;
    const width=Math.max(canvas.clientWidth,1),height=Math.max(canvas.clientHeight,1);
    if(canvas.width!==Math.round(width*renderer.getPixelRatio())||canvas.height!==Math.round(height*renderer.getPixelRatio()))renderer.setSize(width,height,false);
    camera.aspect=width/height;
    const scale=current?.height||1;
    // Body framing stays fixed while height, shape and orbit change.
    orbit.rotation.y=yaw;
    orbit.updateMatrixWorld(true);
    meshes.forEach(mesh=>mesh.skeleton?.update());
    let targetX=0,targetZ=0,targetY,distance;
    if(focus==='face'){
      ({targetX,targetY,targetZ,distance}=portraitCameraFrame(manifest.faceTargetY||1.44,manifest.faceTargetZ??.045,scale,yaw,camera.aspect,camera.fov));
    }else{
      ({targetY,distance}=bodyCameraFrame(bodyEnvelopes.get(current.pose),camera.aspect,camera.fov));
    }
    camera.position.set(targetX,targetY+.04*(focus==='face'?scale:1),targetZ+distance);camera.lookAt(targetX,targetY,targetZ);camera.updateProjectionMatrix();
    renderer.render(scene,camera);
  }
  async function exportGLB(name){
    if(!current)throw new Error('The character has not finished loading.');
    orbit.updateMatrixWorld(true);
    const previous=human.name;
    const poseClips=exportPoseClips(gltf.animations,meshes.filter(mesh=>mesh.visible),manifest.poseCorrectives);
    const animations=bindPoseClipsToUUID(current.lowerGarment==='skirt'?skirt.extendClips(poseClips,current.skirtSwing):poseClips,human).sort((a,b)=>Number(b.name===current.pose)-Number(a.name===current.pose));
    human.name=name||previous;
    try{return await new GLTFExporter().parseAsync(human,{binary:true,onlyVisible:true,trs:true,animations,includeCustomExtensions:false});}
    finally{human.name=previous;}
  }
  return {update,render,exportGLB,get triangleCount(){return visibleTriangleCount();},info:{mode:rendererMode,boneCount:bones.size,get auxiliaryBoneCount(){return current?.lowerGarment==='skirt'?skirt.bones.length:0;},morphs:manifest.morphs,license:manifest.license||'See asset license manifest',gpu:rendererMode==='webgl'?renderer.getContext().getParameter(renderer.getContext().getExtension('WEBGL_debug_renderer_info')?.UNMASKED_RENDERER_WEBGL||renderer.getContext().RENDERER):'CPU'},dispose(){studioEnvironment?.dispose();mixer.stopAllAction();const textures=new Set(),materials=new Set(),skeletons=new Set();meshes.forEach(mesh=>{if(mesh.skeleton)skeletons.add(mesh.skeleton);mesh.geometry.dispose();for(const material of Array.isArray(mesh.material)?mesh.material:[mesh.material]){materials.add(material);for(const value of Object.values(material))if(value?.isTexture)textures.add(value);}});textures.forEach(texture=>texture.dispose());materials.forEach(material=>material.dispose());skeletons.forEach(skeleton=>skeleton.dispose());renderer.dispose();}};
}
