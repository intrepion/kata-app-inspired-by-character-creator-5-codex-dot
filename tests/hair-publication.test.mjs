import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
const meta=JSON.parse(await readFile(new URL('../app.json',import.meta.url),'utf8'));
test('hair release advertises the reviewed cards with current comparison and honest limits',async()=>{
 assert.match(meta.description,/layered Blender hair-card crop/);
 assert.equal(meta.screenshots[0],'docs/screenshots/persona-hair-edges-closeup.png');
 assert.ok(meta.features.some(x=>/435 guide curves/.test(x)));
 assert.ok(meta.features.some(x=>/28 identity morph/.test(x)));
 assert.ok(meta.limitations.some(x=>/Static layered hair cards.*not photorealistic.*rear layering/.test(x)));
 assert.ok(!meta.limitations.some(x=>/Stylized procedural hair/.test(x)));
 for(const path of meta.screenshots)await access(new URL('../'+path,import.meta.url));
});
