import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,copyFile,readFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {createHash} from 'node:crypto';

async function start(t,enabled) {
  const temp=await mkdtemp(join(tmpdir(),'persona-capture-test-'));
  await copyFile(new URL('../server.mjs',import.meta.url),join(temp,'server.mjs'));
  const child=spawn(process.execPath,['server.mjs','--port','0','--host','127.0.0.1',...(enabled?['--qa-exports']:[])],{cwd:temp,stdio:['ignore','pipe','pipe']});
  t.after(async()=>{child.kill();await new Promise(resolve=>child.exitCode!==null?resolve():child.once('exit',resolve));await rm(temp,{recursive:true,force:true});});
  const origin=await new Promise((resolve,reject)=>{let output='';child.stdout.on('data',chunk=>{output+=chunk;const match=output.match(/http:\/\/127\.0\.0\.1:\d+/);if(match)resolve(match[0]);});child.once('error',reject);child.once('exit',code=>reject(Error('Server exited '+code)));});
  const post=(name,body,headers={Origin:origin})=>fetch(origin+'/__qa/capture/'+name,{method:'POST',headers,body});
  return {origin,temp,post};
}
test('distinct evidence capture is off by default',async t=>{
  const {post}=await start(t,false);
  assert.equal((await post('distinct-report.json','{}')).status,405);
  assert.equal((await post('distinct-presets.png',Buffer.from('89504e470d0a1a0a','hex'))).status,405);
});
test('distinct capture strictly checks origin, whitelist, formats and size', {timeout:20000},async t=>{
  const {origin,temp,post}=await start(t,true);
  assert.equal((await post('distinct-report.json','{}',{})).status,403);
  assert.equal((await post('distinct-report.json','{}',{Origin:'https://example.com'})).status,403);
  assert.equal((await post('distinct-report.json','{}',{Origin:'http://evil.example',Host:'evil.example'})).status,403);
  assert.equal((await post('distinct-report.json',Buffer.from([123,34,120,34,58,34,255,34,125]))).status,400);
  const streamed=await fetch(origin+'/__qa/capture/distinct-report.json',{method:'POST',headers:{Origin:origin},duplex:'half',body:(async function*(){yield Buffer.alloc(2*1024*1024+1,32);})()});
  assert.equal(streamed.status,413);
  for(const name of ['other.json','distinct-report.json?x=1','distinct-extra.png','nested/distinct-report.json'])assert.equal((await post(name,'{}')).status,405,name);
  for(const value of ['null','[]','1','"text"','{oops'])assert.equal((await post('distinct-report.json',value)).status,400,value);
  assert.equal((await post('distinct-report.json',JSON.stringify({padding:'x'.repeat(2*1024*1024)}))).status,413);
  assert.equal((await post('distinct-presets.png','not png')).status,400);
  const huge=Buffer.alloc(8*1024*1024+1);Buffer.from('89504e470d0a1a0a','hex').copy(huge);
  assert.equal((await post('distinct-presets.png',huge)).status,413);
  for(const name of ['distinct-report.json','distinct-software-report.json']){
    const data=JSON.stringify({checks:[{pass:true}],origin});
    const response=await post(name,data);assert.equal(response.status,201);
    const receipt=await response.json();assert.equal(receipt.name,name);assert.equal(receipt.bytes,Buffer.byteLength(data));assert.equal(receipt.sha256,createHash('sha256').update(data).digest('hex'));
    assert.equal(await readFile(join(temp,'artifacts',name),'utf8'),data);
  }
  const png=Buffer.from('89504e470d0a1a0a00000000','hex');
  for(const name of ['distinct-presets.png','distinct-crop.png','distinct-limits.png','distinct-software.png']){
    const response=await post(name,png);assert.equal(response.status,201,name);
    assert.deepEqual(await readFile(join(temp,'artifacts',name)),png);
  }
});

test('QA GLB capture bounds expanded morph exports at 96 MiB before reading body',async t=>{
  const {origin}=await start(t,true);
  const {request}=await import('node:http');
  const status=await new Promise((resolve,reject)=>{
    const req=request(origin+'/__qa/export/portrait-extreme.glb',{method:'POST',headers:{Origin:origin,'Content-Length':96*1024*1024+1}},res=>{res.resume();resolve(res.statusCode);});
    req.once('error',reject);req.flushHeaders();
    req.setTimeout(2000,()=>req.destroy(Error('Server did not reject oversized Content-Length before reading body')));
  });
  assert.equal(status,413);
  // A bounded header-valid payload above the old 40 MiB cap must be accepted.
  const expanded=Buffer.alloc(41*1024*1024);expanded.writeUInt32LE(0x46546c67,0);expanded.writeUInt32LE(2,4);expanded.writeUInt32LE(expanded.length,8);
  const accepted=await fetch(origin+'/__qa/export/portrait-extreme.glb',{method:'POST',headers:{Origin:origin},body:expanded});
  assert.equal(accepted.status,201);assert.equal((await accepted.json()).bytes,expanded.length);
});

test('hair-edge evidence and GLBs use exact opt-in same-origin capture names',async t=>{
  const {origin,temp,post}=await start(t,true);
  for(const name of ['hair-edges-report.json','hair-edges-export-report.json','hair-edges-software-report.json']){
    assert.equal((await post(name,'{}',{})).status,403);
    assert.equal((await post(name,'{}')).status,201);
    assert.equal(await readFile(join(temp,'artifacts',name),'utf8'),'{}');
  }
  const png=Buffer.from('89504e470d0a1a0a00000000','hex');
  for(const name of ['hair-edges-comparison.png','hair-edges-closeup.png','hair-edges-extremes.png','hair-edges-software.png'])assert.equal((await post(name,png)).status,201,name);
  const glb=Buffer.alloc(20);glb.writeUInt32LE(0x46546c67,0);glb.writeUInt32LE(2,4);glb.writeUInt32LE(glb.length,8);
  for(const name of ['baseline','neutral','extreme','bald']){
    const path='/__qa/export/hair-edges-'+name+'.glb';
    assert.equal((await fetch(origin+path,{method:'POST',body:glb})).status,403);
    const response=await fetch(origin+path,{method:'POST',headers:{Origin:origin},body:glb});
    assert.equal(response.status,201);assert.equal((await response.json()).sha256,createHash('sha256').update(glb).digest('hex'));
  }
  for(const name of ['hair-edges-extra.png','hair-edges-report.json?x=1','nested/hair-edges-report.json'])assert.equal((await post(name,'{}')).status,405,name);
  const disabled=await start(t,false);
  assert.equal((await disabled.post('hair-edges-report.json','{}')).status,405);
  assert.equal((await fetch(disabled.origin+'/__qa/export/hair-edges-neutral.glb',{method:'POST',headers:{Origin:disabled.origin},body:glb})).status,405);
});
