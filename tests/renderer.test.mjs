import test from 'node:test';
import assert from 'node:assert/strict';
import { frameCharacter } from '../src/renderer.js';
import { mesh,defaults,ranges } from '../src/model.js';
test('full body camera fits every pose at narrow and desktop widths',()=>{for(const width of [390,650])for(const pose of ['relaxed','tpose','wave','stride'])for(const [key,limits] of Object.entries(ranges))for(const value of limits){const faces=mesh({...defaults,pose,[key]:value}),f=frameCharacter(faces,width,650,0,'body');for(const face of faces)for(const v of face.v){const x=width/2+(v[0]-f.center[0])*f.scale,y=650/2-(v[1]-f.center[1])*f.scale;assert.ok(x>=20&&x<=width-20);assert.ok(y>=45&&y<=560);}}});
test('face framing brings the head into view',()=>{const faces=mesh(defaults),body=frameCharacter(faces,650,800,0,'body'),face=frameCharacter(faces,650,800,0,'face');assert.ok(face.scale>body.scale*3);assert.ok(face.center[1]>3);});
import { createRenderer } from '../src/renderer.js';
test('software fallback resolves overlap by depth, independent of triangle order',()=>{
  globalThis.devicePixelRatio=1;
  const makeFace=(z,color)=>({part:'head',color,v:[[-1,0,z],[1,0,z],[0,2,z]],normals:[[0,0,1],[0,0,1],[0,0,1]]});
  let rendered;
  const context={createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),putImageData:image=>{rendered=image.data;}};
  const canvas={dataset:{},getContext:type=>type==='2d'?context:null,getBoundingClientRect:()=>({width:400,height:650})};
  const renderer=createRenderer(canvas),near=makeFace(.1,'#ff0000'),far=makeFace(0,'#0000ff');
  renderer.render([near,far],0);const forward=rendered.slice();
  renderer.render([far,near],0);assert.deepEqual(rendered,forward);
  assert.equal(canvas.dataset.renderer,'software-depth');
  const center=(350*400+200)*4;assert.ok(rendered[center]>150);assert.equal(rendered[center+2],0);
});
