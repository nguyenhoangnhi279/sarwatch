/** Reproducible, resumable OSM fallback collector. Low concurrency: one request. */
import fs from 'node:fs/promises';

export async function collectBatch(root, count=5) {
  const base = root+'/data/inputs/auxiliary';
  await fs.mkdir(base+'/osm', {recursive:true});
  let records;
  try { records=JSON.parse(await fs.readFile(base+'/osm_collection.json','utf8')); }
  catch { records=JSON.parse(await fs.readFile(base+'/osm_jobs.json','utf8')).map(j=>({...j,status:'pending'})); }
  let processed=0;
  for(let index=0;index<records.length && processed<count;index++) {
    const job=records[index];
    if(job.status!=='pending')continue;
    processed++;
    const url='https://api.openstreetmap.org/api/0.6/map?bbox='+job.bbox.map(v=>v.toFixed(8)).join(',');
    try {
      const r=await fetch(url,{headers:{'User-Agent':'SARWatch/1.0 (NASA Space Apps research)','Accept':'application/xml'},signal:AbortSignal.timeout(12000)});
      const body=await r.text();
      if(r.status===429){await fs.writeFile(base+'/osm_collection.json',JSON.stringify(records,null,2));return {rate_limited:true,retry_after:r.headers.get('retry-after')};}
      if(r.status===400 && (job.depth||0)<2 && /too many|maximum|50000/i.test(body)){
        job.status='subdivided';const [w,s,e,n]=job.bbox,mx=(w+e)/2,my=(s+n)/2;
        [[w,s,mx,my],[mx,s,e,my],[w,my,mx,n],[mx,my,e,n]].forEach((bbox,i)=>records.push({id:job.id+'_'+i,bbox,depth:(job.depth||0)+1,status:'pending'}));
      } else {
        if(!r.ok||!body.includes('<osm '))throw Error('HTTP '+r.status+' '+body.slice(0,120));
        await fs.writeFile(base+'/osm/'+job.id+'.osm',body);
        job.status='ok';job.bytes=Buffer.byteLength(body);job.retrieved_at=new Date().toISOString();job.url=url;
      }
    } catch(e) {job.status='failed';job.error=String(e);}
    await fs.writeFile(base+'/osm_collection.json',JSON.stringify(records,null,2));
    await new Promise(resolve=>setTimeout(resolve,250));
  }
  return {ok:records.filter(j=>j.status==='ok').length,pending:records.filter(j=>j.status==='pending').length,failed:records.filter(j=>j.status==='failed').length,processed};
}
