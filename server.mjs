import http from 'node:http';
import { readFile, stat, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {createHash} from 'node:crypto';
const qaExports=process.argv.includes('--qa-exports');
// Sparse facial targets expand on GLB export; QA captures stay bounded at 96 MiB.
const qaGLBLimit=96*1024*1024;
const root = fileURLToPath(new URL('.', import.meta.url));
const types = { '.glb':'model/gltf-binary', '.gltf':'model/gltf+json', '.bin':'application/octet-stream', '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.mjs':'text/javascript; charset=utf-8', '.svg':'image/svg+xml', '.json':'application/json; charset=utf-8', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.png':'image/png', '.webp':'image/webp' };
export const server = http.createServer(async (req, res) => {
  // Explicit, loopback-only QA capture. Off in normal app use; never in dist.
  if(qaExports && req.method==='POST' && /^\/__qa\/export\/(portrait-extreme|bald-wave|skirt-stride|skirt-neutral|skirt-trousers)\.glb$/.test(req.url)){
    if(!['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress) || req.headers.origin!==`http://${req.headers.host}`){res.writeHead(403);res.end('Local same-origin QA only');return;}
    if(Number(req.headers['content-length'])>qaGLBLimit){res.writeHead(413);res.end('QA export too large');return;}
    try{
      const chunks=[];let size=0;
      for await(const chunk of req){size+=chunk.length;if(size>qaGLBLimit){res.writeHead(413);res.end('QA export too large');return;}chunks.push(chunk);}
      const data=Buffer.concat(chunks);
      if(data.length<20||data.readUInt32LE(0)!==0x46546c67||data.readUInt32LE(4)!==2||data.readUInt32LE(8)!==data.length){res.writeHead(400);res.end('Invalid GLB');return;}
      await mkdir(path.join(root,'artifacts'),{recursive:true});const name=req.url.split('/').at(-1);await writeFile(path.join(root,'artifacts',name),data);
      res.writeHead(201,{'Content-Type':'application/json'});res.end(JSON.stringify({name,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')}));return;
    }catch{res.writeHead(500);res.end('QA capture failed');return;}
  }
  // Bounded evidence capture shares the explicit QA opt-in; exact names only.
  const evidenceNames=new Set(['skirt-controls-report.json','skirt-report.json','skirt-software-report.json','skirt-comparison.png','skirt-software.png','distinct-report.json','distinct-software-report.json','distinct-presets.png','distinct-crop.png','distinct-limits.png','distinct-software.png']);
  const evidenceName=req.url?.startsWith('/__qa/capture/')?req.url.slice('/__qa/capture/'.length):'';
  if(qaExports && req.method==='POST' && evidenceNames.has(evidenceName)) {
    let localHost=false;
    try{localHost=['127.0.0.1','localhost','[::1]'].includes(new URL(`http://${req.headers.host}`).hostname);}catch{}
    if(!localHost || !['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress) || req.headers.origin!==`http://${req.headers.host}`){res.writeHead(403);res.end('Local same-origin QA only');return;}
    const isJSON=evidenceName.endsWith('.json'),limit=(isJSON?2:8)*1024*1024;
    if(Number(req.headers['content-length'])>limit){res.writeHead(413);res.end('QA evidence too large');return;}
    try {
      const chunks=[];let size=0;
      for await(const chunk of req){size+=chunk.length;if(size>limit){res.writeHead(413);res.end('QA evidence too large');return;}chunks.push(chunk);}
      const data=Buffer.concat(chunks);let valid=false;
      if(isJSON){try{const parsed=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(data));valid=parsed!==null&&typeof parsed==='object'&&!Array.isArray(parsed);}catch{}}
      else valid=data.length>=8&&data.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex'));
      if(!valid){res.writeHead(400);res.end(isJSON?'Expected JSON object':'Expected PNG signature');return;}
      await mkdir(path.join(root,'artifacts'),{recursive:true});await writeFile(path.join(root,'artifacts',evidenceName),data);
      res.writeHead(201,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify({name:evidenceName,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')}));return;
    }catch{res.writeHead(500);res.end('QA evidence capture failed');return;}
  }
  if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405, {Allow:'GET, HEAD'}); res.end(); return; }
  try {
    const url = new URL(req.url, 'http://127.0.0.1');
    const pathname = decodeURIComponent(url.pathname);
    if (pathname.split('/').some(p => p.startsWith('.')) || pathname.includes('\\') || pathname.includes('\0')) throw new Error('invalid path');
    let file = path.resolve(root, `.${pathname}`);
    if (path.relative(root, file).startsWith('..')) throw new Error('invalid path');
    if ((await stat(file)).isDirectory()) file = path.join(file, 'index.html');
    const content = await readFile(file);
    res.writeHead(200, {'Content-Type':types[path.extname(file)] || 'application/octet-stream', 'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
    res.end(req.method === 'HEAD' ? undefined : content);
  } catch { res.writeHead(404, {'Content-Type':'text/plain'}); res.end('Not found'); }
});
const args = process.argv.slice(2);
const option = name => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
const port = Number(option('--port') || process.env.PORT || 4186);
const host = option('--host') || process.env.HOST || '127.0.0.1';
server.listen(port, host, () => console.log(`Kata Persona Forge: http://${host}:${server.address().port}`));
