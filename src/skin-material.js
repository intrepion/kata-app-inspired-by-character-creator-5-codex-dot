import * as THREE from '../vendor/three.module.min.js';

export const SKIN_FILES=['skin-color.png','skin-normal.png','skin-roughness.png','skin-thin.png'];
export const SKIN_TRANSFER_LIMIT='Base color, normal and roughness export as glTF PBR textures. The browser thin-tissue backlight approximation is not exported and is not volumetric subsurface scattering.';
export function skinDirectShader(source){
  const anchor='reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );';
  if(!source.includes(anchor))throw Error('Skin shader does not match bundled Three.js');
  return source.replace(anchor,anchor+`
  // A small, shadow-aware transmitted lobe, strongest at thin ear tissue.
  // This is an artistic single-surface approximation, not path-traced SSS.
  float thin = texture2D( skinThinMap, vMapUv ).r;
  float back = pow( max( dot( -geometryNormal, directLight.direction ), 0.0 ), 1.8 );
  float forward = pow( max( dot( geometryViewDir, -directLight.direction ), 0.0 ), 2.0 );
  vec3 tint = vec3( 1.0, 0.32, 0.18 );
  reflectedLight.directDiffuse += directLight.color * material.diffuseColor * tint * thin * back * ( 0.065 + 0.10 * forward );
`);
}

/** Uses the original UV layout. Does not touch geometry, morphs or skeletons. */
export async function createSkinMaterial(original,maxAnisotropy=1){
  const loader=new THREE.TextureLoader(),loaded=[];
  try {
    for(const file of SKIN_FILES){
      const texture=await loader.loadAsync(new URL('../assets/human/skin/'+file,import.meta.url).href);
      texture.flipY=false;texture.anisotropy=maxAnisotropy;texture.name=file;loaded.push(texture);
    }
  } catch(error){loaded.forEach(t=>t.dispose());throw Error('Regional skin maps could not be loaded. '+error.message);}
  const [map,normalMap,roughnessMap,thin]=loaded;map.colorSpace=THREE.SRGBColorSpace;
  const material=original.clone();material.name='Skin';material.map=map;material.normalMap=normalMap;material.normalScale.set(.55,.55);
  material.roughnessMap=roughnessMap;material.roughness=1;material.metalness=0;
  material.envMapIntensity=.5;
  if('ior' in material)material.ior=1.4;
  material.userData={...original.userData,skinPass:'regional-v1',skinTransferLimit:SKIN_TRANSFER_LIMIT};
  material.onBeforeCompile=shader=>{
    shader.uniforms.skinThinMap={value:thin};
    shader.fragmentShader='uniform sampler2D skinThinMap;\n'+shader.fragmentShader.replace('#include <lights_physical_pars_fragment>',skinDirectShader(THREE.ShaderChunk.lights_physical_pars_fragment));
  };
  material.customProgramCacheKey=()=> 'persona-regional-skin-v1';
  return {material,dispose(){loaded.forEach(t=>t.dispose());material.dispose();}};
}
