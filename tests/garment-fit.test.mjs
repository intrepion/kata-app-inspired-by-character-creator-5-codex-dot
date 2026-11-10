import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const bytes=readFileSync(process.env.GARMENT_TEST_GLB || new URL('../assets/human/foundation.glb',import.meta.url));
const jsonLength=bytes.readUInt32LE(12),gltf=JSON.parse(bytes.subarray(20,20+jsonLength)),binary=bytes.subarray(28+jsonLength);
function attribute(id){const a=gltf.accessors[id],n={SCALAR:1,VEC2:2,VEC3:3,VEC4:4}[a.type],sizes={5121:1,5123:2,5125:4,5126:4},size=sizes[a.componentType];const data=new Array(a.count*n).fill(0),read=(at,type)=>type===5126?binary.readFloatLE(at):type===5125?binary.readUInt32LE(at):type===5123?binary.readUInt16LE(at):binary.readUInt8(at);if(a.bufferView!==undefined){const v=gltf.bufferViews[a.bufferView];for(let i=0;i<a.count;i++)for(let c=0;c<n;c++)data[i*n+c]=read((v.byteOffset||0)+(a.byteOffset||0)+i*(v.byteStride||n*size)+c*size,a.componentType);}if(a.sparse){const sp=a.sparse,iv=gltf.bufferViews[sp.indices.bufferView],vv=gltf.bufferViews[sp.values.bufferView];for(let k=0;k<sp.count;k++){const i=read((iv.byteOffset||0)+(sp.indices.byteOffset||0)+k*sizes[sp.indices.componentType],sp.indices.componentType);for(let c=0;c<n;c++)data[i*n+c]=read((vv.byteOffset||0)+(sp.values.byteOffset||0)+(k*n+c)*size,a.componentType);}}return data;}
function mesh(name,build,shoulders){const m=gltf.meshes[gltf.nodes.find(n=>n.name===name&&n.mesh!==undefined)?.mesh]||gltf.meshes.find(m=>m.name===name),p=m.primitives[0],vertices=attribute(p.attributes.POSITION),indices=attribute(p.indices);for(const [control,value] of [['Build',build],['Shoulders',shoulders]]){const target=m.extras.targetNames.indexOf(control+(value<.5?'Narrow':'Broad'));const delta=attribute(p.targets[target].POSITION),weight=Math.abs(value-.5)*2;for(let i=0;i<vertices.length;i++)vertices[i]+=delta[i]*weight;}return{vertices,indices};}
// Horizontal cross-sections avoid vague image thresholds: an untucked shirt must
// form one complete surface outside the trousers throughout their overlap.
function radiusAt(mesh,y,angle){const {vertices:v,indices}=mesh,c=Math.cos(angle),s=Math.sin(angle),radii=[];for(let i=0;i<indices.length;i+=3){const points=[];for(let k=0;k<3;k++){const a=indices[i+k]*3,b=indices[i+(k+1)%3]*3,dy=v[b+1]-v[a+1];if(Math.abs(dy)<1e-9)continue;const t=(y-v[a+1])/dy;if(t<0||t>=1)continue;points.push([v[a]+t*(v[b]-v[a]),v[a+2]+t*(v[b+2]-v[a+2])]);}if(points.length!==2)continue;const [[ax,az],[bx,bz]]=points,dx=bx-ax,dz=bz-az,den=c*dz-s*dx;if(Math.abs(den)<1e-10)continue;const r=(ax*dz-az*dx)/den,t=(ax*s-az*c)/den;if(r>0&&t>=-1e-6&&t<=1+1e-6)radii.push(r);}return radii.length?Math.max(...radii):null;}
test('shirt remains outside trousers around the entire waist for the full build range',()=>{let minimum=Infinity,where='';for(let step=0;step<=100;step++){const build=step/100;for(const shoulders of [0,.5,1]){const shirt=mesh('Outfit',build,shoulders),pants=mesh('Pants',build,shoulders);for(const y of [.959,.965,.971])for(let degree=0;degree<360;degree+=10){const angle=degree*Math.PI/180,outer=radiusAt(shirt,y,angle),inner=radiusAt(pants,y,angle);assert.notEqual(outer,null,`Missing shirt at ${degree}°`);assert.notEqual(inner,null,`Missing pants at ${degree}°`);if(outer-inner<minimum){minimum=outer-inner;where=`build ${build}, shoulders ${shoulders}, y ${y}, angle ${degree}`;}}}}assert.ok(minimum>=.002,`Waist surfaces intersect or almost touch: clearance ${minimum.toFixed(5)}m at ${where}`);});

// Inspect the exported triangles themselves, not just radial intersections. The
// latter skip horizontal faces and previously missed folded, coplanar hem rows.
const subtract=(a,b)=>a.map((x,i)=>x-b[i]);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a.reduce((sum,x,i)=>sum+x*b[i],0);
function hemTriangles(build,shoulders){
  const {vertices,indices}=mesh('Outfit',build,shoulders),triangles=[];
  for(let i=0;i<indices.length;i+=3){
    const points=indices.slice(i,i+3).map(index=>vertices.slice(index*3,index*3+3));
    // This lower-torso band excludes sleeves and other non-radial garment parts.
    if(points.some(p=>p[1]<.94||p[1]>1.015))continue;
    const normal=cross(subtract(points[1],points[0]),subtract(points[2],points[0]));
    triangles.push({index:i/3,points,normal,area:Math.hypot(...normal)/2});
  }
  assert.ok(triangles.length>30,'Expected actual lower-shirt topology in the waist band');
  return triangles;
}
const waistShapes=Array.from({length:5},(_,i)=>i/4).flatMap(build=>[0,.5,1].map(shoulders=>({build,shoulders})));
const shapeLabel=({build,shoulders})=>`build ${build}, shoulders ${shoulders}`;
// 1e-10 m² is 0.0001 mm²: far below any intentional garment face, but above
// floating-point dust left by GLB export of collapsed source triangles.
const minimumHemArea=1e-10;
test('exported hem has no collapsed triangles across build and shoulder morphs',()=>{
  const failures=[];
  for(const shape of waistShapes){
    const bad=hemTriangles(shape.build,shape.shoulders).filter(t=>t.area<=minimumHemArea);
    if(bad.length)failures.push(`${shapeLabel(shape)}: ${bad.length} collapsed faces (first ${bad[0].index}, area ${bad[0].area} m²)`);
  }
  assert.deepEqual(failures,[],'The hem must retain nonzero surface area:\n'+failures.join('\n'));
});
test('lower-shirt face normals point outward rather than folding into a horizontal shelf',()=>{
  const failures=[];
  for(const shape of waistShapes){
    const bad=hemTriangles(shape.build,shape.shoulders).filter(t=>{
      if(t.area<=minimumHemArea)return false; // Reported independently above.
      const center=t.points[0].map((_,i)=>t.points.reduce((sum,p)=>sum+p[i],0)/3);
      const outward=[center[0],0,center[2]];
      const cosine=dot(t.normal,outward)/(Math.hypot(...t.normal)*Math.hypot(...outward));
      // A torso shell has positive radial orientation. This near-zero tolerance
      // rejects reversed or exactly horizontal rows, not an artistic silhouette.
      return cosine<=1e-6;
    });
    if(bad.length)failures.push(`${shapeLabel(shape)}: ${bad.length} non-outward faces (first ${bad[0].index})`);
  }
  assert.deepEqual(failures,[],'Lower hem faces must form an outward shell:\n'+failures.join('\n'));
});
function strictlyInsideTriangle(point,triangle){
  // The point must lie strictly inside all three oriented edges. Shared edges
  // and vertices are legal and excluded by a metric 1e-8 m tolerance.
  const normal=triangle.normal.map(v=>v/Math.hypot(...triangle.normal));
  return triangle.points.every((a,i)=>{
    const edge=subtract(triangle.points[(i+1)%3],a);
    return dot(cross(edge,subtract(point,a)),normal)>1e-8*Math.hypot(...edge);
  });
}
function overlapsCoplanar(a,b){
  if(a.area<=minimumHemArea||b.area<=minimumHemArea)return false;
  const normal=a.normal.map(v=>v/Math.hypot(...a.normal));
  // Plane tolerance is 0.1 micrometre, not the millimetre garment clearance.
  if(b.points.some(p=>Math.abs(dot(normal,subtract(p,a.points[0])))>1e-7))return false;
  const center=t=>t.points[0].map((_,i)=>t.points.reduce((sum,p)=>sum+p[i],0)/3);
  return strictlyInsideTriangle(center(a),b)||strictlyInsideTriangle(center(b),a);
}
test('exported hem has no coplanar faces covering the same surface interior',()=>{
  const failures=[];
  for(const shape of waistShapes){
    const triangles=hemTriangles(shape.build,shape.shoulders),overlaps=[];
    for(let i=0;i<triangles.length;i++)for(let j=i+1;j<triangles.length;j++){
      if(overlapsCoplanar(triangles[i],triangles[j]))overlaps.push([triangles[i].index,triangles[j].index]);
    }
    if(overlaps.length)failures.push(`${shapeLabel(shape)}: ${overlaps.length} overlapping face pairs (first ${overlaps[0].join('/')})`);
  }
  assert.deepEqual(failures,[],'Coplanar overlap causes depth ambiguity even when trouser clearance passes:\n'+failures.join('\n'));
});
