import {Vector3} from '../vendor/three.module.min.js';

/** Measure at unit model scale and zero orbit, with the requested pose applied.
 * Morphing and skinning are linear for a fixed pose. Independent controls add
 * their per-axis extrema; paired targets are alternatives, not simultaneous.
 * Nonappearance targets (such as pose correctives) remain fixed in the base.
 * A horizontal radius makes the resulting reference safe for any orbit angle.
 */
export function measureBodyEnvelope(meshes,morphs,maxHeight){
  let minY=Infinity,maxY=-Infinity,radius=0;
  const point=new Vector3();
  for(const mesh of meshes){
    const influences=mesh.morphTargetInfluences;
    const saved=influences?.slice();
    const count=mesh.geometry.attributes.position.count;
    const base=new Float64Array(count*3),lower=new Float64Array(count*3),upper=new Float64Array(count*3);
    try{
      // Only sweep appearance controls. Preserve the currently selected pose's
      // corrective morphs throughout both the base and endpoint measurements.
      for(const name of Object.values(morphs).flat()){
        const index=mesh.morphTargetDictionary?.[name];
        if(index!==undefined)influences[index]=0;
      }
      for(let i=0;i<count;i++){
        mesh.getVertexPosition(i,point).applyMatrix4(mesh.matrixWorld);
        point.toArray(base,i*3);
      }
      for(const mapping of Object.values(morphs)){
        const low=new Float64Array(count*3),high=new Float64Array(count*3);
        for(const name of Array.isArray(mapping)?mapping:[mapping]){
          const index=mesh.morphTargetDictionary?.[name];
          if(index===undefined)continue;
          influences[index]=1;
          for(let i=0;i<count;i++){
            mesh.getVertexPosition(i,point).applyMatrix4(mesh.matrixWorld);
            const values=[point.x,point.y,point.z];
            for(let axis=0;axis<3;axis++){
              const j=i*3+axis,delta=values[axis]-base[j];
              low[j]=Math.min(low[j],delta);high[j]=Math.max(high[j],delta);
            }
          }
          influences[index]=0;
        }
        for(let j=0;j<base.length;j++){lower[j]+=low[j];upper[j]+=high[j];}
      }
      for(let i=0;i<count;i++){
        const j=i*3;
        minY=Math.min(minY,base[j+1]+lower[j+1]);
        maxY=Math.max(maxY,base[j+1]+upper[j+1]);
        const x=Math.max(Math.abs(base[j]+lower[j]),Math.abs(base[j]+upper[j]));
        const z=Math.max(Math.abs(base[j+2]+lower[j+2]),Math.abs(base[j+2]+upper[j+2]));
        radius=Math.max(radius,Math.hypot(x,z));
      }
    }finally{if(saved)influences.splice(0,influences.length,...saved);}
  }
  return {minY:minY*maxHeight,maxY:maxY*maxHeight,radius:radius*maxHeight};
}

export function bodyCameraFrame(envelope,aspect,fov){
  const halfHeight=(envelope.maxY-envelope.minY)/2;
  const halfFrame=Math.max(halfHeight*1.32,envelope.radius/aspect*1.16);
  return {targetY:(envelope.minY+envelope.maxY)/2,
    distance:halfFrame/Math.tan(fov*Math.PI/360)+envelope.radius};
}

/** The anatomical head sits in front of the rig origin. Orbit its center too,
 * otherwise a tight profile view clips the nose at narrow viewport widths. */
export function portraitCameraFrame(faceY,faceZ,scale,yaw,aspect,fov){
  const halfFrame=Math.max(.15/aspect,.19)*scale;
  return {targetX:Math.sin(yaw)*faceZ*scale,targetY:faceY*scale,targetZ:Math.cos(yaw)*faceZ*scale,distance:halfFrame/Math.tan(fov*Math.PI/360)};
}
