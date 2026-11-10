import * as T from '../vendor/three.module.min.js';

// Original parametric A-line garment. No learned weights, external rigging data,
// physics engine, or edits to the foundation mesh/skeleton are involved.
const SEGMENTS=96, PANELS=8;
const HEIGHTS=[.971,.965,.955,.948,.935,.915,.89,.86,.82,.775,.73,.685,.64,.595,.57];
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const smooth=x=>{x=clamp(x);return x*x*(3-2*x);};

function shapedPositions(mesh,build){
  const p=mesh.geometry.attributes.position,out=Float32Array.from(p.array);
  const name=build<.5?'BuildNarrow':'BuildBroad',id=mesh.morphTargetDictionary?.[name];
  const delta=mesh.geometry.morphAttributes.position?.[id],weight=Math.abs(build-.5)*2;
  if(delta)for(let i=0;i<out.length;i++)out[i]+=delta.array[i]*weight;
  return out;
}

// Intersect the actual approved trousers with a horizontal plane. The skirt's
// hidden waist shares this contour; below the shirt it becomes a free shell.
function contour(positions,indices,y){
  const lines=[];
  for(let i=0;i<indices.length;i+=3){
    const points=[];
    for(let j=0;j<3;j++){
      const a=indices[i+j]*3,b=indices[i+(j+1)%3]*3,dy=positions[b+1]-positions[a+1];
      if(Math.abs(dy)<1e-10)continue;
      const t=(y-positions[a+1])/dy;if(t<0||t>=1)continue;
      points.push([positions[a]+t*(positions[b]-positions[a]),positions[a+2]+t*(positions[b+2]-positions[a+2])]);
    }
    if(points.length===2)lines.push(points);
  }
  return angle=>{
    const c=Math.cos(angle),s=Math.sin(angle);let radius=0;
    for(const [[x,z],[xx,zz]]of lines){const dx=xx-x,dz=zz-z,den=c*dz-s*dx;if(Math.abs(den)<1e-10)continue;const r=(x*dz-z*dx)/den,t=(x*s-z*c)/den;if(r>0&&t>=-1e-6&&t<=1+1e-6)radius=Math.max(radius,r);}
    if(radius<=0)throw Error(`Missing foundation fitting contour at y=${y}, angle=${angle}.`);
    return radius;
  };
}
function positionsFor(pants,build){
  const source=shapedPositions(pants,build),indices=pants.geometry.index.array;
  const hip=contour(source,indices,.89),waists=HEIGHTS.slice(0,4).map(y=>contour(source,indices,y));
  const x=hip(0)+.10,z=Math.max(hip(Math.PI/2),hip(3*Math.PI/2))+.105;
  const out=[];
  for(let row=0;row<HEIGHTS.length;row++){
    const y=HEIGHTS[row],down=smooth((.955-y)/(.955-.57));
    for(let segment=0;segment<=SEGMENTS;segment++){
      const a=(segment%SEGMENTS)/SEGMENTS*Math.PI*2,c=Math.cos(a),s=Math.sin(a);
      let radius;
      if(row<4)radius=waists[row](a)+[.0007,.0007,.001,.006][row];
      else{
        const upper=hip(a)+.012;
        const hem=1/Math.sqrt(c*c/(x*x)+s*s/(z*z));
        const blend=smooth((.935-y)/(.935-.57));
        radius=upper+(hem-upper)*blend;
      }
      // Shallow, continuous flutes give the hem structure without sharp folds.
      radius+=.0035*(1-Math.cos(16*a))*down;
      out.push(c*radius,y,s*radius);
    }
  }
  return new Float32Array(out);
}
function seamNormals(geometry){
  geometry.computeVertexNormals();const n=geometry.attributes.normal;
  for(let row=0;row<HEIGHTS.length;row++){
    const a=row*(SEGMENTS+1),b=a+SEGMENTS,v=new T.Vector3().fromBufferAttribute(n,a).add(new T.Vector3().fromBufferAttribute(n,b)).normalize();n.setXYZ(a,v.x,v.y,v.z);n.setXYZ(b,v.x,v.y,v.z);
  }
}
function geometryFor(pants){
  const geometry=new T.BufferGeometry(),base=positionsFor(pants,.5),uv=[],indices=[],skinIndex=[],skinWeight=[];
  geometry.setAttribute('position',new T.Float32BufferAttribute(base,3));
  for(let row=0;row<HEIGHTS.length;row++)for(let segment=0;segment<=SEGMENTS;segment++){
    const t=segment/SEGMENTS*PANELS,left=Math.floor(t)%PANELS,right=(left+1)%PANELS,mix=t-Math.floor(t);
    // The waist stays at the pelvis; only the hanging fabric follows panels.
    const panel=smooth((.91-HEIGHTS[row])/(.91-.62));
    skinIndex.push(0,1+left,1+right,0);skinWeight.push(1-panel,panel*(1-mix),panel*mix,0);
    uv.push(segment/SEGMENTS,(HEIGHTS[0]-HEIGHTS[row])/(HEIGHTS[0]-HEIGHTS.at(-1)));
    if(row<HEIGHTS.length-1&&segment<SEGMENTS){const a=row*(SEGMENTS+1)+segment,b=a+SEGMENTS+1;indices.push(a,a+1,b,a+1,b+1,b);}
  }
  geometry.setIndex(indices);geometry.setAttribute('uv',new T.Float32BufferAttribute(uv,2));
  geometry.setAttribute('skinIndex',new T.Uint16BufferAttribute(skinIndex,4));geometry.setAttribute('skinWeight',new T.Float32BufferAttribute(skinWeight,4));seamNormals(geometry);
  geometry.morphTargetsRelative=true;geometry.morphAttributes.position=[];geometry.morphAttributes.normal=[];
  for(const [build,name]of [[0,'BuildNarrow'],[1,'BuildBroad']]){
    const positions=positionsFor(pants,build),shape=new T.BufferGeometry();shape.setAttribute('position',new T.Float32BufferAttribute(positions,3));shape.setIndex(indices);seamNormals(shape);
    const delta=new T.Float32BufferAttribute(positions.map((v,i)=>v-base[i]),3);delta.name=name;geometry.morphAttributes.position.push(delta);
    const normals=new T.Float32BufferAttribute(shape.attributes.normal.array.map((v,i)=>v-geometry.attributes.normal.array[i]),3);normals.name=name;geometry.morphAttributes.normal.push(normals);shape.dispose();
  }
  return geometry;
}

export function skirtPoseRotations(pose,swing=0){
  return Array.from({length:PANELS},(_,i)=>{
    const a=i/PANELS*Math.PI*2;
    // Authored clearance for the four static poses, not simulated movement.
    const lift=pose==='stride'?.16*Math.abs(Math.sin(a)):.015;
    return [-lift*Math.sin(a),0,lift*Math.cos(a)+clamp(swing,-.12,.12)];
  });
}

export function createSkirtRig({human,pants,pelvis}){
  if(!human||!pants?.isSkinnedMesh||!pelvis?.isBone)throw Error('Skirt requires the original human, trousers, and pelvis.');
  human.updateMatrixWorld(true);
  const root=new T.Bone();root.name='skirt_anchor';root.userData={role:'garment',license:'MIT',description:'Original optional skirt auxiliary rig'};
  const desired=human.matrixWorld.clone().multiply(new T.Matrix4().makeTranslation(0,.89,0));
  const local=pelvis.matrixWorld.clone().invert().multiply(desired);local.decompose(root.position,root.quaternion,root.scale);pelvis.add(root);
  const bones=[root];
  for(let i=0;i<PANELS;i++){
    const bone=new T.Bone(),a=i/PANELS*Math.PI*2;bone.name=`skirt_panel_${String(i+1).padStart(2,'0')}`;bone.position.set(.12*Math.cos(a),0,.075*Math.sin(a));root.add(bone);bones.push(bone);
  }
  const material=new T.MeshStandardMaterial({name:'Skirt',color:0x3b5550,roughness:.92,metalness:0,side:T.DoubleSide});
  const mesh=new T.SkinnedMesh(geometryFor(pants),material);mesh.name='Skirt';mesh.castShadow=true;mesh.receiveShadow=true;mesh.frustumCulled=false;mesh.userData={role:'original-skirt',license:'MIT',construction:'Original parametric A-line shell',simulation:false};
  human.add(mesh);human.updateMatrixWorld(true);mesh.bind(new T.Skeleton(bones));
  function update(project){
    const visible=project.lowerGarment==='skirt';mesh.visible=visible;root.visible=visible;pants.visible=!visible;
    const build=project.build??.5;mesh.morphTargetInfluences[0]=Math.max(0,(.5-build)*2);mesh.morphTargetInfluences[1]=Math.max(0,(build-.5)*2);
    material.color.set(project.pants||'#3b5550');const rotations=skirtPoseRotations(project.pose,project.skirtSwing??0);bones.slice(1).forEach((b,i)=>b.rotation.set(...rotations[i]));
  }
  function extendClips(clips,swing=0){return clips.map(source=>{const clip=source.clone();const rotations=skirtPoseRotations(clip.name,swing);bones.slice(1).forEach((b,i)=>{const q=new T.Quaternion().setFromEuler(new T.Euler(...rotations[i])).toArray();clip.tracks.push(new T.QuaternionKeyframeTrack(`${b.name}.quaternion`,[0,Math.max(clip.duration,1/24)],q.concat(q),T.InterpolateDiscrete));});return clip;});}
  update({});
  return {mesh,root,bones,update,extendClips,triangleCount:mesh.geometry.index.count/3};
}
