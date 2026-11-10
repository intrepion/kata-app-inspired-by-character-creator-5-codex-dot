import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

const root = new URL('../', import.meta.url);
test('original skirt work leaves both approved foundation files byte-identical', () => {
  for (const [path, expected] of [
    ['assets/human/foundation.glb', '642dc95643eca689266fce489bc87ac65377529af77c2e522c0326d87a9d79ab'],
    ['assets/source/foundation.blend', '504164e65309c940446375fc28d7116baa0f83dfdd5425d50852c2d4ae5e40e5'],
  ]) assert.equal(createHash('sha256').update(readFileSync(new URL(path, root))).digest('hex'), expected, path);
});
test('independent export validator rejects broken weights, indices, influence counts and matrices', () => {
  const result = JSON.parse(execFileSync('python3', ['tools/validate-skirt-export.py', '--self-test'], {cwd:root,encoding:'utf8'}));
  assert.equal(result.passed, true);
  assert.equal(result.negativeControls, 6);
});
