// Local development server, using only Node's built-in modules. No npm packages.
// It serves frontend files only. It is not the team's backend or authentication.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root=fileURLToPath(new URL('.',import.meta.url));
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.woff2':'font/woff2','.woff':'font/woff'};

export async function assetResponse(rawUrl,method='GET') {
  const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
  if(!['GET','HEAD'].includes(method))return {status:405,headers:{...headers,Allow:'GET, HEAD'},body:'Method not allowed'};
  let pathname;
  try {pathname=decodeURIComponent(new URL(rawUrl,'http://localhost').pathname);} catch {return {status:400,headers,body:'Invalid path'};}
  if(pathname==='/')pathname='/index.html';
  const path=resolve(root,'.'+pathname);
  const allowed=['/index.html','/BACKEND_CONNECT.js'].includes(pathname)||['/css/','/js/'].some(prefix=>pathname.startsWith(prefix));
  if(!allowed||pathname.includes('\\')||pathname.includes('\0')||!path.startsWith(root.endsWith(sep)?root:root+sep))return {status:404,headers,body:'Not found'};
  // Source directory allowlist prevents this server exposing other repo folders.
  if(!['.html','.css','.js','.svg','.png','.woff2','.woff'].includes(extname(path)))return {status:404,headers,body:'Not found'};
  try {
    const bytes=await readFile(path);
    return {status:200,headers:{...headers,'Content-Type':types[extname(path)],'Content-Length':bytes.length},body:method==='HEAD'?'':bytes};
  } catch {return {status:404,headers,body:'Not found'};}
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const index=process.argv.indexOf('--port');
  const port=Number(index>=0?process.argv[index+1]:5500);
  if(!Number.isInteger(port)||port<1024||port>65535)throw new Error('Choose a port between 1024 and 65535.');
  const server=createServer(async(req,res)=>{
    const result=await assetResponse(req.url,req.method);
    res.writeHead(result.status,result.headers);res.end(result.body);
  });
  server.on('error',error=>{
    console.error(error.code==='EADDRINUSE'?`Port ${port} is busy. Run: npm run dev -- --port ${port+1}`:error.message);
    process.exitCode=1;
  });
  server.listen(port,'127.0.0.1',()=>console.log(`TraceVeil: http://localhost:${port}\nPress Ctrl+C to stop.`));
}
