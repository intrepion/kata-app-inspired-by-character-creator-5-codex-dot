import * as T from '../vendor/three.module.min.js';

// Original MIT short groom. Deterministic, static, and ordinary skinned glTF
// triangles: no simulation, proprietary hair asset, or browser-only shader.
export const HAIR_SEED=240611;
export const HAIR_LIMIT='Static clump-and-fiber crop, not strand simulation. Directional highlights use KHR_materials_anisotropy; viewers without it retain the PBR geometry and color.';
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const smooth=(a,b,v)=>{const t=clamp((v-a)/(b-a));return t*t*(3-2*t);};
function random(seed){return()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};}
const V=(x=0,y=0,z=0)=>new T.Vector3(x,y,z);

function scalpSurface(cap){
  const g=cap.geometry,p=g.attributes.position,n=g.attributes.normal,uv=g.attributes.uv,indices=g.index.array,triangles=[],edges=new Map();let area=0;
  for(let i=0;i<indices.length;i+=3){
    const ids=Array.from(indices.slice(i,i+3)),points=ids.map(j=>V().fromBufferAttribute(p,j)),tri=new T.Triangle(...points),weight=tri.getArea();area+=weight;triangles.push({ids,tri,area});
    for(let j=0;j<3;j++){const a=ids[j],b=ids[(j+1)%3],key=[a,b].sort((a,b)=>a-b).join(',');const edge=edges.get(key)||{a,b,count:0};edge.count++;edges.set(key,edge);}
  }
  // The original UV seam is a geometry split, so weld by position before
  // classifying its boundary. It must not become a false rear hairline.
  const keyed=new Map();for(const e of edges.values()){const key=[e.a,e.b].map(i=>[p.getX(i),p.getY(i),p.getZ(i)].map(v=>v.toFixed(6)).join(',')).sort().join('|');const all=keyed.get(key)||{...e,count:0};all.count+=e.count;keyed.set(key,all);}
  const boundary=[...keyed.values()].filter(e=>e.count===1),points=[...new Set(boundary.flatMap(e=>[e.a,e.b]))].map(i=>({i,u:uv.getX(i),y:p.getY(i)})).sort((a,b)=>a.u-b.u);
  function boundaryY(u){u=(u%1+1)%1;let right=points.findIndex(p=>p.u>=u);if(right===-1)right=0;const b=points[right],a=points[(right+points.length-1)%points.length];let au=a.u,bu=b.u;if(au>bu){if(u<bu)au-=1;else bu+=1;}return a.y+(b.y-a.y)*clamp((u-au)/(bu-au||1));}
  const bary=V(),nearest=V(),no=V();
  function sample(triangle,weights){const point=V();no.set(0,0,0);triangle.ids.forEach((id,j)=>{point.addScaledVector(V().fromBufferAttribute(p,id),weights[j]);no.addScaledVector(V().fromBufferAttribute(n,id),weights[j]);});return{point,normal:no.clone().normalize(),ids:triangle.ids,weights};}
  function nearestPoint(point){let best,dist=Infinity;for(const triangle of triangles){triangle.tri.closestPointToPoint(point,nearest);const d=point.distanceToSquared(nearest);if(d<dist){dist=d;best=triangle;}}best.tri.closestPointToPoint(point,nearest);best.tri.getBarycoord(nearest,bary);return sample(best,[bary.x,bary.y,bary.z]);}
  function pick(r){const target=r()*area,triangle=triangles.find(t=>t.area>=target)||triangles.at(-1),a=Math.sqrt(r()),b=r();return sample(triangle,[1-a,a*(1-b),a*b]);}
  return{pick,nearestPoint,boundaryY,boundary,position:p,normal:n,uv};
}

// Crown sweeps diagonally back, the whorl turns gently, sides and nape lie
// downward. Growth is continuous between these regions rather than upright.
export function growthDirection(point,normal){
  const top=smooth(1.505,1.554,point.y),back=1-smooth(-.025,.055,point.z);
  const crown=V(.65,.04,-.85),side=V(Math.sign(point.x)*.14,-.95,-.34);
  const front=smooth(.075,.12,point.z)*smooth(1.49,1.525,point.y)*(1-top*.4);
  const flow=side.lerp(crown,top).lerp(V(.4,.9,-.45),front);flow.x+=back*top*(point.z+.005)*9;flow.z-=back*top*point.x*6;
  flow.addScaledVector(normal,-flow.dot(normal));
  if(flow.lengthSq()<1e-8)flow.set(.7,0,-.7).addScaledVector(normal,-flow.dot(normal));
  return flow.normalize();
}

// A two-edge fiber carries cylindrical normals rather than a flat card normal.
// Interpolation across its width produces a narrow, direction-dependent sheen.
function fiberNormals(geometry){
  geometry.computeVertexNormals();const p=geometry.attributes.position,n=geometry.attributes.normal,side=V();
  for(let i=0;i<p.count;i+=2){side.fromBufferAttribute(p,i+1).sub(V().fromBufferAttribute(p,i)).normalize();for(let k=0;k<2;k++){const normal=V().fromBufferAttribute(n,i+k).multiplyScalar(.52).addScaledVector(side,k===0?-.854:.854).normalize();n.setXYZ(i+k,normal.x,normal.y,normal.z);}}
}
export function buildHairGeometry(cap){
  const surface=scalpSurface(cap),r=random(HAIR_SEED),positions=[],uvs=[],colors=[],indices=[],skinIndices=[],skinWeights=[],fits=[],guides=[];
  const stats={seed:HAIR_SEED,clumps:0,fibers:0,flyaways:0,hairlineFibers:0};
  function vertex(point,fit,u,v,tone){positions.push(...point.toArray());uvs.push(u,v);colors.push(tone,tone,tone);fits.push(fit);const weight=new Map();fit.ids.forEach((id,k)=>{for(let j=0;j<4;j++){const bone=cap.geometry.attributes.skinIndex.array[id*4+j],w=cap.geometry.attributes.skinWeight.array[id*4+j]*fit.weights[k];weight.set(bone,(weight.get(bone)||0)+w);}});const keep=[...weight].sort((a,b)=>b[1]-a[1]).slice(0,4),sum=keep.reduce((a,[,w])=>a+w,0);for(let j=0;j<4;j++){skinIndices.push(keep[j]?.[0]||0);skinWeights.push((keep[j]?.[1]||0)/sum);}}
  function ribbon(root,length,width,lift,twist,tone,wide=false){
    const start=positions.length/3,flow=growthDirection(root.point,root.normal),side=V().crossVectors(flow,root.normal).normalize(),steps=wide?6:5,columns=wide?3:2;
    const variation=(r()-.5)*.3;flow.addScaledVector(side,variation).normalize();
    for(let j=0;j<=steps;j++){
      const t=j/steps,target=root.point.clone().addScaledVector(flow,length*t).addScaledVector(side,twist*Math.sin(t*Math.PI*.8));
      const fit=surface.nearestPoint(target),height=.00018+lift*Math.sin(Math.PI*t*.83)+length*.03*t;
      // At edges the tip may leave the scalp by at most 2.5mm. This avoids
      // snapping an entire guide into a boundary ridge.
      const excess=target.clone().sub(fit.point);excess.addScaledVector(fit.normal,-excess.dot(fit.normal));if(excess.length()>.0025)excess.setLength(.0025);
      const center=fit.point.clone().add(excess).addScaledVector(fit.normal,height),taper=Math.pow(1-t,.7)*(.55+.45*Math.sin(Math.PI*Math.min(1,t*2)))+.018;
      const tangent=flow.clone().addScaledVector(fit.normal,-flow.dot(fit.normal)).normalize(),across=V().crossVectors(tangent,fit.normal).normalize();
      for(let k=0;k<columns;k++){const s=k/(columns-1)*2-1,p=center.clone().addScaledVector(across,width*taper*s);if(wide)p.addScaledVector(fit.normal,(1-Math.abs(s))*width*.42);vertex(p,fit,wide?k/(columns-1):.49+k/(columns-1)*.02,t,tone*(.84+.16*smooth(0,.3,t)));}
      if(j)for(let k=0;k<columns-1;k++){const a=start+(j-1)*columns+k,b=a+columns;indices.push(a,a+1,b,a+1,b+1,b);}
    }
  }
  for(let i=0;i<700;i++){
    let root=surface.pick(r);const top=smooth(1.485,1.535,root.point.y),u=Math.atan2(root.point.x,root.point.z-.04)/(2*Math.PI)+.5;
    const edge=root.point.y-surface.boundaryY(u);if(edge<.0015&&r()>.22){i--;continue;}
    const length=(.0045+r()*.006)*(1-top)+(.022+r()*.015)*top,width=(.00055+r()*.0006)*(1-top)+(.0008+r()*.0008)*top,lift=(.0005+r()*.0006)*(1-top)+(.008+r()*.005)*top,twist=(r()-.5)*.003,tone=.62+r()*.30;
    guides.push({root,length,width,lift,twist});stats.clumps++;
    const flow=growthDirection(root.point,root.normal),side=V().crossVectors(flow,root.normal).normalize();
    for(let j=0;j<5;j++){const offset=(j-2)*width*.55+(r()-.5)*width*.5,fit=surface.nearestPoint(root.point.clone().addScaledVector(side,offset));ribbon(fit,length*(.8+r()*.3),.00010+r()*.00008,lift*(.80+r()*.35)+.00022,twist,.64+r()*.36);stats.fibers++;}
  }
  for(let i=0;i<60;i++){const guide=guides[Math.floor(r()*guides.length)];if(guide.root.point.y<1.51){i--;continue;}ribbon(guide.root,guide.length*(.8+r()*.4),.000045+r()*.000035,guide.lift+.002+r()*.0035,guide.twist+(r()-.5)*.004,.7+r()*.22);stats.flyaways++;}
  // Explicit short perimeter fibers soften the hairline instead of a broad
  // randomized stipple. They share head weights and every identity target.
  for(const edge of surface.boundary){const a=V().fromBufferAttribute(surface.position,edge.a),b=V().fromBufferAttribute(surface.position,edge.b);const count=Math.max(2,Math.ceil(a.distanceTo(b)/.00085));for(let j=0;j<count;j++){const t=(j+r())/count,fit=surface.nearestPoint(a.clone().lerp(b,t)),n=fit.normal,inside=V(0,1,0).addScaledVector(n,-n.y).normalize();fit.point.addScaledVector(inside,(r()-.3)*.0011);ribbon(fit,.002+r()*.0035,.000045+r()*.00004,.0002+r()*.00035,(r()-.5)*.0004,.7+r()*.25);stats.hairlineFibers++;}}
  const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(positions,3));g.setAttribute('uv',new T.Float32BufferAttribute(uvs,2));g.setAttribute('color',new T.Float32BufferAttribute(colors,3));g.setAttribute('skinIndex',new T.Uint16BufferAttribute(skinIndices,4));g.setAttribute('skinWeight',new T.Float32BufferAttribute(skinWeights,4));g.setIndex(indices);fiberNormals(g);g.morphTargetsRelative=true;g.morphAttributes.position=[];g.morphAttributes.normal=[];
  // Transport each section with its actual scalp triangle. Roots and tips
  // follow differing identity deformations, with recomputed portable normals.
  for(const original of cap.geometry.morphAttributes.position||[]){const out=new Float32Array(positions.length);fits.forEach((fit,i)=>{for(let k=0;k<3;k++)out[i*3+k]=fit.ids.reduce((sum,id,j)=>sum+original.array[id*3+k]*fit.weights[j],0);});const p=new T.Float32BufferAttribute(out,3);p.name=original.name;g.morphAttributes.position.push(p);
    const shape=new T.BufferGeometry();shape.setIndex(g.index);shape.setAttribute('position',new T.Float32BufferAttribute(out.map((v,i)=>v+positions[i]),3));fiberNormals(shape);const normal=new T.Float32BufferAttribute(shape.attributes.normal.array.map((v,i)=>v-g.attributes.normal.array[i]),3);normal.name=original.name;g.morphAttributes.normal.push(normal);shape.dispose();}
  g.computeBoundingSphere();g.userData={hairGroom:{...stats,triangles:indices.length/3}};return{geometry:g,stats:g.userData.hairGroom,surface};
}

function underlayTexture(surface){
  const size=2048,data=new Uint8Array(size*size*4),r=random(46183),roots=Float32Array.from({length:size},()=>.0004+.0018*r()**2),edges=Array.from({length:size},(_,x)=>surface.boundaryY((x+.5)/size));
  for(let y=0;y<size;y++)for(let x=0;x<size;x++){
    const u=(x+.5)/size,v=(y+.5)/size,height=1.44+(1-v)*.14,edge=edges[x],phase=u*580+v*30+Math.sin(v*13+u*9)*.4,stripe=Math.sin(phase*Math.PI*2),micro=Math.sin(u*2391+v*63);
    const coverage=smooth(roots[x],roots[x]+.010,height-edge);
    const value=Math.round(255*clamp(.49+.075*stripe+.025*micro+.11*Math.sin(u*2*Math.PI*83+v*29+Math.sin(v*8)*.4),.2,.8)),offset=(y*size+x)*4;data[offset]=data[offset+1]=data[offset+2]=value;data[offset+3]=r()<coverage?255:0;
  }
  const texture=new T.DataTexture(data,size,size,T.RGBAFormat);texture.name='OriginalCropRootAtlas';texture.colorSpace=T.SRGBColorSpace;texture.flipY=false;texture.magFilter=T.LinearFilter;texture.minFilter=T.LinearMipmapLinearFilter;texture.generateMipmaps=true;texture.needsUpdate=true;return texture;
}

// UV triangles crossing the rear wrap must interpolate locally, not through
// the frontal hairline mask. Duplicate corners at the wrap, preserving every
// position, normal, skin weight and identity delta from the source vertex.
export function seamScalpGeometry(source){
  const g=new T.BufferGeometry(),ids=source.index.array;
  for(const [name,a]of Object.entries(source.attributes)){const out=new a.array.constructor(ids.length*a.itemSize);for(let i=0;i<ids.length;i++)for(let j=0;j<a.itemSize;j++)out[i*a.itemSize+j]=a.array[ids[i]*a.itemSize+j];g.setAttribute(name,new T.BufferAttribute(out,a.itemSize,a.normalized));}
  const uv=g.attributes.uv;for(let i=0;i<ids.length;i+=3){const u=[uv.getX(i),uv.getX(i+1),uv.getX(i+2)];if(Math.max(...u)-Math.min(...u)>.5)for(let k=0;k<3;k++)if(u[k]<.5)uv.setX(i+k,u[k]+1);const fixed=[uv.getX(i),uv.getX(i+1),uv.getX(i+2)];if(Math.max(...fixed)-Math.min(...fixed)>.5){const crown=[0,1,2].sort((a,b)=>g.attributes.position.getY(i+b)-g.attributes.position.getY(i+a))[0],others=[0,1,2].filter(k=>k!==crown);uv.setX(i+crown,(fixed[others[0]]+fixed[others[1]])/2);}}
  g.setIndex(Array.from({length:ids.length},(_,i)=>i));g.morphTargetsRelative=true;
  for(const [name,list]of Object.entries(source.morphAttributes))g.morphAttributes[name]=list.map(a=>{const out=new Float32Array(ids.length*a.itemSize);for(let i=0;i<ids.length;i++)for(let j=0;j<a.itemSize;j++)out[i*a.itemSize+j]=a.array[ids[i]*a.itemSize+j];const result=new T.Float32BufferAttribute(out,a.itemSize);result.name=a.name;return result;});
  return g;
}

export function createHairGroom({human}){
  const cap=human.getObjectByName('HairCrop'),oldStrands=human.getObjectByName('HairStrands');if(!cap||!oldStrands)throw Error('Short groom requires the retained scalp and baseline strands');
  const started=performance.now(),{geometry,stats,surface}=buildHairGeometry(cap),baseline=cap.material,baselineGeometry=cap.geometry,rootGeometry=seamScalpGeometry(cap.geometry);
  const underlay=baseline.clone();underlay.name='Hair';underlay.map=underlayTexture(surface);underlay.map.wrapS=T.RepeatWrapping;underlay.alphaTest=.5;underlay.alphaToCoverage=true;underlay.transparent=false;underlay.roughness=.70;underlay.roughnessMap=null;underlay.userData={...baseline.userData,hairGroom:{version:1,role:'close scalp underlay'}};
  const material=new T.MeshPhysicalMaterial({name:'HairGroom',color:0xffffff,vertexColors:true,roughness:.48,metalness:0,anisotropy:.7,anisotropyRotation:Math.PI/2,specularIntensity:.65,side:T.DoubleSide});material.envMapIntensity=.65;material.userData={baseColor:material.color.clone(),hairTransferLimit:HAIR_LIMIT};
  const mesh=new T.SkinnedMesh(geometry,material);mesh.name='HairGroom';mesh.userData={role:'hair',hairGroom:{version:1,...stats,static:true,license:'MIT',transferLimit:HAIR_LIMIT}};mesh.position.copy(cap.position);mesh.quaternion.copy(cap.quaternion);mesh.scale.copy(cap.scale);mesh.bind(cap.skeleton,cap.bindMatrix);mesh.morphTargetDictionary={...cap.morphTargetDictionary};mesh.castShadow=true;mesh.receiveShadow=false;mesh.frustumCulled=false;cap.parent.add(mesh);
  let preview='groom';
  function update(project){const enabled=project.hair!=='none';cap.visible=enabled;cap.material=preview==='baseline'?baseline:underlay;cap.geometry=preview==='baseline'?baselineGeometry:rootGeometry;cap.material.color.set(project.hairColor);oldStrands.visible=enabled&&preview==='baseline';mesh.visible=enabled&&preview==='groom';mesh.material.color.set(project.hairColor);}
  return{mesh,stats:{...stats,buildMilliseconds:performance.now()-started},update,setPreview(mode){if(!['baseline','groom'].includes(mode))throw Error('Unknown hair preview');preview=mode;},dispose(){baselineGeometry.dispose();rootGeometry.dispose();for(const texture of new Set([...Object.values(baseline),...Object.values(underlay)].filter(v=>v?.isTexture)))texture.dispose();underlay.dispose();baseline.dispose();}};
}
