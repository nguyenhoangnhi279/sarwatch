/* Review support from real NISAR, WorldPop and OpenStreetMap intersections. */
(() => {
  'use strict';
  const $=id=>document.getElementById(id), ns='http://www.w3.org/2000/svg';
  const impact=globalThis.SARWatchImpact, map=globalThis.SARWatchMap;
  if(!impact||!map||impact.analysis_version!==map.analysis()?.version)return;
  const features=impact.geojson.features, byId=new Map(features.map(f=>[String(f.properties.id),f]));
  const n=(v,d=0)=>new Intl.NumberFormat('vi-VN',{maximumFractionDigits:d}).format(v);
  const people=v=>v===null?'Chưa rõ':v>0&&v<1?'< 1':`≈ ${n(v)}`;
  const kind={hospital:'Bệnh viện',clinic:'Cơ sở y tế',school:'Trường học',kindergarten:'Mầm non',fire_station:'Trạm cứu hỏa',police:'Công an'};
  let selected=null,limit=15,valid=true;
  function element(tag,className,text){const e=document.createElement(tag);if(className)e.className=className;if(text!==undefined)e.textContent=text;return e;}
  function svg(tag,attrs){const e=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,String(v));return e;}
  function reason(p){const parts=[];if(p.facility_count)parts.push(`${p.facility_count} cơ sở thiết yếu giao vùng`);if((p.population_estimate||0)>0)parts.push(`${people(p.population_estimate)} người trên phần lưới hợp lệ`);if(p.road_length_m>0)parts.push(`${n(p.road_length_m)} m đường giao cắt`);return parts.join(' · ')||'Chỉ dấu radar; cần bổ sung bằng chứng phơi nhiễm';}
  function renderList(){
    if(!valid)return;
    const query=$('review-search').value.normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase().trim();
    const filter=$('review-filter').value;
    const visible=features.filter(f=>{
      const p=f.properties,text=[String(p.id),...p.road_names,...p.facilities.map(f=>f.name)].join(' ').normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase();
      const reference=globalThis.SARWatchReferenceUI?.record(p.id);
      const matches=filter==='all'||(filter==='optical_overlap'&&reference?.crosscheck_status==='optical_new_water_overlap')||(filter==='optical_obscured'&&reference?.crosscheck_status==='obscured');
      return (!query||text.includes(query))&&matches;
    });
    const fragment=document.createDocumentFragment();
    visible.slice(0,limit).forEach(f=>{
      const p=f.properties,id=String(p.id),row=element('tr',selected===id?'selected':'');
      const rank=element('td','review-rank',String(p.review_rank).padStart(2,'0'));
      const loc=element('td','');const button=element('button','review-location',`Vùng ${id.padStart(3,'0')}`);button.type='button';button.addEventListener('click',()=>map.select(id));
      loc.append(button,element('small','review-road-name',p.road_names.slice(0,2).join(', ')||'Chưa có tên đường giao cắt'));
      const population=element('td','',people(p.population_estimate));if(p.population_status==='partial')population.append(element('small','','Lưới phủ một phần'));
      const road=element('td','',p.infrastructure_status==='partial'&&p.road_length_m===0?'Chưa đủ dữ liệu':`${n(p.road_length_m)} m`);
      const reference=globalThis.SARWatchReferenceUI?.cell(id)||element('td','','Chưa có tham chiếu');
      row.append(rank,loc,population,road,reference);fragment.append(row);
    });
    $('review-table-body').replaceChildren(fragment);$('review-results').textContent=`${n(visible.length)} vị trí`;
    $('review-more').hidden=visible.length<=limit;
  }
  function select(feature){
    if(!valid)return;
    selected=String(feature.properties.id);const f=byId.get(selected);if(!f)return;
    const p=f.properties;
    $('review-selection-empty').hidden=true;$('review-selection').hidden=false;
    $('review-selected-title').textContent=`Vùng ${selected.padStart(3,'0')}`;
    $('review-selected-rank').textContent=`Thứ tự xem: ${p.review_rank} / ${n(features.length)}`;
    $('review-reason').textContent=reason(p);
    $('review-coordinates').textContent=`${p.review_latitude.toFixed(5)}° B, ${p.review_longitude.toFixed(5)}° Đ`;
    $('review-population-note').textContent=p.population_estimate===null?'Chưa có dữ liệu dân số hợp lệ cho vùng này.':`WorldPop 2026 có giá trị hợp lệ trên ${n(p.population_valid_area_fraction*100,1)}% diện tích vùng. Phần còn lại chưa rõ; không phải số người đang bị ngập.`;
    const list=document.createDocumentFragment();
    (p.nearby_facilities||[]).forEach(f=>{const item=element('li','',`${f.name||kind[f.kind]||'Cơ sở OSM'} · ${n(f.distance_m)} m`);list.append(item);});
    if(!p.nearby_facilities?.length)list.append(element('li','','Chưa ghi nhận cơ sở có nhãn phù hợp trong phạm vi 500 m của dữ liệu OSM.'));
    $('review-nearby').replaceChildren(list);
    $('detail-priority').textContent=String(p.review_rank);
    $('detail-population').textContent=people(p.population_estimate);
    $('detail-road-length').textContent=`${n(p.road_length_m)} m`;
    $('detail-coordinates').textContent=`${p.review_latitude.toFixed(5)}° B, ${p.review_longitude.toFixed(5)}° Đ`;
    renderList();
  }
  function linePath(geom){
    if(geom.type==='LineString')return geom.coordinates.map((c,i)=>{const[x,y]=map.project(c);return`${i?'L':'M'}${x},${y}`;}).join(' ');
    if(geom.type==='MultiLineString')return geom.coordinates.map(c=>linePath({type:'LineString',coordinates:c})).join(' ');
    if(geom.type==='GeometryCollection')return geom.geometries.map(linePath).join(' ');
    return '';
  }
  const popGroup=$('population-layer'),roadGroup=$('road-layer'),facilityGroup=$('facility-layer');
  const popFragment=document.createDocumentFragment();
  impact.population_cells.features.forEach(f=>{const ring=f.geometry.coordinates[0];const d=ring.map((c,i)=>{const[x,y]=map.project(c);return`${i?'L':'M'}${x},${y}`;}).join(' ')+'Z';const path=svg('path',{d,fill:'#8b77c8','fill-opacity':Math.min(.7,.15+Math.log1p(f.properties.people_in_cell)/10),'pointer-events':'none'});const title=svg('title',{});title.textContent=`WorldPop: ${n(f.properties.people_in_cell,1)} người/ô (ước tính)`;path.append(title);popFragment.append(path);});
  popGroup.replaceChildren(popFragment);
  const roadFragment=document.createDocumentFragment();
  impact.roads.features.forEach(f=>{const path=svg('path',{d:linePath(f.geometry),fill:'none',stroke:'#47c9d7','stroke-width':2,'vector-effect':'non-scaling-stroke','pointer-events':'none'});roadFragment.append(path);});roadGroup.replaceChildren(roadFragment);
  const facilityFragment=document.createDocumentFragment();
  impact.facilities.features.forEach(f=>{const c=f.properties.display_point||f.geometry.coordinates;if(!Array.isArray(c)||!Number.isFinite(c[0]))return;const[x,y]=map.project(c);const p=svg('path',{d:`M${x} ${y}h0`,stroke:'#e6f3ff','stroke-width':7,'stroke-linecap':'round','vector-effect':'non-scaling-stroke','pointer-events':'none'});facilityFragment.append(p);});facilityGroup.replaceChildren(facilityFragment);
  function toggleLayers(){popGroup.style.display=$('show-population').checked?'':'none';roadGroup.style.display=$('show-roads').checked?'':'none';facilityGroup.style.display=$('show-facilities').checked?'':'none';}
  ['show-population','show-roads','show-facilities'].forEach(id=>$(id).addEventListener('change',toggleLayers));toggleLayers();
  $('review-population-total').textContent=people(impact.summary.population_estimate_partial);
  $('review-roads-total').textContent=n(impact.summary.road_length_m/1000,1);
  $('review-coverage-note').textContent=`Dân số tính trên phần lưới hợp lệ (${n(impact.summary.population_valid_candidate_area_fraction*100,1)}% diện tích ứng viên). Không phải số nạn nhân hoặc đường bị phong tỏa.`;
  $('review-source-summary').textContent=`WorldPop 2026 · OSM ${impact.sources.osm.retrieved_at.slice(0,10)} · ${n(impact.summary.regions_with_road_overlap)} vùng có đường giao cắt`;
  window.addEventListener('sarwatch:region-selected',event=>select(event.detail));
  window.addEventListener('sarwatch:analysis',event=>{
    if(event.detail.version===impact.analysis_version)return;
    valid=false;$('review-workspace').dataset.stale='true';$('review-workspace').hidden=true;
    $('review-population-total').textContent='—';$('review-roads-total').textContent='—';
    $('review-coverage-note').textContent='Quan sát đã đổi phiên bản. Cần tính lại phơi nhiễm trước khi sử dụng danh sách kiểm chứng.';
    popGroup.replaceChildren();roadGroup.replaceChildren();facilityGroup.replaceChildren();
  });
  $('review-search').addEventListener('input',()=>{limit=15;renderList();});$('review-filter').addEventListener('change',()=>{limit=15;renderList();});$('review-more').addEventListener('click',()=>{limit+=20;renderList();});
  $('review-compare').addEventListener('click',()=>{if(selected){map.compare(selected);$('map-page').scrollIntoView?.({behavior:'smooth'});}});
  $('detail-review').addEventListener('click',()=>$('review-workspace').scrollIntoView?.({behavior:'smooth'}));
  $('open-review-list').addEventListener('click',()=>$('review-workspace').scrollIntoView?.({behavior:'smooth'}));
  function csvCell(value){let s=String(value??'');if(/^[=+@\-\t\r]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';}
  $('review-export').addEventListener('click',()=>{
    const rows=[['Thu_tu','Ma_vung','Vi_do','Kinh_do','Dien_tich_m2','Dan_so_uoc_tinh_phan_luoi_hop_le','Ty_le_dien_tich_co_du_lieu_dan_so','Duong_giao_cat_m','Co_so_giao_vung','Du_lieu_ha_tang','Ly_do_xem_truoc','Doi_chieu_Sentinel2','Ty_le_anh_ro','Giao_lop_nuoc_moi_m2','Phien_ban_quan_sat']];
    features.forEach(f=>{const p=f.properties,reference=globalThis.SARWatchReferenceUI?.record(p.id);rows.push([p.review_rank,p.id,p.review_latitude,p.review_longitude,p.area_m2,p.population_estimate,p.population_valid_area_fraction,p.road_length_m,p.facility_count,p.infrastructure_status,reason(p),globalThis.SARWatchReferenceUI?.label(p.id)||'',reference?.clear_fraction,reference?.new_water_overlap_m2,impact.analysis_version]);});
    const blob=new Blob(['\ufeff'+rows.map(row=>row.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='SARWatch_danh_sach_kiem_chung_Hue.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  renderList();
})();
