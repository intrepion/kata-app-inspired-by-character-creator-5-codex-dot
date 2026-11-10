import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';

// Use an ephemeral HTTP port, never a file:// page or a second browser preview.
test('HTTP server honors CLI port and serves safe static responses', {timeout: 10000}, async t => {
  const child = spawn(process.execPath, ['server.mjs', '--port', '0', '--host', '127.0.0.1'], {cwd: new URL('..', import.meta.url), stdio: ['ignore','pipe','pipe']});
  t.after(() => child.kill());
  const origin = await new Promise((resolve, reject) => {
    let output = '';
    child.stdout.on('data', chunk => {
      output += chunk;
      const match = output.match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) resolve(match[0]);
    });
    child.once('error', reject);
    child.once('exit', code => reject(new Error('Server exited: ' + code)));
  });
  const page = await fetch(origin + '/');
  assert.equal(page.status, 200);
  assert.match(page.headers.get('content-type'), /text\/html/);
  assert.match(await page.text(), /<canvas/);
  const script = await fetch(origin + '/src/app.js');
  assert.equal(script.status, 200);
  assert.match(script.headers.get('content-type'), /javascript/);
  const asset = await fetch(origin + '/assets/human/foundation.glb', {method:'HEAD'});
  assert.equal(asset.status, 200);
  assert.match(asset.headers.get('content-type'), /model\/gltf-binary/);
  const head = await fetch(origin + '/', {method:'HEAD'});
  assert.equal(head.status, 200);
  assert.equal(await head.text(), '');
  assert.equal((await fetch(origin + '/.git/config')).status, 404);
  assert.equal((await fetch(origin + '/does-not-exist')).status, 404);
  assert.equal((await fetch(origin + '/', {method:'POST'})).status, 405);
});

test('opt-in export capture accepts only valid same-origin loopback QA GLBs', {timeout:10000},async t=>{
  const {readFile,mkdtemp,copyFile,rm}=await import('node:fs/promises');const {tmpdir}=await import('node:os');const {join}=await import('node:path');const temp=await mkdtemp(join(tmpdir(),'persona-export-test-'));await copyFile(new URL('../server.mjs',import.meta.url),join(temp,'server.mjs'));t.after(()=>rm(temp,{recursive:true,force:true}));const {createHash}=await import('node:crypto');
  const child=spawn(process.execPath,['server.mjs','--port','0','--host','127.0.0.1','--qa-exports'],{cwd:temp,stdio:['ignore','pipe','pipe']});t.after(()=>child.kill());
  const origin=await new Promise((resolve,reject)=>{let text='';child.stdout.on('data',chunk=>{text+=chunk;const m=text.match(/http:\/\/127\.0\.0\.1:\d+/);if(m)resolve(m[0]);});child.once('error',reject);});
  const url=origin+'/__qa/export/portrait-extreme.glb',data=await readFile(new URL('../assets/human/foundation.glb',import.meta.url));
  assert.equal((await fetch(url,{method:'POST',body:data})).status,403);
  assert.equal((await fetch(url,{method:'POST',headers:{Origin:'https://example.com'},body:data})).status,403);
  assert.equal((await fetch(url,{method:'POST',headers:{Origin:origin},body:'not a GLB'})).status,400);
  assert.equal((await fetch(origin+'/__qa/export/other.glb',{method:'POST',headers:{Origin:origin},body:data})).status,405);
  const res=await fetch(url,{method:'POST',headers:{Origin:origin},body:data});assert.equal(res.status,201);const info=await res.json();assert.equal(info.sha256,createHash('sha256').update(data).digest('hex'));assert.equal(info.bytes,data.length);
});
