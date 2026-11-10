import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from '../vendor/three.module.min.js';
import {createHumanSoftwareRenderer} from '../src/human-software-renderer.js';

function fixture() {
  let frame;
  const context={createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),putImageData:image=>{frame=image.data.slice();}};
  const canvas={width:64,height:64,style:{},dataset:{},getContext:kind=>{assert.equal(kind,'2d');return context;}};
  const renderer=createHumanSoftwareRenderer(canvas);
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(45,1,.1,10);
  camera.position.z=3;
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.Float32BufferAttribute([-1,-1,0,1,-1,0,0,1,0],3));
  const mesh=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({color:0xff0000}));scene.add(mesh);
  return {renderer,scene,camera,mesh,canvas,pixel:()=>Array.from(frame.slice((32*64+32)*4,(32*64+32)*4+3))};
}
test('rasterizes the actual Three mesh with front-face culling and depth',()=>{
  const f=fixture(); f.renderer.render(f.scene,f.camera);assert.deepEqual(f.pixel(),[255,0,0]);
  const farther=f.mesh.clone();farther.material=new THREE.MeshBasicMaterial({color:0x0000ff});farther.position.z=-.5;f.scene.add(farther);
  f.renderer.render(f.scene,f.camera);assert.deepEqual(f.pixel(),[255,0,0]);
  f.mesh.rotation.y=Math.PI; f.scene.remove(farther);f.renderer.render(f.scene,f.camera);assert.notDeepEqual(f.pixel(),[255,0,0]);
  f.mesh.material.side=THREE.DoubleSide;f.renderer.render(f.scene,f.camera);assert.deepEqual(f.pixel(),[255,0,0]);
});
test('uses live morph deformation and hidden-parent visibility',()=>{
  const f=fixture();f.mesh.geometry.morphTargetsRelative=true;
  f.mesh.geometry.morphAttributes.position=[new THREE.Float32BufferAttribute([4,0,0,4,0,0,4,0,0],3)];f.mesh.updateMorphTargets();
  f.renderer.render(f.scene,f.camera);assert.deepEqual(f.pixel(),[255,0,0]);
  f.mesh.morphTargetInfluences[0]=1;f.renderer.render(f.scene,f.camera);assert.notDeepEqual(f.pixel(),[255,0,0]);
  f.mesh.morphTargetInfluences[0]=0;const parent=new THREE.Group();f.scene.add(parent);parent.add(f.mesh);parent.visible=false;
  f.renderer.render(f.scene,f.camera);assert.notDeepEqual(f.pixel(),[255,0,0]);
  assert.equal(f.canvas.dataset.renderer,'software-human');
});
test('caps backing resolution at 900 pixels and ignores high DPR',()=>{
  const f=fixture();f.renderer.setPixelRatio(3);f.renderer.setSize(1200,1800,false);
  assert.equal(f.canvas.width,600);assert.equal(f.canvas.height,900);assert.equal(f.renderer.getPixelRatio(),1);
});
test('draws alpha-blended eye-like surfaces after opaque skin even when listed first',()=>{
  const f=fixture();
  f.mesh.material.transparent=true;f.mesh.material.depthWrite=false;f.mesh.material.opacity=.5;
  const body=f.mesh.clone();body.position.z=-.5;body.material=new THREE.MeshBasicMaterial({color:0x0000ff});
  f.scene.add(body);f.renderer.render(f.scene,f.camera);
  const [red,green,blue]=f.pixel();assert.ok(red>100 && red<150);assert.equal(green,0);assert.ok(blue>100 && blue<150);
});
