/* Actual provider payload, fixed test clock; tests UI behavior, not forecast accuracy. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');

const root=path.resolve(__dirname,'../..');
const jsdomPath=require.resolve('jsdom',{paths:[path.join(root,'dev')]});
assert.ok(jsdomPath.startsWith(path.join(root,'dev','node_modules')+path.sep),'Run npm ci inside this repository; external node_modules is not allowed.');
const {JSDOM}=require(jsdomPath);
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/provider_forecast.json'),'utf8'));
(async()=>{
 const dom=new JSDOM(fs.readFileSync(path.join(root,'app/standalone','index.html'),'utf8'),{url:'file:///SARWatch.html',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,d=w.document,clock=fixture.data.hourly.time[12];
 w.Date.now=()=>clock*1000;
 w.ResizeObserver=class{observe(){}};
 w.URL.createObjectURL=()=> 'blob:test';w.URL.revokeObjectURL=()=>{};
 w.fetch=async()=>({ok:true,json:async()=>fixture.data});
 Object.defineProperty(w.HTMLElement.prototype,'clientWidth',{get:()=>1000});
 Object.defineProperty(w.HTMLElement.prototype,'clientHeight',{get:()=>650});
 for(const script of d.querySelectorAll('script'))w.eval(script.textContent);
 for(let i=0;i<40&&!/^\d+\.\d$/.test(d.querySelector('#five').textContent);i++)await new Promise(r=>setTimeout(r,40));
 assert.match(d.querySelector('#five').textContent,/^\d+\.\d$/);
 assert.match(d.querySelector('#twelve').textContent,/^\d+\.\d$/);
 assert.ok(d.querySelectorAll('#chart .bar-col').length>=12);
 assert.match(d.querySelector('#status').textContent,/ECMWF IFS/);
 assert.ok(d.querySelector('#window').textContent.includes('→'));
 assert.equal(d.querySelector('#status').classList.contains('error'),false);
 // Expired data must not remain visible as a fresh forecast.
 w.Date.now=()=> (clock+1900)*1000;
 d.querySelector('#watch-threshold').dispatchEvent(new w.Event('input'));
 assert.match(d.querySelector('#five').textContent,/^[—-]$/);
 assert.match(d.querySelector('#twelve').textContent,/^[—-]$/);
 assert.equal(d.querySelector('#status').classList.contains('error'),true);
 dom.window.close();
 console.log('PASS: actual provider payload renders 5/12-hour forecasts; stale data is hidden. DOM-only, not accuracy verification.');
})().catch(e=>{console.error(e);process.exit(1);});
