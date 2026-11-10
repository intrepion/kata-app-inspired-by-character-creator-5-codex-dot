import {NumberKeyframeTrack,InterpolateDiscrete,PropertyBinding} from '../vendor/three.module.min.js';

export function applyPoseCorrectives(mesh,mapping,pose){
  for(const [name,target] of Object.entries(mapping||{})){
    const index=mesh.morphTargetDictionary?.[target];
    if(index!==undefined)mesh.morphTargetInfluences[index]=Number(name===pose);
  }
}

/** Each exported pose keeps the user's appearance, switches its own corrective
 * on, and explicitly clears the other poses' correctives. No change to the live
 * preview's influences and no baked-in edit to the editable appearance keys. */
export function exportPoseClips(clips,meshes,mapping){
  return clips.map(source=>{
    const clip=source.clone();
    clip.tracks=clip.tracks.filter(track=>!track.name.endsWith('.morphTargetInfluences'));
    for(const mesh of meshes){
      if(!mesh.morphTargetInfluences)continue;
      const copy={morphTargetDictionary:mesh.morphTargetDictionary,morphTargetInfluences:mesh.morphTargetInfluences.slice()};
      applyPoseCorrectives(copy,mapping,clip.name);
      clip.tracks.push(new NumberKeyframeTrack(`${mesh.name}.morphTargetInfluences`,[0,Math.max(clip.duration,1/24)],copy.morphTargetInfluences.concat(copy.morphTargetInfluences),InterpolateDiscrete));
    }
    return clip;
  });
}

/** Resolve track targets before assigning a user-visible root name. A character
 * named Skirt, HumanBody or a bone must never steal that child's animation. */
export function bindPoseClipsToUUID(clips,root){
  return clips.map(source=>{
    const clip=source.clone();
    for(const track of clip.tracks){
      const binding=PropertyBinding.parseTrackName(track.name);
      const node=PropertyBinding.findNode(root,binding.nodeName);
      if(!node)throw new Error(`Missing export animation target: ${binding.nodeName}`);
      const object=binding.objectName?`.${binding.objectName}${binding.objectIndex!==undefined?'['+binding.objectIndex+']':''}`:'';
      const property=`.${binding.propertyName}${binding.propertyIndex!==undefined?'['+binding.propertyIndex+']':''}`;
      track.name=node.uuid+object+property;
    }
    return clip;
  });
}
