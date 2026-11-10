import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
const meta=JSON.parse(await readFile(new URL('../app.json',import.meta.url),'utf8'));
test('published catalogue describes optional garment rig without claiming simulation',async()=>{
  assert.match(meta.description,/A-line skirt/);
  assert.ok(meta.features.some(x=>/nine garment-only auxiliary bones/i.test(x)));
  assert.ok(meta.features.some(x=>/hem.sway/i.test(x)));
  assert.ok(meta.features.some(x=>/53-bone/.test(x)));
  assert.ok(meta.features.some(x=>/adult face presets/.test(x)));
  assert.ok(meta.limitations.some(x=>/No.*cloth simulation/.test(x)));
  assert.ok(meta.screenshots.includes('docs/screenshots/persona-skirt-comparison.png'));
  for(const file of meta.screenshots)await access(new URL('../'+file,import.meta.url));
});
