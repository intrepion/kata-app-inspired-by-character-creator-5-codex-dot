export const defaults={version:1,name:'Juniper',height:1,shoulders:1,torso:1,head:1,arms:1,legs:1,skin:'#ba805e',outfit:'#d97842',pants:'#3b5550',hairColor:'#313c34',hair:'crop',pose:'relaxed',yaw:0.32};
export const ranges={height:[.75,1.3],shoulders:[.65,1.4],torso:[.65,1.35],head:[.7,1.35],arms:[.7,1.3],legs:[.7,1.3]};
export const presets={explorer:{...defaults},pilot:{...defaults,name:'Orion',height:1.12,shoulders:1.2,head:.9,skin:'#805339',outfit:'#e3d0a7',pants:'#3b4c5e',hair:'none'},botanist:{...defaults,name:'Fern',height:.91,torso:.84,head:1.1,skin:'#e0b492',outfit:'#5f8073',pants:'#c5b48f',hair:'bob',hairColor:'#654334'}};
export function validate(x){if(!x||x.version!==1)throw Error('Not a Persona Forge project.');const p={...defaults};if(typeof x.name!=='string'||!x.name.trim()||x.name.length>60)throw Error('Character name must be 1–60 characters.');p.name=x.name.trim();for(const [k,[a,b]] of Object.entries(ranges)){if(typeof x[k]!=='number'||!Number.isFinite(x[k])||x[k]<a||x[k]>b)throw Error(`Invalid ${k} value.`);p[k]=x[k];}for(const k of ['skin','outfit','pants','hairColor']){if(!/^#[0-9a-f]{6}$/i.test(x[k]))throw Error('Invalid color.');p[k]=x[k];}if(!['crop','bob','none'].includes(x.hair)||!['relaxed','tpose','wave','stride'].includes(x.pose))throw Error('Unknown style or pose.');p.hair=x.hair;p.pose=x.pose;p.yaw=Number.isFinite(x.yaw)?x.yaw:defaults.yaw;return p;}
export class History{constructor(state){this.states=[structuredClone(state)];this.index=0;}push(s){if(JSON.stringify(this.states[this.index])===JSON.stringify(s))return;this.states=this.states.slice(0,this.index+1);this.states.push(structuredClone(s));if(this.states.length>41)this.states.shift();this.index=this.states.length-1;}undo(){if(this.index>0)this.index--;return structuredClone(this.states[this.index]);}redo(){if(this.index<this.states.length-1)this.index++;return structuredClone(this.states[this.index]);}}
// Dimensions use a 3.60-unit adult body, approximately 7.5 heads tall.
// Local lofts provide a jaw, waist and tapered limbs rather than chains of beads.
const sub=(a,b)=>a.map((x,i)=>x-b[i]);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const unit=a=>{const length=Math.hypot(...a)||1;return a.map(v=>v/length);};
const add=(a,b)=>a.map((v,i)=>v+b[i]);
const mul=(a,s)=>a.map(v=>v*s);
export function mesh(p){
  const faces=[];
  function surface(rings,color,part,origin=[0,0,0],axis=[0,1,0],segments=32,deform=null){
    const ey=unit(axis),reference=Math.abs(ey[2])>.9?[1,0,0]:[0,0,1];
    const ex=unit(cross(ey,reference)),ez=unit(cross(ex,ey));
    const vertices=[],indices=[];
    for(const [ringIndex,[y,rx,rz,zc=0]] of rings.entries())for(let j=0;j<segments;j++){
      const theta=j/segments*Math.PI*2;let q=[rx*Math.cos(theta),y,zc+rz*Math.sin(theta)];if(deform)q=deform(q,ringIndex,theta);
      vertices.push(origin.map((v,k)=>(v+ex[k]*q[0]+ey[k]*q[1]+ez[k]*q[2])*(k===1?p.height:1)));
    }
    for(let i=0;i<rings.length-1;i++)for(let j=0;j<segments;j++){
      const a=i*segments+j,b=i*segments+(j+1)%segments,c=a+segments,d=b+segments;
      if(rings[i][1]>0)indices.push([a,c,b]);
      if(rings[i+1][1]>0)indices.push([b,c,d]);
    }
    const normals=vertices.map(()=>[0,0,0]);
    for(const [a,b,c] of indices){const normal=cross(sub(vertices[b],vertices[a]),sub(vertices[c],vertices[a]));for(const i of [a,b,c])normals[i]=add(normals[i],normal);}
    // Duplicate pole vertices share one normal, avoiding a pinwheel at the cap.
    for(const i of [0,rings.length-1])if(rings[i][1]===0){let n=[0,0,0];for(let j=0;j<segments;j++)n=add(n,normals[i*segments+j]);for(let j=0;j<segments;j++)normals[i*segments+j]=n;}
    for(const ids of indices)faces.push({v:ids.map(i=>vertices[i]),normals:ids.map(i=>unit(normals[i])),color,part});
  }
  function ellipsoid(center,scale,color,part,axis=[0,1,0],n=24,m=14){
    const rings=Array.from({length:m+1},(_,i)=>{const a=i/m*Math.PI;return[-Math.cos(a)*scale[1],i===0||i===m?0:Math.sin(a)*scale[0],i===0||i===m?0:Math.sin(a)*scale[2]];});
    surface(rings,color,part,center,axis,n);
  }
  function segment(a,b,r0,r1,color,part,depth=1){
    const length=Math.hypot(...sub(b,a));
    surface([[-.035,0,0],[0,r0*.85,r0*.85*depth],[length*.12,r0,r0*depth],[length*.44,r0*.92,r0*.92*depth],[length*.78,r1*1.12,r1*1.12*depth],[length,r1,r1*depth],[length+.025,0,0]],color,part,a,sub(b,a),24);
  }
  const hip=.18+1.62*p.legs,body=1.16*p.torso,shoulder=hip+body,headY=shoulder+.40*p.head;
  const skin=p.skin,boot='#343a35',trim='#c9b78f';
  surface([[hip-.15,0,0],[hip-.12,.25,.145],[hip+.03,.32,.18],[hip+.14,.30,.17],[hip+.22,.27,.16],[hip+.24,0,0]],p.pants,'pelvis');
  surface([[hip+.08,0,0],[hip+.09,.305*p.shoulders,.172],[hip+body*.22,.285*p.shoulders,.172],[hip+body*.40,.265*p.shoulders,.161],[hip+body*.63,.31*p.shoulders,.185],[hip+body*.80,.365*p.shoulders,.19],[shoulder-.035,.405*p.shoulders,.17],[shoulder+.035,.32*p.shoulders,.14],[shoulder+.095,.14,.10],[shoulder+.10,0,0]],p.outfit,'torso');
  surface([[hip+.08,0,0],[hip+.085,.31*p.shoulders,.176],[hip+.13,.309*p.shoulders,.176],[hip+.135,0,0]],boot,'belt');
  ellipsoid([0,hip+.11,.18],[.055,.029,.012],trim,'buckle');
  ellipsoid([0,shoulder+.12*p.head,-.008],[.087*p.head,.15*p.head,.082*p.head],skin,'neck');
  // Head cross sections from chin to crown: distinct jaw, cheekbones and cranium.
  const headRings=[[-.24,0,0,.035],[-.225,.055,.070,.039],[-.20,.095,.099,.027],[-.15,.130,.128,.008],[-.09,.153,.148,-.005],[-.025,.165,.162,-.012],[.045,.162,.167,-.017],[.115,.162,.163,-.021],[.18,.13,.135,-.025],[.225,.071,.080,-.026],[.24,0,0,-.027]].map(r=>r.map(v=>v*p.head));
  surface(headRings,skin,'head',[0,headY,0],undefined,48);
  const feature=(center,scale,color,part,axis,n=24,m=12)=>ellipsoid([center[0]*p.head,headY+center[1]*p.head,center[2]*p.head],scale.map(v=>v*p.head),color,part,axis,n,m);
  for(const s of [-1,1]){
    feature([s*.164,-.015,-.005],[.029,.059,.027],skin,'ear');
    feature([s*.18,-.017,.014],[.009,.033,.010],'#9a6652','ear-detail');
    // Small almond eyes sit inside skin-colored rims, with a separate upper lid.
    feature([s*.065,.008,.141],[.035,.017,.019],skin,'eyelid');
    feature([s*.065,.010,.159],[.027,.010,.007],'#e8e2d8','eye');
    feature([s*.065,.010,.167],[.009,.0095,.003],'#51645e','iris');
    feature([s*.065,.010,.170],[.004,.006,.002],'#252a26','pupil');
    feature([s*.062,.014,.172],[.002,.002,.001],'#fff9eb','eye-highlight');
    feature([s*.065,.026,.159],[.030,.005,.008],skin,'eyelid');
    feature([s*.065,.045,.145],[.041,.007,.011],p.hairColor,'brow');
    feature([s*.021,-.075,.173],[.021,.014,.017],skin,'nose');
    feature([s*.016,-.084,.186],[.007,.003,.005],'#855645','nostril');
  }
  feature([0,-.030,.163],[.021,.060,.023],skin,'nose');
  feature([0,-.068,.192],[.023,.017,.022],skin,'nose');
  feature([0,-.131,.149],[.041,.005,.010],'#956653','lip');
  feature([0,-.143,.150],[.038,.006,.011],'#b27a64','lip');
  feature([0,-.137,.160],[.038,.002,.002],'#664b41','mouth');
  if(p.hair!=='none'){
    const cap=Array.from({length:15},(_,i)=>{const t=i/14,r=Math.sqrt(1-t*t);return[t*p.head,.171*r*p.head,.178*r*p.head,-.025*p.head];});
    surface(cap,p.hairColor,'hair',[0,headY,0],undefined,48,(q,i,theta)=>{
      const t=i/14,line=.012+.078*Math.max(0,Math.sin(theta))-.105*Math.max(0,-Math.sin(theta));
      const y=(line+(.252-line)*t)*p.head,skullY=y/1.05;
      let section=headRings[headRings.length-1];
      for(let k=1;k<headRings.length;k++)if(skullY<=headRings[k][0]){const a=headRings[k-1],b=headRings[k],u=Math.max(0,(skullY-a[0])/(b[0]-a[0]));section=a.map((v,j)=>v+(b[j]-v)*u);break;}
      const extra=i===14?0:.008*p.head;
      return[(section[1]*1.05+extra)*Math.cos(theta),y,section[3]+(section[2]*1.05+extra)*Math.sin(theta)];
    });
    if(p.hair==='bob'){
      feature([0,-.012,-.10],[.173,.205,.102],p.hairColor,'hair');
      for(const s of [-1,1])feature([s*.148,-.035,-.012],[.042,.175,.13],p.hairColor,'hair');
    }
  }
  for(const s of [-1,1]){
    const thighStart=[s*.174,hip-.04,-.012];
    const ankle=[s*.185,.20,0],knee=[s*.19,.20+.77*p.legs,.025];
    if(p.pose==='stride'){ankle[2]=s*.40;knee[2]=s*.19;}
    segment(thighStart,knee,.158,.104,p.pants,'thigh',1.02);
    ellipsoid(knee,[.105,.12,.108],p.pants,'knee');
    segment(knee,ankle,.11,.067,p.pants,'calf',1.05);
    ellipsoid([ankle[0],.095,ankle[2]+.075],[.093,.095,.205],boot,'shoe',undefined,28);
    segment([ankle[0],.11,ankle[2]],[ankle[0],.28,ankle[2]],.077,.074,boot,'boot');
    const start=[s*.365*p.shoulders,shoulder-.10,0];
    let elbow=[s*(.42*p.shoulders+.09),shoulder-.51*p.arms,.012],wrist=[s*(.43*p.shoulders+.13),shoulder-1.00*p.arms,.05];
    if(p.pose==='tpose'){elbow=[start[0]+s*.51*p.arms,shoulder-.10,0];wrist=[start[0]+s*1.0*p.arms,shoulder-.10,0];}
    if(p.pose==='wave'&&s===1){elbow=[start[0]+.40*p.arms,shoulder+.14*p.arms,0];wrist=[start[0]+.43*p.arms,shoulder+.62*p.arms,.02];}
    if(p.pose==='stride'){elbow[2]=-s*.22;wrist[2]=-s*.37;}
    ellipsoid(start,[.121,.128,.126],p.outfit,'shoulder');
    segment(start,elbow,.133,.089,p.outfit,'upper-arm');
    ellipsoid(elbow,[.091,.10,.091],p.outfit,'elbow');
    segment(elbow,wrist,.092,.054,p.outfit,'forearm');
    const direction=unit(sub(wrist,elbow)),side=unit(cross(direction,[0,0,1]));
    const point=(along,across=0,z=0)=>add(add(add(wrist,mul(direction,along)),mul(side,across)),[0,0,z]);
    ellipsoid(point(.074),[.058,.096,.031],skin,'palm',direction);
    for(let i=0;i<4;i++){
      const x=(i-1.5)*.027,length=[.092,.116,.108,.079][i];
      segment(point(.131,x),point(.131+length,x*1.08,.008),.0135,.010,skin,'finger',.85);
    }
    segment(point(.027,-s*.046),point(.114,-s*.084,.019),.021,.014,skin,'thumb',.90);
  }
  // Tailoring details follow the front surface, rather than floating pockets.
  segment([0,hip+.16,.178],[0,shoulder-.11,.194],.005,.005,trim,'zipper');
  return faces;
}
export function exportOBJ(faces,name){let lines=[`# Persona Forge — ${name.replace(/[\r\n]/g,' ')}`, '# Independent triangle mesh; RGB vertex colors; no skeleton or UVs.','o Persona'];let i=1;for(const f of faces){const rgb=f.color.match(/\w\w/g).map(v=>(parseInt(v,16)/255).toFixed(4));for(const v of f.v)lines.push(`v ${v.map(n=>n.toFixed(6)).join(' ')} ${rgb.join(' ')}`);lines.push(`f ${i} ${i+1} ${i+2}`);i+=3;}return lines.join('\n');}
