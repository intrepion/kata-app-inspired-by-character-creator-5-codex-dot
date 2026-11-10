import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
test('independent expression export oracle checks opposition, clamping, smile squint, and unchanged foundations',()=>{
  const report=JSON.parse(execFileSync('python3',['-B','tools/validate-expression-export.py','--self-test'],{cwd:new URL('../',import.meta.url),encoding:'utf8'}));
  assert.equal(report.passed,true);
  assert.equal(report.oracleCases,4);
  assert.equal(Object.keys(report.sourceHashes).length,2);
});
