import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from '../vendor/three.module.min.js';
import {measureBodyEnvelope, bodyCameraFrame} from '../src/human-framing.js';

function fixture(){
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.Float32BufferAttribute([-.2,0,.1,.2,1.6,-.1],3));
  geometry.morphTargetsRelative=true;
  geometry.morphAttributes.position=[
    new THREE.Float32BufferAttribute([-.1,0,0,.1,.1,0],3),
    new THREE.Float32BufferAttribute([.05,0,0,-.05,-.05,0],3),
    new THREE.Float32BufferAttribute([0,0,.2,0,.2,-.2],3),
  ];
  const mesh=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial());
  mesh.morphTargetDictionary={wide:0,narrow:1,raised:2};
  mesh.morphTargetInfluences=[.7,0,.3];
  mesh.updateMatrixWorld(true);
  return mesh;
}
const mapping={build:['narrow','wide'],poseDetail:'raised'};
test('reference envelope includes simultaneous morph extremes and max height, restoring active shape',()=>{
  const mesh=fixture();
  const envelope=measureBodyEnvelope([mesh],mapping,1.1);
  assert.deepEqual(mesh.morphTargetInfluences,[.7,0,.3]);
  assert.ok(Math.abs(envelope.maxY-1.9*1.1)<1e-6);
  assert.ok(envelope.radius>=Math.hypot(.3,.3)*1.1-1e-6);
});
test('body camera is independent of active height, morphs and orbit, so height remains visible',()=>{
  const mesh=fixture(),envelope=measureBodyEnvelope([mesh],mapping,1.1);
  const frame=bodyCameraFrame(envelope,1,29);
  mesh.morphTargetInfluences=[0,1,1];
  const remeasured=measureBodyEnvelope([mesh],mapping,1.1);
  assert.deepEqual(bodyCameraFrame(remeasured,1,29),frame);
  // At a fixed camera, a taller centered segment has a greater projected size.
  const projected=height=>1.6*height/frame.distance;
  assert.ok(projected(1.1)/projected(.9)>1.22);
});
test('portrait and wide frames contain the full-height envelope at every orbit angle',()=>{
  const envelope=measureBodyEnvelope([fixture()],mapping,1.1);
  for(const aspect of [.35,.7,1,2.4]){
    const frame=bodyCameraFrame(envelope,aspect,29);
    const tan=Math.tan(29*Math.PI/360);
    const nearest=frame.distance-envelope.radius;
    assert.ok(envelope.radius/nearest/tan/aspect<1);
    assert.ok((envelope.maxY-envelope.minY)/2/nearest/tan<1);
  }
});
test('pose corrective influences stay fixed in the reference while appearance controls span their ranges',()=>{
  const mesh=fixture();
  const appearance={build:['narrow','wide']};
  mesh.morphTargetDictionary.PoseWave=mesh.morphTargetDictionary.raised;
  delete mesh.morphTargetDictionary.raised;
  mesh.morphTargetInfluences=[.7,0,1];
  const corrected=measureBodyEnvelope([mesh],appearance,1.1);
  assert.deepEqual(mesh.morphTargetInfluences,[.7,0,1]);
  assert.ok(Math.abs(corrected.maxY-1.9*1.1)<1e-6);
  mesh.morphTargetInfluences=[0,1,1];
  assert.deepEqual(measureBodyEnvelope([mesh],appearance,1.1),corrected);
  mesh.morphTargetInfluences[2]=0;
  const uncorrected=measureBodyEnvelope([mesh],appearance,1.1);
  assert.ok(Math.abs(corrected.maxY-uncorrected.maxY-.2*1.1)<1e-6);
  assert.ok(corrected.radius>uncorrected.radius);
});

test('portrait framing follows the offset head through profile and keeps its envelope visible',async()=>{
  const {portraitCameraFrame}=await import('../src/human-framing.js');assert.equal(typeof portraitCameraFrame,'function');
  for(const aspect of [.45,360/440,1.5])for(const yaw of [0,.55,Math.PI/2,Math.PI])for(const scale of [.9,1.1]){
    const f=portraitCameraFrame(1.461,.045,scale,yaw,aspect,29);
    const camera=new THREE.PerspectiveCamera(29,aspect,.01,40);camera.position.set(f.targetX,f.targetY+.04*scale,f.targetZ+f.distance);camera.lookAt(f.targetX,f.targetY,f.targetZ);camera.updateMatrixWorld(true);
    for(const x of [-.08,.08])for(const z of [-.055,.16])for(const y of [1.37,1.584]){
      const p=new THREE.Vector3(x,y,z).multiplyScalar(scale).applyAxisAngle(new THREE.Vector3(0,1,0),yaw).project(camera);assert.ok(Math.abs(p.x)<.99&&Math.abs(p.y)<.99,JSON.stringify({aspect,yaw,scale,p}));
    }
  }
});
