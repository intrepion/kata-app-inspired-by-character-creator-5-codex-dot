import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
const meta=JSON.parse(await readFile(new URL('../app.json',import.meta.url),'utf8'));
test('published catalogue describes closed-mouth expressions and honest rig limits',async()=>{
 assert.match(meta.description,/expressions/);
 assert.ok(meta.features.some(x=>/smile.*frown.*brow/i.test(x)));
 assert.ok(meta.features.some(x=>/blink.*gaze/i.test(x)));
 assert.ok(meta.features.some(x=>/editable.*expression/i.test(x)));
 assert.ok(meta.limitations.some(x=>/No mouth interior.*jaw.*lip-sync/i.test(x)));
 assert.ok(meta.limitations.some(x=>/Blender.*squint/i.test(x)));
 assert.ok(meta.screenshots.includes('docs/screenshots/persona-expressions.png'));
 assert.ok(!meta.limitations.some(x=>/No mouth expressions|eye-only/i.test(x)));
 for(const file of meta.screenshots)await access(new URL('../'+file,import.meta.url));
});
