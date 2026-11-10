import test from 'node:test';import assert from 'node:assert/strict';
import {AnimationClip,NumberKeyframeTrack} from '../vendor/three.module.min.js';
import {applyPoseCorrectives,exportPoseClips} from '../src/pose-morphs.js';
const mapping={wave:'PoseWave',tpose:'PoseTpose'};
const mesh=()=>({name:'Outfit',morphTargetDictionary:{BuildNarrow:0,PoseWave:1,PoseTpose:2},morphTargetInfluences:[.6,1,0]});
test('pose change clears every stale correction without touching appearance',()=>{const m=mesh();applyPoseCorrectives(m,mapping,'tpose');assert.deepEqual(m.morphTargetInfluences,[.6,0,1]);applyPoseCorrectives(m,mapping,'relaxed');assert.deepEqual(m.morphTargetInfluences,[.6,0,0]);});
test('all exported clips preserve current appearance and activate only matching correction',()=>{const m=mesh(),clips=['wave','relaxed','tpose'].map(n=>new AnimationClip(n,1,[new NumberKeyframeTrack('Outfit.morphTargetInfluences',[0,1],[0,1,0,0,1,0])]));const result=exportPoseClips(clips,[m],mapping);for(const c of result){const t=c.tracks.find(t=>t.name==='Outfit.morphTargetInfluences');const expected=[.6,Number(c.name==='wave'),Number(c.name==='tpose')];assert.ok(t);assert.equal(c.tracks.length,1);for(let i=0;i<t.values.length;i++)assert.ok(Math.abs(t.values[i]-expected[i%3])<1e-6);}assert.deepEqual(m.morphTargetInfluences,[.6,1,0]);assert.equal(clips[0].tracks[0].values[0],0);});
