import test from 'node:test';
import assert from 'node:assert/strict';
import {defaults,presets,ranges,validate,parseProject,History} from '../src/project.js';
const neutral={smile:0,frown:0,browRaise:0,browFurrow:0};
test('expression defaults and ranges preserve neutral older projects',()=>{for(const p of [defaults,...Object.values(presets)])for(const[k,v]of Object.entries(neutral))assert.equal(p[k],v,k);const old={...defaults};for(const k in neutral)delete old[k];const before=structuredClone(old),parsed=validate(old);assert.deepEqual(old,before);for(const k in neutral){assert.equal(parsed[k],0);assert.deepEqual(ranges[k],[0,1]);}});
test('expression save/open and undo/redo retain all values without touching eyes',()=>{const p={...defaults,smile:.7,frown:.2,browRaise:.8,browFurrow:.3,blinkLeft:.6,gazeVertical:-1};assert.deepEqual(parseProject(JSON.stringify(p)).project,p);const h=new History(defaults);h.push(p);h.push({...p,...neutral});assert.deepEqual(h.undo(),p);assert.deepEqual(h.redo(),{...p,...neutral});});
test('explicit invalid expressions are rejected, not silently normalized',()=>{for(const k in neutral){for(const v of [undefined,null,NaN,Infinity,'0',false,{},[],1.01,-.01])assert.throws(()=>validate({...defaults,[k]:v}),new RegExp('Invalid '+k));for(const v of [0,.23,1])assert.equal(validate({...defaults,[k]:v})[k],v);}});
