// Smooth, depth-tested preview. All geometry remains original and local.
export function frameCharacter(faces,width,height,yaw,focus='body'){
  const source=focus==='face'?faces.filter(f=>['head','hair','ear','neck'].includes(f.part)):faces;
  const c=Math.cos(yaw),s=Math.sin(yaw);let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity;
  for(const face of source)for(const v of face.v){const x=v[0]*c+v[2]*s;minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,v[1]);maxY=Math.max(maxY,v[1]);}
  const top=70,bottom=focus==='face'?160:140,space=Math.max(120,height-top-bottom);
  const scale=Math.min((width-72)/Math.max(maxX-minX,.1),space/Math.max(maxY-minY,.1));
  return {scale,center:[(minX+maxX)/2,(minY+maxY)/2-(bottom-top)/2/scale,0]};
}
const vertexShader=`
attribute vec3 position; attribute vec3 normal; attribute vec3 color;
uniform vec2 viewport; uniform float scale; uniform float yaw; uniform vec3 center;
varying vec3 vNormal; varying vec3 vColor; varying vec3 world;
void main(){float c=cos(yaw),s=sin(yaw);mat3 turn=mat3(c,0.,-s,0.,1.,0.,s,0.,c);
 vec3 p=turn*position; vNormal=normalize(turn*normal);vColor=color;world=p;
 gl_Position=vec4((p.x-center.x)*scale*2./viewport.x,(p.y-center.y)*scale*2./viewport.y,-p.z/10.,1.);
}`;
const fragmentShader=`
precision mediump float; varying vec3 vNormal; varying vec3 vColor; varying vec3 world;
void main(){vec3 n=normalize(vNormal);float key=max(dot(n,normalize(vec3(-.6,.9,1.4))),0.);
float fill=max(dot(n,normalize(vec3(.9,.2,.4))),0.);
float rim=pow(1.-abs(n.z),3.)*.09;
vec3 lit=vColor*(.54+.39*key+.12*fill)+vec3(rim);
gl_FragColor=vec4(lit,1.);
}`;
export function createRenderer(canvas){
  const gl=canvas.getContext('webgl',{alpha:true,antialias:true,preserveDrawingBuffer:true});
  if(!gl)return createSoftwareRenderer(canvas);
  const compile=(type,source)=>{const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(shader));return shader;};
  const program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,vertexShader));gl.attachShader(program,compile(gl.FRAGMENT_SHADER,fragmentShader));gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
  const buffer=gl.createBuffer(),uniforms=Object.fromEntries(['viewport','scale','yaw','center'].map(name=>[name,gl.getUniformLocation(program,name)]));
  let previous=null,count=0;
  return {render(faces,yaw,focus='body'){
    if(gl.isContextLost())throw Error('The graphics context was lost. Reload to restore the preview; saved projects are unchanged.');
    const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2),w=rect.width,h=rect.height;
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    gl.viewport(0,0,canvas.width,canvas.height);gl.clearColor(.914,.929,.894,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);gl.useProgram(program);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    if(previous!==faces){const data=[];for(const face of faces){const color=face.color.match(/\w\w/g).map(v=>parseInt(v,16)/255);face.v.forEach((v,i)=>data.push(...v,...face.normals[i],...color));}gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.STATIC_DRAW);count=faces.length*3;previous=faces;}
    for(const [i,name] of ['position','normal','color'].entries()){const location=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,3,gl.FLOAT,false,36,i*12);}
    const framing=frameCharacter(faces,w,h,yaw,focus);gl.uniform2f(uniforms.viewport,w,h);gl.uniform1f(uniforms.scale,framing.scale);gl.uniform1f(uniforms.yaw,yaw);gl.uniform3fv(uniforms.center,framing.center);gl.drawArrays(gl.TRIANGLES,0,count);canvas.dataset.renderer='webgl';
  }};
}

// A depth buffer and interpolated lighting keep the same geometry usable on
// browsers without WebGL. Unlike painter sorting this handles intersecting parts.
function createSoftwareRenderer(canvas){
  const context=canvas.getContext('2d');
  if(!context)throw Error('A canvas preview is unavailable in this browser. Your project is unchanged.');
  return {render(faces,yaw,focus='body'){
    const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,1.5),width=Math.round(rect.width*dpr),height=Math.round(rect.height*dpr);
    canvas.width=width;canvas.height=height;
    const framing=frameCharacter(faces,rect.width,rect.height,yaw,focus),scale=framing.scale*dpr;
    const output=context.createImageData(width,height),pixels=output.data,depth=new Float32Array(width*height);depth.fill(-Infinity);
    for(let i=0;i<pixels.length;i+=4){pixels[i]=233;pixels[i+1]=237;pixels[i+2]=228;pixels[i+3]=255;}
    const c=Math.cos(yaw),s=Math.sin(yaw),colors=new Map();
    const turn=v=>[v[0]*c+v[2]*s,v[1],v[2]*c-v[0]*s];
    const shade=n=>{const q=turn(n);return .54+.39*Math.max(0,(-.6*q[0]+.9*q[1]+1.4*q[2])/1.769)+.12*Math.max(0,(.9*q[0]+.2*q[1]+.4*q[2])/1.005);};
    for(const face of faces){
      const v=face.v.map(turn).map(q=>[width/2+(q[0]-framing.center[0])*scale,height/2-(q[1]-framing.center[1])*scale,q[2]]);
      const [a,b,c]=v,den=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
      if(den>=-1e-8)continue;
      const x0=Math.max(0,Math.floor(Math.min(a[0],b[0],c[0]))),x1=Math.min(width-1,Math.ceil(Math.max(a[0],b[0],c[0]))),y0=Math.max(0,Math.floor(Math.min(a[1],b[1],c[1]))),y1=Math.min(height-1,Math.ceil(Math.max(a[1],b[1],c[1])));
      if(x0>x1||y0>y1)continue;
      if(!colors.has(face.color))colors.set(face.color,face.color.match(/\w\w/g).map(v=>parseInt(v,16)));
      const rgb=colors.get(face.color),light=face.normals.map(shade);
      for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){
        const dx=x+.5-a[0],dy=y+.5-a[1],u=(dx*(c[1]-a[1])-dy*(c[0]-a[0]))/den,w=((b[0]-a[0])*dy-(b[1]-a[1])*dx)/den,t=1-u-w;
        if(u<0||w<0||t<0)continue;
        const z=t*a[2]+u*b[2]+w*c[2],index=y*width+x;if(z<=depth[index])continue;
        depth[index]=z;const l=t*light[0]+u*light[1]+w*light[2],offset=index*4;
        pixels[offset]=rgb[0]*l;pixels[offset+1]=rgb[1]*l;pixels[offset+2]=rgb[2]*l;
      }
    }
    context.putImageData(output,0,0);canvas.dataset.renderer='software-depth';
  }};
}
