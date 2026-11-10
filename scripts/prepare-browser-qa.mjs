// Serve the actual app HTML with WebGL disabled for an isolated fallback test.
// Nothing is copied into dist and normal user autosave remains untouched (?qa).
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
const forceSoftware=`<base href="../"><script>const getContext=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?null:getContext.call(this,type,...args)};</script>`;
await mkdir(new URL('../artifacts/',import.meta.url),{recursive:true});
await writeFile(new URL('../artifacts/qa-software-app.html',import.meta.url),html.replace('<head>','<head>'+forceSoftware));
console.log('Prepared localhost software-only app fixture. Run /tests/browser-foundation.html?software=1.');
