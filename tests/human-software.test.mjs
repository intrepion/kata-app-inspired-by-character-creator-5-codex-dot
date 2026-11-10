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

test('shading follows authored GLB normals instead of silently repairing them',()=>{
  const f=fixture();f.mesh.material=new THREE.MeshStandardMaterial({color:0x808080});
  const attribute=new THREE.Float32BufferAttribute([0,0,1,0,0,1,0,0,1],3);f.mesh.geometry.setAttribute('normal',attribute);
  f.renderer.render(f.scene,f.camera);const forward=f.pixel()[0];
  for(let i=0;i<3;i++)attribute.setXYZ(i,0,0,-1);
  f.renderer.render(f.scene,f.camera);assert.ok(f.pixel()[0]<forward-15,'Authored inward normals must visibly darken the preview, like WebGL');
});
test('shading includes morph-target normal deltas',()=>{
  const f=fixture();f.mesh.material=new THREE.MeshStandardMaterial({color:0x808080});
  f.mesh.geometry.setAttribute('normal',new THREE.Float32BufferAttribute([0,0,1,0,0,1,0,0,1],3));
  f.mesh.geometry.morphTargetsRelative=true;f.mesh.geometry.morphAttributes.normal=[new THREE.Float32BufferAttribute([0,0,-2,0,0,-2,0,0,-2],3)];f.mesh.updateMorphTargets();
  f.renderer.render(f.scene,f.camera);const forward=f.pixel()[0];f.mesh.morphTargetInfluences[0]=1;
  f.renderer.render(f.scene,f.camera);assert.ok(f.pixel()[0]<forward-15,'Normal morphs must influence shading even when positions stay fixed');
});

test('skinned authored normals match shader-order bone, bind, and nonuniform world transforms',()=>{
  const f=fixture(),geometry=f.mesh.geometry;
  const authored=new THREE.Vector3(.35,.2,1).normalize();
  geometry.setAttribute('normal',new THREE.Float32BufferAttribute(Array(3).fill(authored.toArray()).flat(),3));
  geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute([0,1,0,0,0,1,0,0,0,1,0,0],4));
  geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute([.65,.35,0,0,.65,.35,0,0,.65,.35,0,0],4));
  const material=new THREE.MeshStandardMaterial({color:0x808080,side:THREE.DoubleSide});
  const skinned=new THREE.SkinnedMesh(geometry,material),root=new THREE.Bone(),tip=new THREE.Bone();
  root.add(tip);tip.position.y=.15;skinned.add(root);f.scene.remove(f.mesh);f.scene.add(skinned);
  f.scene.updateMatrixWorld(true);skinned.bind(new THREE.Skeleton([root,tip]));
  skinned.rotation.set(.1,.18,-.15);skinned.scale.set(1.2,.7,.85);skinned.position.set(.04,-.03,.08);
  root.rotation.set(.12,.2,.08);tip.rotation.set(-.25,.3,-.18);
  const parent=new THREE.Group();parent.rotation.z=.12;parent.scale.set(.85,1.1,1);f.scene.add(parent);parent.add(skinned);
  f.scene.updateMatrixWorld(true);skinned.skeleton.update();
  f.renderer.render(f.scene,f.camera);const actual=f.pixel();
  const positions=[],normals=[];
  for(let i=0;i<3;i++){
    positions.push(...skinned.getVertexPosition(i,new THREE.Vector3()).applyMatrix4(skinned.matrixWorld).toArray());
    // Independent shader reference: skinbase_vertex forms the weighted bone
    // matrix; skinnormal_vertex sandwiches it between inverse bind and bind.
    // A direction has w=0, so bone/mesh translation must not affect lighting.
    const bound=new THREE.Vector4(...authored.toArray(),0).applyMatrix4(skinned.bindMatrix);
    const sum=new THREE.Vector4(0,0,0,0);
    for(const [index,weight] of [[0,.65],[1,.35]]){
      const matrix=new THREE.Matrix4().fromArray(skinned.skeleton.boneMatrices,index*16);
      sum.add(bound.clone().applyMatrix4(matrix).multiplyScalar(weight));
    }
    sum.applyMatrix4(skinned.bindMatrixInverse);
    const expected=new THREE.Vector3(sum.x,sum.y,sum.z)
      .applyMatrix3(new THREE.Matrix3().getNormalMatrix(skinned.matrixWorld)).normalize();
    normals.push(...expected.toArray());
  }
  const referenceGeometry=new THREE.BufferGeometry();
  referenceGeometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
  referenceGeometry.setAttribute('normal',new THREE.Float32BufferAttribute(normals,3));
  const reference=new THREE.Mesh(referenceGeometry,material);parent.visible=false;f.scene.add(reference);
  f.renderer.render(f.scene,f.camera);
  assert.deepEqual(actual,f.pixel(),'Skinned lighting must equal independently transformed authored normals');
  // Ensure the reference is sensitive to omitting the normal transforms, rather
  // than accidentally sampling background or an unchanged light direction.
  referenceGeometry.setAttribute('normal',new THREE.Float32BufferAttribute(Array(3).fill(authored.toArray()).flat(),3));
  f.renderer.render(f.scene,f.camera);
  assert.ok(Math.abs(actual[0]-f.pixel()[0])>=3,'Fixture must distinguish transformed and untransformed normals');
});

test('software preview preserves generated data textures and linear vertex color',()=>{const f=fixture();f.mesh.material.color.set(0xffffff);f.mesh.material.vertexColors=true;f.mesh.geometry.setAttribute('color',new THREE.Float32BufferAttribute([.25,1,.5,.25,1,.5,.25,1,.5],3));f.mesh.geometry.setAttribute('uv',new THREE.Float32BufferAttribute([0,0,1,0,.5,1],2));f.mesh.material.map=new THREE.DataTexture(new Uint8Array([255,255,255,255]),1,1,THREE.RGBAFormat);f.mesh.material.map.needsUpdate=true;f.renderer.render(f.scene,f.camera);assert.deepEqual(f.pixel(),[137,255,188]);});

test('software repeat wrapping occurs after UV interpolation across an atlas seam',()=>{const f=fixture();f.mesh.material.color.set(0xffffff);f.mesh.geometry.setAttribute('uv',new THREE.Float32BufferAttribute([.9,0,1.1,0,1.1,1],2));const texture=new THREE.DataTexture(new Uint8Array([255,0,0,255,0,255,0,255,0,0,255,255,0,0,255,255]),4,1,THREE.RGBAFormat);texture.wrapS=THREE.RepeatWrapping;texture.needsUpdate=true;f.mesh.material.map=texture;f.renderer.render(f.scene,f.camera);assert.deepEqual(f.pixel(),[255,0,0]);});
