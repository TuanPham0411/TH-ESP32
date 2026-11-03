import {build} from 'esbuild';
import {mkdir,readFile,readdir,rm,writeFile} from 'node:fs/promises';
import path from 'node:path';
const out='../app/static/vendor';
await rm(out,{recursive:true,force:true});await mkdir(out,{recursive:true});
const result=await build({entryPoints:['installer.js'],bundle:true,minify:true,format:'esm',splitting:true,outdir:out,chunkNames:'chunks/[name]-[hash]',legalComments:'linked',metafile:true});
const packages=new Set();
for(const input of Object.keys(result.metafile.inputs)){
 const parts=input.split('/');const index=parts.lastIndexOf('node_modules');if(index<0)continue;
 const count=parts[index+1].startsWith('@')?3:2;packages.add(parts.slice(0,index+count).join('/'));
}
// dist/web is prebundled upstream; preserve its runtime dependency notices too.
async function visit(directory){
 const pkg=JSON.parse(await readFile(path.join(directory,'package.json'),'utf8'));
 for(const name of Object.keys(pkg.dependencies||{})){
  let parent=path.resolve(directory),found;
  while(true){
   const candidate=path.join(parent,'node_modules',name);
   try{await readFile(path.join(candidate,'package.json'));found=candidate;break}catch{}
   const next=path.dirname(parent);if(next===parent)break;parent=next;
  }
  if(!found)throw new Error('Missing runtime dependency '+name);
  if(!packages.has(found)){packages.add(found);await visit(found)}
 }
}
await visit('node_modules/esp-web-tools');
const records=[];
for(const directory of packages){
 const pkg=JSON.parse(await readFile(path.join(directory,'package.json'),'utf8'));
 const texts=[];
 for(const file of (await readdir(directory)).filter(name=>/^(license|licence|notice|copying)(\.|$)/i.test(name)).sort())texts.push(await readFile(path.join(directory,file),'utf8'));
 records.push({id:pkg.name+'@'+pkg.version,text:`${pkg.name} ${pkg.version}\nLicense: ${pkg.license||'See bundled licence text'}\n`+texts.join('\n')});
}
records.sort((a,b)=>a.id.localeCompare(b.id,'en'));
await writeFile(path.join(out,'THIRD_PARTY_NOTICES.txt'),records.map(record=>record.text).join('\n\n----------------------------------------\n\n').replace(/\r\n/g,'\n'));
console.log(`Bundled installer and notices for ${records.length} runtime packages.`);
