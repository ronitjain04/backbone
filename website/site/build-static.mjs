import {mkdir,rm,writeFile} from 'node:fs/promises';
import {createAssets} from './assets.mjs';
const root=new URL('../public/',import.meta.url);
await rm(root,{recursive:true,force:true});
for(const [path,asset] of Object.entries(await createAssets())){
 const output=new URL('.'+path,root);
 await mkdir(new URL('.',output),{recursive:true});
 await writeFile(output,asset.encoding==='base64'?Buffer.from(asset.body,'base64'):asset.body);
}
console.log('Built public website assets: website/public');
