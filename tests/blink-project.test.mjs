import test from 'node:test';
import assert from 'node:assert/strict';
import {defaults, presets, ranges, validate, parseProject, migrate, History} from '../src/project.js';
import {defaults as legacyDefaults} from '../src/model.js';
const controls={blinkLeft:0,blinkRight:0,gazeHorizontal:0,gazeVertical:0};

test('eye controls default to neutral in every preset',()=>{
  for(const project of [defaults,...Object.values(presets)])for(const [key,value] of Object.entries(controls))assert.equal(project[key],value,key);
  for(const key of Object.keys(controls))assert.deepEqual(ranges[key],key.startsWith('blink')?[0,1]:[-1,1]);
});
test('old v2 files omit eye controls and normalize neutral without mutating source',()=>{
  const source={...defaults};for(const key of Object.keys(controls))delete source[key];
  const before=structuredClone(source), normalized=validate(source);
  for(const [key,value] of Object.entries(controls))assert.equal(normalized[key],value,key);
  assert.deepEqual(source,before);
  assert.deepEqual(parseProject(JSON.stringify(source)).project,normalized);
  for(const key of Object.keys(controls))assert.equal(migrate(legacyDefaults).project[key],0,key);
});
test('eye control endpoints and independent values validate',()=>{
  for(const key of Object.keys(controls))for(const value of key.startsWith('blink')?[0,.43,1]:[-1,-.43,0,.43,1])assert.equal(validate({...defaults,[key]:value})[key],value);
  const project={...defaults,blinkLeft:1,blinkRight:.12,gazeHorizontal:-.57,gazeVertical:.83};
  assert.deepEqual(parseProject(JSON.stringify(project)).project,project);
});
test('supplied invalid eye controls are rejected rather than defaulted or clamped',()=>{
  for(const key of Object.keys(controls))for(const value of [undefined,null,NaN,Infinity,-Infinity,'0',false,{},[],1.01,key.startsWith('blink')?-.01:-1.01])assert.throws(()=>validate({...defaults,[key]:value}),new RegExp(`Invalid ${key} value`));
});
test('history preserves independent eye edits, reset, undo and redo',()=>{
  const history=new History(defaults), edited={...defaults,blinkLeft:1,blinkRight:.25,gazeHorizontal:-1,gazeVertical:1};
  history.push(edited);history.push({...edited,...controls});
  assert.deepEqual(history.undo(),edited);assert.deepEqual(history.undo(),defaults);
  assert.deepEqual(history.redo(),edited);assert.deepEqual(history.redo(),{...edited,...controls});
});
