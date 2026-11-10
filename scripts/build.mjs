import {mkdir,copyFile,cp,rm} from 'node:fs/promises';
await rm('dist',{recursive:true,force:true}); await mkdir('dist',{recursive:true});
for(const f of ['index.html','styles.css','favicon.svg','app.json','LICENSE']) await copyFile(f,`dist/${f}`);
await cp('src','dist/src',{recursive:true}); await cp('vendor','dist/vendor',{recursive:true});
await cp('assets/human','dist/assets/human',{recursive:true,filter:source=>!source.endsWith('.blend')&&!source.endsWith('.blend1')});
await cp('assets/source/licenses','dist/licenses',{recursive:true});
await mkdir('dist/docs',{recursive:true});
await copyFile('docs/ASSET-LICENSES.md','dist/docs/ASSET-LICENSES.md');
console.log('Built static app in dist/');
