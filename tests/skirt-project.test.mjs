import test from 'node:test';
import assert from 'node:assert/strict';
import * as project from '../src/project.js';
import {defaults as legacy} from '../src/model.js';
const {defaults,ranges,presets,validate,parseProject,migrate,History}=project;

test('existing defaults and all presets remain trousers with neutral skirt bones',()=>{
  assert.deepEqual(project.garmentDefaults,{lowerGarment:'trousers',skirtSwing:0});
  for(const p of [defaults,...Object.values(presets)]){
    assert.equal(p.lowerGarment,'trousers');assert.equal(p.skirtSwing,0);
    assert.deepEqual(validate(p),p);
  }
  assert.equal(Object.hasOwn(ranges,'skirtSwing'),false,'garment bones are not body or face controls');
  assert.equal(Object.keys(ranges).filter(key=>!Object.hasOwn(project.eyeControlDefaults,key)).length,15);
});

test('missing optional garment fields normalize independently without mutating old projects',()=>{
  for(const omitted of [['lowerGarment'],['skirtSwing'],['lowerGarment','skirtSwing']]){
    const old={...defaults};for(const key of omitted)delete old[key];
    const before=structuredClone(old),normalized=validate(old);
    assert.deepEqual(normalized,defaults);assert.deepEqual(old,before);
  }
  const old={...defaults,lowerGarment:'skirt'};delete old.skirtSwing;
  assert.equal(validate(old).lowerGarment,'skirt');assert.equal(validate(old).skirtSwing,0);
  delete old.lowerGarment;for(const key of Object.keys(project.faceDefaults))delete old[key];
  assert.deepEqual(parseProject(JSON.stringify(old)).project,defaults);
});

test('garment selection and sway reject supplied invalid values but accept both endpoints',()=>{
  for(const lowerGarment of ['trousers','skirt'])for(const skirtSwing of [-.12,0,.12]){
    const p={...defaults,lowerGarment,skirtSwing};assert.deepEqual(validate(p),p);
  }
  for(const lowerGarment of [undefined,null,'','Skirt','dress',0,false,{},[]])assert.throws(()=>validate({...defaults,lowerGarment}),/lower garment/i);
  for(const skirtSwing of [undefined,null,NaN,Infinity,-Infinity,'0',false,-.120001,.120001,{},[]])assert.throws(()=>validate({...defaults,skirtSwing}),/skirtSwing/);
  const missingRequired={...defaults};delete missingRequired.build;delete missingRequired.lowerGarment;delete missingRequired.skirtSwing;
  assert.throws(()=>validate(missingRequired),/build/);
});

test('skirt projects roundtrip and history preserves selection, color and bone pose',()=>{
  const skirt={...defaults,lowerGarment:'skirt',skirtSwing:.08,pants:'#b08264',headWidth:.7};
  assert.deepEqual(parseProject(JSON.stringify(skirt)).project,skirt);
  const history=new History(defaults);history.push(skirt);
  assert.deepEqual(history.undo(),defaults);assert.deepEqual(history.redo(),skirt);
  const loaded=parseProject(JSON.stringify(skirt)).project;loaded.skirtSwing=0;
  assert.equal(skirt.skirtSwing,.08);
});

test('v1 migration gains garment defaults without changing the retained legacy payload',()=>{
  const old=structuredClone(legacy),{project:p}=migrate(old);
  assert.equal(p.lowerGarment,'trousers');assert.equal(p.skirtSwing,0);
  assert.deepEqual(p.legacySource,legacy);assert.deepEqual(old,legacy);
  assert.equal(Object.hasOwn(p.legacySource,'lowerGarment'),false);
  assert.equal(Object.hasOwn(p.legacySource,'skirtSwing'),false);
});
