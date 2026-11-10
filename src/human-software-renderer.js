import * as THREE from '../vendor/three.module.min.js';

/** CPU rasterization of the loaded human's actual deformed geometry and UV maps.
 * This is a compatibility renderer, not a substitute/procedural character. */
export function createHumanSoftwareRenderer(canvas) {
  const context = canvas.getContext('2d', {alpha: false});
  if (!context) throw new Error('A 2D canvas is required for the compatibility human preview.');
  canvas.dataset.renderer = 'software-human';
  const textures = new WeakMap();
  let width = 1, height = 1, output, depth, disposed = false;
  const position = new THREE.Vector3(), projected = new THREE.Vector4();
  const viewProjection = new THREE.Matrix4();
  const textureUV = new THREE.Vector2();
  const srgb = value => Math.round(255 * (value <= .0031308 ? value * 12.92 : 1.055 * Math.pow(value, 1 / 2.4) - .055));
  const linear = new Float32Array(256);
  for (let i = 0; i < 256; i++) linear[i] = i / 255 <= .04045 ? i / 255 / 12.92 : Math.pow((i / 255 + .055) / 1.055, 2.4);
  function textureData(texture) {
    if (!texture?.image) return null;
    const cached = textures.get(texture);
    if (cached?.version === texture.version) return cached;
    const image = texture.image;
    const w = image.width || image.videoWidth, h = image.height || image.videoHeight;
    if (!w || !h) return null;
    // Reading only locally loaded asset images; never bypass a canvas taint.
    const scratch = document.createElement('canvas');
    scratch.width = w; scratch.height = h;
    const ctx = scratch.getContext('2d', {willReadFrequently: true});
    ctx.drawImage(image, 0, 0);
    const result = {data: ctx.getImageData(0, 0, w, h).data, width: w, height: h, version: texture.version};
    textures.set(texture, result);
    return result;
  }
  function resize(w, h, updateStyle = true) {
    const scale = Math.min(1, 900 / Math.max(w, h));
    width = Math.max(1, Math.round(w * scale)); height = Math.max(1, Math.round(h * scale));
    if (canvas.width !== width || canvas.height !== height) {canvas.width = width; canvas.height = height;}
    if (updateStyle) {canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;}
    output = context.createImageData(width, height); depth = new Float32Array(width * height);
  }
  resize(canvas.width || 1, canvas.height || 1, false);
  function render(scene, camera) {
    if (disposed) return;
    scene.updateMatrixWorld(true); camera.updateMatrixWorld(true);
    viewProjection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    depth.fill(Infinity);
    const pixels = output.data;
    for (let y = 0; y < height; y++) {
      const gradient = y / height;
      for (let x = 0; x < width; x++) {
        const i = (y * width + x) * 4;
        const shadow = Math.exp(-Math.pow((x - width * .5) / (width * .2), 2) - Math.pow((y - height * .88) / (height * .018), 2)) * 16;
        pixels[i] = 239 - 8 * gradient - shadow; pixels[i+1] = 240 - 7 * gradient - shadow; pixels[i+2] = 232 - 8 * gradient - shadow; pixels[i+3] = 255;
      }
    }
    const meshes = [];
    scene.traverseVisible(mesh => {
      if (!mesh.isMesh || !mesh.geometry?.attributes.position) return;
      if (mesh.material?.isShadowMaterial || /^(floor|ground|ring)$/i.test(mesh.name) || /^(RingGeometry|CircleGeometry)$/.test(mesh.geometry.type)) return;
      meshes.push(mesh);
    });
    // GLTF alpha-blended eyes must follow opaque skin. Like WebGLRenderer,
    // render opaque surfaces first so transparent depthWrite=false does not
    // allow a subsequently drawn body to erase the visible eyeballs.
    const transparent = mesh => (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).every(material => material.transparent);
    const centerA = new THREE.Vector3(), centerB = new THREE.Vector3();
    meshes.sort((a,b) => {
      const ta=transparent(a), tb=transparent(b);
      if (ta !== tb) return Number(ta)-Number(tb);
      if (!ta) return a.renderOrder-b.renderOrder;
      a.getWorldPosition(centerA); b.getWorldPosition(centerB);
      return centerB.distanceToSquared(camera.position)-centerA.distanceToSquared(camera.position);
    });
    for (const mesh of meshes) {
      if (mesh.isSkinnedMesh) mesh.skeleton.update();
      const geometry = mesh.geometry, count = geometry.attributes.position.count;
      const world = new Float32Array(count * 3), screen = new Float32Array(count * 4), normals = new Float32Array(count * 3);
      const indices = geometry.index?.array;
      const indexCount = indices?.length || count;
      for (let i = 0; i < count; i++) {
        mesh.getVertexPosition(i, position); position.applyMatrix4(mesh.matrixWorld);
        world.set([position.x, position.y, position.z], i * 3);
        projected.set(position.x, position.y, position.z, 1).applyMatrix4(viewProjection);
        const inverseW = 1 / projected.w;
        screen.set([(projected.x * inverseW * .5 + .5) * width, (.5 - projected.y * inverseW * .5) * height, projected.z * inverseW, inverseW], i * 4);
      }
      // Area-weighted smooth normals from the final morph + skin positions also
      // follow poses correctly without assuming a particular skeleton layout.
      for (let t = 0; t + 2 < indexCount; t += 3) {
        const a = (indices ? indices[t] : t) * 3, b = (indices ? indices[t+1] : t+1) * 3, c = (indices ? indices[t+2] : t+2) * 3;
        const ux = world[b]-world[a], uy = world[b+1]-world[a+1], uz = world[b+2]-world[a+2];
        const vx = world[c]-world[a], vy = world[c+1]-world[a+1], vz = world[c+2]-world[a+2];
        const nx = uy*vz-uz*vy, ny = uz*vx-ux*vz, nz = ux*vy-uy*vx;
        for (const v of [a,b,c]) {normals[v]+=nx; normals[v+1]+=ny; normals[v+2]+=nz;}
      }
      const lighting = new Float32Array(count);
      for (let i=0; i<count; i++) {
        const j=i*3, length=Math.hypot(normals[j],normals[j+1],normals[j+2]) || 1;
        const nx=normals[j]/length, ny=normals[j+1]/length, nz=normals[j+2]/length;
        lighting[i]=.48+.45*Math.max(0, -.44*nx+.62*ny+.65*nz)+.12*Math.max(0,.8*nx+.25*ny+.54*nz);
      }
      const groups = geometry.groups.length ? geometry.groups : [{start:0, count:indexCount, materialIndex:0}];
      for (const group of groups) {
        const material=Array.isArray(mesh.material)?mesh.material[group.materialIndex]:mesh.material;
        if (!material || material.visible===false || material.opacity===0) continue;
        const map=material.map, tex=textureData(map), uvAttribute=geometry.getAttribute(map?.channel ? `uv${map.channel}` : 'uv');
        const uv = tex && uvAttribute ? new Float32Array(count*2) : null;
        if (uv) {
          if (map.matrixAutoUpdate) map.updateMatrix();
          for(let i=0;i<count;i++) {textureUV.fromBufferAttribute(uvAttribute,i);map.transformUv(textureUV);uv[i*2]=textureUV.x;uv[i*2+1]=textureUV.y;}
        }
        const color=material.color || {r:1,g:1,b:1};
        const start=Math.max(group.start,geometry.drawRange.start), end=Math.min(indexCount,group.start+group.count,geometry.drawRange.start+geometry.drawRange.count);
        const triangles=[];
        for(let t=start;t+2<end;t+=3) triangles.push(t);
        // Eye meshes can contain nested transparent shells. Sort their actual
        // projected triangles too, not merely their common object origin.
        if(material.transparent) {
          const triangleDepth=t => screen[(indices?indices[t]:t)*4+2]+screen[(indices?indices[t+1]:t+1)*4+2]+screen[(indices?indices[t+2]:t+2)*4+2];
          triangles.sort((a,b)=>triangleDepth(b)-triangleDepth(a));
        }
        for(const t of triangles) {
          const ia=indices?indices[t]:t, ib=indices?indices[t+1]:t+1, ic=indices?indices[t+2]:t+2;
          const a=ia*4,b=ib*4,c=ic*4;
          if(screen[a+3]<=0||screen[b+3]<=0||screen[c+3]<=0)continue;
          const ax=screen[a],ay=screen[a+1],bx=screen[b],by=screen[b+1],cx=screen[c],cy=screen[c+1];
          const area=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax);
          if(Math.abs(area)<1e-8)continue;
          const back=area>0;
          if(material.side===THREE.FrontSide&&back || material.side===THREE.BackSide&&!back)continue;
          const x0=Math.max(0,Math.floor(Math.min(ax,bx,cx))),x1=Math.min(width-1,Math.ceil(Math.max(ax,bx,cx)));
          const y0=Math.max(0,Math.floor(Math.min(ay,by,cy))),y1=Math.min(height-1,Math.ceil(Math.max(ay,by,cy)));
          for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++) {
            const dx=x+.5-ax,dy=y+.5-ay;
            const wb=(dx*(cy-ay)-dy*(cx-ax))/area, wc=((bx-ax)*dy-(by-ay)*dx)/area, wa=1-wb-wc;
            if(wa<0||wb<0||wc<0)continue;
            const z=wa*screen[a+2]+wb*screen[b+2]+wc*screen[c+2],pixel=y*width+x;
            if(z < -1 || z > 1 || z>=depth[pixel])continue;
            const denominator=wa*screen[a+3]+wb*screen[b+3]+wc*screen[c+3];
            const pa=wa*screen[a+3]/denominator,pb=wb*screen[b+3]/denominator,pc=wc*screen[c+3]/denominator;
            let r=color.r,g=color.g,bl=color.b,alpha=material.opacity??1;
            if(uv) {
              const u=pa*uv[ia*2]+pb*uv[ib*2]+pc*uv[ic*2],v=pa*uv[ia*2+1]+pb*uv[ib*2+1]+pc*uv[ic*2+1];
              const tx=Math.min(tex.width-1,Math.max(0,Math.floor(u*tex.width))),ty=Math.min(tex.height-1,Math.max(0,Math.floor(v*tex.height))),k=(ty*tex.width+tx)*4;
              r*=linear[tex.data[k]];g*=linear[tex.data[k+1]];bl*=linear[tex.data[k+2]];alpha*=tex.data[k+3]/255;
            }
            if(alpha<Math.max(material.alphaTest||0,.01))continue;
            const light=material.isMeshBasicMaterial?1:pa*lighting[ia]+pb*lighting[ib]+pc*lighting[ic];
            const k=pixel*4;
            pixels[k]=Math.min(255,srgb(Math.max(0,r*light)))*alpha+pixels[k]*(1-alpha);
            pixels[k+1]=Math.min(255,srgb(Math.max(0,g*light)))*alpha+pixels[k+1]*(1-alpha);
            pixels[k+2]=Math.min(255,srgb(Math.max(0,bl*light)))*alpha+pixels[k+2]*(1-alpha);
            if(material.depthWrite!==false)depth[pixel]=z;
          }
        }
      }
    }
    context.putImageData(output,0,0);
  }
  return {setPixelRatio(){},getPixelRatio:()=>1,setSize:resize,render,dispose(){disposed=true;output=null;depth=null;},capabilities:{getMaxAnisotropy:()=>1},shadowMap:{enabled:false},isSoftwareRenderer:true};
}
