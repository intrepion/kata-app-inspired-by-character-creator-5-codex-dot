import {BufferGeometry,Float32BufferAttribute} from '../vendor/three.module.min.js';

// Original MIT blink/gaze deformation. The licensed source mesh is never changed.
// Each app identity gets fitted editable endpoints. Character-left is +X.
export const EYE_TARGETS=Object.freeze(['BlinkLeft','BlinkRight','GazeLeft','GazeRight','GazeUp','GazeDown','BlinkLeftGazeUp','BlinkLeftGazeDown','BlinkRightGazeUp','BlinkRightGazeDown']);
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const smooth=(a,b,v)=>{const t=clamp((v-a)/(b-a),0,1);return t*t*(3-2*t);};
const rim=[[.0138,1.4594,1.4578],[.017,1.4607,1.4573],[.020,1.4620,1.4571],[.025,1.4648,1.4566],[.029,1.4650,1.4566],[.033,1.4648,1.4568],[.036,1.4642,1.4574],[.039,1.4626,1.4585],[.0425,1.4607,1.4600]];
function lids(x){x=Math.abs(x);for(let i=1;i<rim.length;i++)if(x<rim[i][0]){const a=rim[i-1],b=rim[i],t=clamp((x-a[0])/(b[0]-a[0]),0,1);return[a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];}return rim.at(-1).slice(1);}
function lidPoint(x,y,z,blink,vertical,lashes=false){
  const ax=Math.abs(x),[top,bottom]=lids(x),mid=(top+bottom)/2,seam=bottom+(top-bottom)*.39;
  const side=smooth(.012,.015,ax)*(1-smooth(.045,.051,ax));
  const front=smooth(.113,.126,z);const upper=y>=mid;
  const influence=side*front*(upper?1-smooth(top+.001,top+.014,y):smooth(bottom-.013,bottom-.001,y));
  const shift=(seam-(upper?top:bottom)+(upper?-.00018:.00018))*blink;
  const follow=vertical*.0018*(1-blink);
  const yy=y+(shift+follow)*influence;
  const dx=(ax-.0302)/.014,dy=(yy-1.4621)/.015;
  const dome=.1208+.0135*Math.sqrt(Math.max(0,1-dx*dx-dy*dy));
  const zz=z+Math.max(0,dome+(lashes?.0006:.00015)-z)*influence*blink;
  return[x,yy,zz];
}
function neutral(mesh,count){const out=new Float32Array(mesh.geometry.attributes.position.array);for(let j=0;j<count;j++){const w=mesh.morphTargetInfluences?.[j]||0;if(!w)continue;const a=mesh.geometry.morphAttributes.position[j].array;for(let i=0;i<out.length;i++)out[i]+=w*a[i];}return out;}
function normals(geometry,positions){const copy=new BufferGeometry();copy.setIndex(geometry.index);copy.setAttribute('position',new Float32BufferAttribute(positions,3));copy.computeVertexNormals();const result=copy.attributes.normal.array.slice();copy.dispose();return result;}
export function createEyeRig({human,manifest}){
  const names=['HumanBody','Lashes','Eyes','Iris','Cornea'];
  const entries=names.map(name=>{const mesh=human.getObjectByName(name);if(!mesh)throw Error('Eye rig requires '+name);const dictionary={...mesh.morphTargetDictionary};const geometry=mesh.geometry,count=geometry.morphAttributes.position?.length||0;
    geometry.morphAttributes.position??=[];geometry.morphAttributes.normal??=[];
    while(geometry.morphAttributes.normal.length<count)geometry.morphAttributes.normal.push(new Float32BufferAttribute(new Float32Array(geometry.attributes.position.count*3),3));
    for(const key of EYE_TARGETS)for(const kind of ['position','normal']){const attribute=new Float32BufferAttribute(new Float32Array(geometry.attributes.position.count*3),3);attribute.name=key;geometry.morphAttributes[kind].push(attribute);}
    mesh.updateMorphTargets();mesh.morphTargetDictionary={...dictionary,...Object.fromEntries(EYE_TARGETS.map((name,i)=>[name,count+i]))};mesh.userData.eyeRig={version:1,targets:[...EYE_TARGETS],identityFitted:true,horizontalDegrees:12,verticalDegrees:8};return{mesh,count,base:geometry.attributes.position.array};
  });
  let identityKey='';
  const nearestCache=new Map();
  function rebuild(project){
    const body=entries[0],bodyNeutral=neutral(body.mesh,body.count),donors=[];
    for(let i=0;i<body.base.length;i+=3)if(Math.abs(body.base[i])>.009&&Math.abs(body.base[i])<.053&&body.base[i+1]>1.43&&body.base[i+1]<1.49&&body.base[i+2]>.113)donors.push(i);
    function fitted(point){const cacheKey=point.join(',');let nearest=nearestCache.get(cacheKey);if(!nearest){nearest=[];for(const i of donors){const d=(body.base[i]-point[0])**2+(body.base[i+1]-point[1])**2+(body.base[i+2]-point[2])**2;if(nearest.length<4||d<nearest.at(-1)[0]){nearest.push([d,i]);nearest.sort((a,b)=>a[0]-b[0]);nearest.length=Math.min(4,nearest.length);}}nearestCache.set(cacheKey,nearest);}const result=point.slice();let sum=0,delta=[0,0,0];for(const[d,i]of nearest){const w=1/Math.max(d,1e-9);sum+=w;for(let k=0;k<3;k++)delta[k]+=(bodyNeutral[i+k]-body.base[i+k])*w;}for(let k=0;k<3;k++)result[k]+=delta[k]/sum;return result;}
    const eye=entries.find(e=>e.mesh.name==='Eyes'),eyeNeutral=neutral(eye.mesh,eye.count),centers={},radii={};
    for(const sign of [-1,1]){const min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];for(let i=0;i<eyeNeutral.length;i+=3)if(eye.base[i]*sign>0)for(let k=0;k<3;k++){min[k]=Math.min(min[k],eyeNeutral[i+k]);max[k]=Math.max(max[k],eyeNeutral[i+k]);}centers[sign]=min.map((v,k)=>(v+max[k])/2);radii[sign]=min.map((v,k)=>(max[k]-v)/2+[.002,.002,.0048][k]);const irisEntry=entries.find(e=>e.mesh.name==='Iris'),irisPoints=neutral(irisEntry.mesh,irisEntry.count);let total=0,sx=0,sy=0;for(let j=0;j<irisPoints.length;j+=3)if(irisEntry.base[j]*sign>0){total++;sx+=irisPoints[j];sy+=irisPoints[j+1];}centers[sign][0]=sx/total;centers[sign][1]=sy/total;}

    for(const entry of entries){const {mesh,count,base}=entry,g=mesh.geometry,current=neutral(mesh,count),n0=normals(g,current),isLid=['HumanBody','Lashes'].includes(mesh.name);
      for(let target=0;target<EYE_TARGETS.length;target++){
        const out=current.slice();
        for(let i=0;i<base.length;i+=3){const sign=base[i]>=0?1:-1;
          if(isLid){if(base[i+1]<1.43||base[i+1]>1.49||Math.abs(base[i])<.009||Math.abs(base[i])>.053||base[i+2]<.113)continue;
            const corrective=target>=6,correctiveSide=target<8?1:-1;
            const blink=target===0&&sign===1||target===1&&sign===-1?1:0,vertical=target===4?1:target===5?-1:corrective&&sign===correctiveSide?(target%2===0?1:-1):0;if(!blink&&!vertical)continue;
            const p=lidPoint(base[i],base[i+1],base[i+2],blink,vertical,mesh.name==='Lashes');
            if(p.every((v,k)=>v===base[i+k]))continue;
            const fittedPoint=fitted(p),oldFit=fitted([base[i],base[i+1],base[i+2]]);
            // Preserve the attachment's neutral offset while transporting it with skin.
            for(let k=0;k<3;k++)out[i+k]=current[i+k]+(fittedPoint[k]-oldFit[k])*(corrective?-1:1);
            if(blink){const center=centers[sign],dx=out[i]-center[0],dy=out[i+1]-center[1],inside=1-(dx/radii[sign][0])**2-(dy/radii[sign][1])**2;const bx=(Math.abs(base[i])-.0302)/.014,by=(base[i+1]-1.4621)/.015,outer=.1208+.012*Math.sqrt(Math.max(0,1-bx*bx-by*by));if(inside>0){const cover=center[2]+radii[sign][2]*Math.sqrt(inside)+(mesh.name==='Lashes'?.0006:0);out[i+2]+=Math.max(0,cover-out[i+2])*Math.max(smooth(outer-.0032,outer+.0002,base[i+2]),smooth(.5,.7,g.attributes.normal.array[i+2]));}}
          }else if(target>=2&&target<6){
            const center=centers[sign],horizontal=target===2?1:target===3?-1:0,vertical=target===4?1:target===5?-1:0,angle=(horizontal?horizontal*11.85:vertical*-7.9)*Math.PI/180,c=Math.cos(angle),s=Math.sin(angle),x=current[i]-center[0],y=current[i+1]-center[1],z=current[i+2]-center[2];
            if(horizontal){out[i]=center[0]+x*c+z*s;out[i+2]=center[2]-x*s+z*c;}else{out[i+1]=center[1]+y*c-z*s;out[i+2]=center[2]+y*s+z*c;}
          }
        }
        const position=g.morphAttributes.position[count+target],normal=g.morphAttributes.normal[count+target],n1=target>=6?null:normals(g,out);
        for(let i=0;i<out.length;i++){position.array[i]=out[i]-current[i];normal.array[i]=target>=6?(isLid&&base[i-i%3]*(target<8?1:-1)>0?-g.morphAttributes.normal[count+(target%2===0?4:5)].array[i]:0):n1[i]-n0[i];}position.needsUpdate=true;normal.needsUpdate=true;
      }
      // Three packs morphs into a GPU texture keyed by count, not attribute version.
      // Invalidate that cache after fitting a new identity, then reuse the geometry.
      g.dispose();
    }
  }
  function update(project){const key=JSON.stringify(Object.keys(manifest.morphs).map(k=>project[k]??.5));if(key!==identityKey){rebuild(project);identityKey=key;}
    const h=clamp(project.gazeHorizontal??0,-1,1),v=clamp(project.gazeVertical??0,-1,1),weights=[clamp(project.blinkLeft??0,0,1),clamp(project.blinkRight??0,0,1),Math.max(0,-h),Math.max(0,h),Math.max(0,v),Math.max(0,-v)];
    weights.push(weights[0]*weights[4],weights[0]*weights[5],weights[1]*weights[4],weights[1]*weights[5]);
    for(const {mesh,count}of entries)for(let i=0;i<weights.length;i++)mesh.morphTargetInfluences[count+i]=weights[i];
  }
  return{update,targets:EYE_TARGETS};
}
