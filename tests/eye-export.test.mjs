import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
test('independent eye export oracle checks corrective products, clamping, and unchanged foundations',()=>{
  const report=JSON.parse(execFileSync('python3',['-B','tools/validate-eye-export.py','--self-test'],{cwd:new URL('../',import.meta.url),encoding:'utf8'}));
  assert.equal(report.passed,true);
  assert.equal(report.oracleCases,2);
});
