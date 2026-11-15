/* Sentinel-2 reference comparison. */
(() => {
  'use strict';
  const data=globalThis.SARWatchReference,map=globalThis.SARWatchMap,$=id=>document.getElementById(id);
  if(!data||data.analysis_version!==map?.analysis()?.version)return;
  const byId=new Map(data.records.map(r=>[r.id,r]));
  const labels={optical_new_water_overlap:'Có phần giao nước mới',existing_water_only:'Nước đã có trước',no_new_water_on_clear_part:'Chưa thấy nước mới',obscured:'Mây / bóng / chưa rõ'};
  const n=(v,d=0)=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:d}).format(v);
  const elem=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
  globalThis.SARWatchReferenceUI={
    record:id=>byId.get(String(id)),
    label:id=>labels[byId.get(String(id))?.crosscheck_status]||'Chưa có tham chiếu',
    cell:id=>{const record=byId.get(String(id)),cell=elem('td');if(!record){cell.textContent='Chưa có tham chiếu';return cell;}const badge=elem('span',labels[record.crosscheck_status]);badge.className='reference-status '+record.crosscheck_status;cell.append(badge,elem('small',`${n(record.clear_fraction*100,1)}% diện tích có ảnh rõ`));return cell;},
  };
  const summary=data.summary;
  if($('reference-toggle-note'))$('reference-toggle-note').textContent=`${n(summary.with_some_clear_reference)} / ${n(summary.candidates_checked)} vùng có một phần ảnh rõ`;
  $('reference-result-summary').textContent=`Đã so sánh ${n(summary.candidates_checked)} vùng với Sentinel-2 ngày 16 và 26/10/2026.`;
  $('reference-clear-count').textContent=n(summary.with_some_clear_reference);
  $('reference-new-count').textContent=n(summary.with_any_new_water_overlap);
  $('reference-obscured-count').textContent=n(summary.with_no_clear_reference);
  $('reference-conclusion').textContent=`${n(summary.with_no_new_water_on_clear_part)} vùng chưa thấy dấu nước mới trên phần ảnh rõ; ${n(summary.with_existing_water_only)} vùng chỉ giao nước đã có trước. Tổng phần giao lớp nước mới khoảng ${n(summary.candidate_new_water_overlap_km2*1e6)} m². Các số này không xác nhận hoặc phủ định ngập tại giờ NISAR.`;
  let chosen=null,active=true;
  window.addEventListener('sarwatch:analysis',event=>{if(event.detail.version!==data.analysis_version){active=false;$('reference-summary-page').hidden=true;$('reference-summary-page').dataset.stale='true';globalThis.SARWatchReferenceUI=null;}});
  const images={};
  for(const date of ['before','after']){const image=new Image();image.onload=()=>{images[date]=image;if(chosen)draw(date,chosen);};image.src=data.images[date].data_url;}
  function rings(geometry){return geometry.type==='Polygon'?geometry.coordinates:geometry.type==='MultiPolygon'?geometry.coordinates.flat():[];}
  function draw(date,feature){
    const image=images[date];if(!image)return;
    const canvas=$('reference-'+date),ctx=canvas.getContext('2d');if(!ctx)return;
    const coordinates=rings(feature.geometry).flat().map(map.project);if(!coordinates.length)return;
    let xmin=Infinity,ymin=Infinity,xmax=-Infinity,ymax=-Infinity;
    coordinates.forEach(([x,y])=>{xmin=Math.min(xmin,x);xmax=Math.max(xmax,x);ymin=Math.min(ymin,y);ymax=Math.max(ymax,y);});
    const size=Math.max(40,Math.max(xmax-xmin,ymax-ymin)*1.7),cx=(xmin+xmax)/2,cy=(ymin+ymax)/2;
    const left=cx-size/2,top=cy-size/2;
    const [[south,west],[north,east]]=data.images[date].bounds;
    const [sceneX,sceneY]=map.project([west,north]),[endX,endY]=map.project([east,south]);
    const sx=(left-sceneX)/(endX-sceneX)*image.width,sy=(top-sceneY)/(endY-sceneY)*image.height;
    const sw=size/(endX-sceneX)*image.width,sh=size/(endY-sceneY)*image.height;
    ctx.fillStyle='#e8ede2';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.imageSmoothingEnabled=false;
    ctx.drawImage(image,sx,sy,sw,sh,0,0,canvas.width,canvas.height);
    ctx.strokeStyle='#ffd36e';ctx.lineWidth=2;
    rings(feature.geometry).forEach(ring=>{ctx.beginPath();ring.forEach((c,i)=>{const[x,y]=map.project(c),px=(x-left)/size*canvas.width,py=(y-top)/size*canvas.height;if(i)ctx.lineTo(px,py);else ctx.moveTo(px,py);});ctx.closePath();ctx.stroke();});
  }
  window.addEventListener('sarwatch:region-selected',event=>{
    if(!active)return;
    chosen=event.detail;const record=byId.get(String(chosen.properties.id));if(!record)return;
    $('reference-selected').hidden=false;
    $('reference-selected-status').textContent=labels[record.crosscheck_status];
    $('reference-selected-status').className='reference-status '+record.crosscheck_status;
    $('reference-selected-detail').textContent=`Ảnh rõ trên ${n(record.clear_fraction*100,1)}% vùng. Diện tích giao lớp nước mới: ${n(record.new_water_overlap_m2)} m²; giao nước đã có trước: ${n(record.existing_water_overlap_m2)} m².`;
    $('detail-reference').textContent=labels[record.crosscheck_status];
    draw('before',chosen);draw('after',chosen);
  });
})();
