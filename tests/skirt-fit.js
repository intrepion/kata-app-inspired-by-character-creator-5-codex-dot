// Actual loaded mesh and skin evaluation in the localhost browser. This checks
// sampled body surfaces and layered waist clearance; it is not cloth collision.
import * as T from '../vendor/three.module.min.js';
const scratch=new T.Vector3();
function vertices(mesh){const p=[];for(let i=0;i<mesh.geometry.attributes.position.count;i++){mesh.getVertexPosition(i,scratch).applyMatrix4(mesh.matrixWorld);p.push(scratch.x,scratch.y,scratch.z);}return p;}
function section(p,indices,y){const lines=[];for(let i=0;i<indices.length;i+=3){const q=[];for(let k=0;k<3;k++){const a=indices[i+k]*3,b=indices[i+(k+1)%3]*3,dy=p[b+1]-p[a+1];if(Math.abs(dy)<1e-10)continue;const t=(y-p[a+1])/dy;if(t<0||t>=1)continue;q.push([p[a]+t*(p[b]-p[a]),p[a+2]+t*(p[b+2]-p[a+2])]);}if(q.length===2)lines.push(q);}return lines;}
function radius(lines,a){const c=Math.cos(a),s=Math.sin(a);let max=null;for(const[[x,z],[xx,zz]]of lines){const dx=xx-x,dz=zz-z,den=c*dz-s*dx;if(Math.abs(den)<1e-10)continue;const r=(x*dz-z*dx)/den,t=(x*s-z*c)/den;if(r>0&&t>=-1e-7&&t<=1+1e-7)max=Math.max(max??0,r);}return max;}
export function checkSkirtFit(gltf,skirt){
 const scene=gltf.scene,body=scene.getObjectByName('HumanBody'),shirt=scene.getObjectByName('Outfit'),mixer=new T.AnimationMixer(scene),meshes=[];scene.traverse(o=>{if(o.isMesh)meshes.push(o)});
 // Only lower torso/legs, identified in the immutable bind mesh, never arms.
 const lower=[];const base=body.geometry.attributes.position.array,ids=body.geometry.index.array;
 for(let i=0;i<ids.length;i+=3){const tri=[ids[i],ids[i+1],ids[i+2]];if(tri.every(v=>base[3*v+1]<.99&&Math.abs(base[3*v])<.24))lower.push(...tri);}
 let bodyClearance=Infinity,waistClearance=Infinity,samples=0,worst=null,waistWorst=null;const missing=[];
 for(const pose of ['relaxed','tpose','wave','stride'])for(const build of [0,.25,.5,.75,1])for(const swing of [-.12,0,.12]){
  mixer.stopAllAction();mixer.clipAction(gltf.animations.find(c=>c.name===pose)).reset().play();mixer.setTime(0);
  for(const mesh of meshes){mesh.morphTargetInfluences?.fill(0);for(const[name,value]of [[build<.5?'BuildNarrow':'BuildBroad',Math.abs(build-.5)*2],['Pose'+pose[0].toUpperCase()+pose.slice(1),1]]){const index=mesh.morphTargetDictionary?.[name];if(index!==undefined)mesh.morphTargetInfluences[index]=value;}}
  skirt.update({lowerGarment:'skirt',pose,build,skirtSwing:swing});scene.updateMatrixWorld(true);meshes.forEach(m=>m.skeleton?.update());
  const b=vertices(body),s=vertices(skirt.mesh),top=vertices(shirt),skirtIds=skirt.mesh.geometry.index.array;
  for(const y of [.65,.70,.75,.80,.85,.9,.935]){const inner=section(b,lower,y),outer=section(s,skirtIds,y);for(let degree=0;degree<360;degree+=5){const angle=degree*Math.PI/180,ib=radius(inner,angle),os=radius(outer,angle);if(ib===null)continue;if(os===null){missing.push({pose,build,swing,y,degree});continue;}samples++;if(os-ib<bodyClearance){bodyClearance=os-ib;worst={pose,build,swing,y,degree};}}}
  // Upper skirt lies beneath the untucked shirt. No rendered shirt is deleted.
  for(const y of [.96,.965]){const inner=section(s,skirtIds,y),outer=section(top,shirt.geometry.index.array,y);for(let degree=0;degree<360;degree+=5){const a=degree*Math.PI/180,si=radius(inner,a),so=radius(outer,a);if(si===null||so===null){missing.push({pose,build,swing,y,degree,layer:'waist'});continue;}if(so-si<waistClearance){waistClearance=so-si;waistWorst={pose,build,swing,y,degree};}}}
 }
 mixer.stopAllAction();return {cases:60,samples,bodyClearance,waistClearance,worst,waistWorst,missing,passed:bodyClearance>=.001&&waistClearance>=.0002&&missing.length===0};
}
