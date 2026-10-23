import { chromium } from 'playwright';
import fs from 'fs';
import http from 'http';
import path from 'path';
const root = process.cwd();
const server = http.createServer((req,res)=>{ const p = path.join(root, decodeURIComponent(req.url.split('?')[0])); 
  fs.readFile(p,(e,d)=>{ if(e){res.writeHead(404);res.end();return;} const t = p.endsWith('.html')?'text/html':p.endsWith('.js')?'text/javascript':'application/octet-stream'; res.writeHead(200,{'content-type':t}); res.end(d);}); });
await new Promise(r=>server.listen(8765,r));
const scenes = JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const browser = await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page = await browser.newPage();
page.on('console', m=>{ if(m.type()==='error') console.log('console:', m.text()); });
await page.goto('http://localhost:8765/render.html');
await page.waitForFunction(()=>window.ready===true);
for (const s of scenes){
  await page.setViewportSize({width:s.size[0], height:s.size[1]});
  await page.evaluate(async (spec)=>{ await window.renderScene(spec); }, s);
  await page.screenshot({path: s.out, clip:{x:0,y:0,width:s.size[0],height:s.size[1]}});
  console.log('wrote', s.out);
}
await browser.close(); server.close();
