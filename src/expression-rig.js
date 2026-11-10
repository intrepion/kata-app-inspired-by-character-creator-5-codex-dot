import {BufferGeometry,Float32BufferAttribute} from '../vendor/three.module.min.js';

// Original MIT expression fields, applied only to the existing CC0 foundation.
// These are closed-mouth poses, not jaw motion or a speech/viseme rig.
export const EXPRESSION_TARGETS=Object.freeze(['Smile','Frown','BrowRaise','BrowFurrow']);
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const smooth=(a,b,v)=>{const t=clamp((v-a)/(b-a));return t*t*(3-2*t);};
const bell=(v,c,r)=>{const t=clamp(1-Math.abs(v-c)/r);return t*t*(3-2*t);};
export function expressionWeights(project){
  const mouth=clamp(project.smile??0)-clamp(project.frown??0);
  const brow=clamp(project.browRaise??0)-clamp(project.browFurrow??0);
  return[Math.max(0,mouth),Math.max(0,-mouth),Math.max(0,brow),Math.max(0,-brow)];
}
export function expressionEyeControls(project){
  // A slight Duchenne-style squeeze follows the smile. Manual full blinks still
  // close completely, and existing gaze/closure corrections remain authoritative.
  const squeeze=expressionWeights(project)[0]*.12;
  return{...project,blinkLeft:clamp(project.blinkLeft??0)+squeeze*(1-clamp(project.blinkLeft??0)),blinkRight:clamp(project.blinkRight??0)+squeeze*(1-clamp(project.blinkRight??0))};
}
function displacement(x,y,z,target){
  const ax=Math.abs(x),sign=Math.sign(x),front=smooth(.09,.125,z);
  if(!front||y<1.35||y>1.54)return[0,0,0];
  if(target<2){
    // Both lip boundaries travel through one continuous field, retaining closure.
    const mouth=bell(y,1.398,.032)*(1-smooth(.027,.051,ax))*front;
    const corner=smooth(.002,.022,ax),cheek=bell(ax,.034,.027)*bell(y,1.431,.023)*front;
    if(target===0)return[sign*.0031*corner*mouth,.0068*corner*mouth-.00035*(1-corner)*mouth+.0022*cheek,-.0013*corner*mouth+.0011*cheek];
    return[-sign*.0006*corner*mouth,-.0053*corner*mouth+.00035*(1-corner)*mouth-.0008*cheek,.00045*corner*mouth];
  }
  // The eyebrow cards and their underlying forehead use the same field. Stop
  // above the eyelid so raising/furrowing never tears the independent blink seam.
  const brow=bell(y,1.481,.031)*smooth(1.468,1.476,y)*(1-smooth(.052,.070,ax))*front;
  if(target===2)return[0,.0080*brow,.0005*brow];
  const inner=1-smooth(.017,.052,ax);
  return[-sign*.0024*inner*brow,-.0046*inner*brow,.0010*inner*brow];
}
function normals(geometry,positions){const copy=new BufferGeometry();copy.setIndex(geometry.index);copy.setAttribute('position',new Float32BufferAttribute(positions,3));copy.computeVertexNormals();const array=copy.attributes.normal.array.slice();copy.dispose();return array;}
export function createExpressionRig({human,manifest}){
  const entries=['HumanBody','Brows'].map(name=>{
    const mesh=human.getObjectByName(name);if(!mesh)throw Error('Expression rig requires '+name);
    const g=mesh.geometry,dictionary={...mesh.morphTargetDictionary},count=g.morphAttributes.position?.length||0;
    g.morphAttributes.position??=[];g.morphAttributes.normal??=[];
    while(g.morphAttributes.normal.length<count)g.morphAttributes.normal.push(new Float32BufferAttribute(new Float32Array(g.attributes.position.count*3),3));
    for(const key of EXPRESSION_TARGETS)for(const kind of ['position','normal']){const attr=new Float32BufferAttribute(new Float32Array(g.attributes.position.count*3),3);attr.name=key;g.morphAttributes[kind].push(attr);}
    mesh.updateMorphTargets();mesh.morphTargetDictionary={...dictionary,...Object.fromEntries(EXPRESSION_TARGETS.map((key,i)=>[key,count+i]))};
    mesh.userData.expressionRig={version:1,targets:[...EXPRESSION_TARGETS],identityFitted:true,closedMouth:true,opposition:'subtract smile/frown and raise/furrow',smileSquint:.12};
    return{mesh,count,base:g.attributes.position.array};
  });
  let identityKey='';
  function identityPoints({mesh,base},project){const out=base.slice();for(const[key,names]of Object.entries(manifest.morphs)){const value=project[key]??.5,index=mesh.morphTargetDictionary[names[value<.5?0:1]],weight=Math.abs(value-.5)*2;if(index===undefined||!weight)continue;const d=mesh.geometry.morphAttributes.position[index].array;for(let i=0;i<out.length;i++)out[i]+=d[i]*weight;}return out;}
  function rebuild(project){
    const body=entries[0],bodyNeutral=identityPoints(body,project);
    // Fit expression amplitudes to the exported identity's face proportions.
    const bounds=[ [Infinity,-Infinity,Infinity,-Infinity], [Infinity,-Infinity,Infinity,-Infinity] ];
    for(let i=0;i<body.base.length;i+=3)if(body.base[i+1]>1.385&&body.base[i+1]<1.495&&body.base[i+2]>.12&&Math.abs(body.base[i])<.052){for(const[j,p]of [body.base,bodyNeutral].entries()){bounds[j][0]=Math.min(bounds[j][0],p[i]);bounds[j][1]=Math.max(bounds[j][1],p[i]);bounds[j][2]=Math.min(bounds[j][2],p[i+1]);bounds[j][3]=Math.max(bounds[j][3],p[i+1]);}}
    const sx=clamp((bounds[1][1]-bounds[1][0])/(bounds[0][1]-bounds[0][0]),.7,1.4),sy=clamp((bounds[1][3]-bounds[1][2])/(bounds[0][3]-bounds[0][2]),.7,1.4);
    for(const entry of entries){const{mesh,count,base}=entry,g=mesh.geometry,current=identityPoints(entry,project),n0=normals(g,current);
      for(let target=0;target<EXPRESSION_TARGETS.length;target++){
        const out=current.slice(),position=g.morphAttributes.position[count+target],normal=g.morphAttributes.normal[count+target];
        for(let i=0;i<base.length;i+=3){const d=displacement(base[i],base[i+1],base[i+2],target);out[i]+=d[0]*sx;out[i+1]+=d[1]*sy;out[i+2]+=d[2];}
        const n1=normals(g,out);for(let i=0;i<out.length;i++){position.array[i]=out[i]-current[i];normal.array[i]=n1[i]-n0[i];}position.needsUpdate=true;normal.needsUpdate=true;
      }
      // Three.js caches the morph texture by count, not attribute version.
      g.dispose();
    }
  }
  function update(project){const key=JSON.stringify(Object.keys(manifest.morphs).map(k=>project[k]??.5));if(key!==identityKey){rebuild(project);identityKey=key;}const weights=expressionWeights(project);for(const{mesh,count}of entries)for(let i=0;i<weights.length;i++)mesh.morphTargetInfluences[count+i]=weights[i];}
  return{update,targets:EXPRESSION_TARGETS};
}
