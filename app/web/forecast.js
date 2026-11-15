/* Hourly rainfall forecasts and accumulation windows. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const sites = {hue:[16.4637,107.5909],northwest:[16.54,107.50],coast:[16.53,107.65],south:[16.36,107.65]};
  let current=null, horizon=12, busy=false, controller=null;
  const formatTime=t=>new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'}).format(new Date(t*1000));
  function windowTotal(data,start,hours){
    const end=start+hours*3600;let total=0,coverage=0;
    data.hourly.time.forEach((t,i)=>{const v=data.hourly.precipitation[i],n=Math.max(0,Math.min(t,end)-Math.max(t-3600,start));if(n&&Number.isFinite(v)&&v>=0){total+=v*n/3600;coverage+=n;}});
    return coverage===hours*3600?total:null;
  }
  async function getJSON(url){const r=await fetch(url,{signal:controller.signal,cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}
  async function refresh(){
    if(busy)return;busy=true;controller=new AbortController();const timer=setTimeout(()=>controller.abort(),20000);
    $('refresh').disabled=true;$('site').disabled=true;current=null;render();$('status').className='status';$('status').textContent='Đang lấy dự báo mới cho điểm đã chọn…';
    try{
      const site=$('site').value;let record;
      if(location.protocol!=='file:'){
        try{record=await getJSON('/api/weather?site='+site);}catch(e){if(controller.signal.aborted)throw e;}
      }
      if(!record){
        const [lat,lon]=sites[site];const query=new URLSearchParams({latitude:lat,longitude:lon,hourly:'precipitation',models:'ecmwf_ifs',forecast_days:3,timezone:'Asia/Ho_Chi_Minh',timeformat:'unixtime'});
        const data=await getJSON('https://api.open-meteo.com/v1/forecast?'+query);
        record={data,retrieved_at:Math.floor(Date.now()/1000),source:'Open-Meteo / ECMWF IFS',browser_direct:true};
      }
      const d=record.data,h=d.hourly;
      if(d.hourly_units?.precipitation!=='mm'||!Array.isArray(h?.time)||!h.time.length||h.time.length!==h.precipitation?.length||h.time.some((t,i)=>!Number.isFinite(t)||(i&&t-h.time[i-1]!==3600))||h.precipitation.some(v=>v!==null&&(!Number.isFinite(v)||v<0)))throw new Error('Dữ liệu không hợp lệ');
      current=record;render();
    }catch(e){$('status').className='status error';$('status').textContent='Không lấy được dự báo. Thử lại sau; thiếu dữ liệu không có nghĩa là an toàn.';}
    finally{clearTimeout(timer);busy=false;$('refresh').disabled=false;$('site').disabled=false;}
  }
  function render(){
    $('chart').replaceChildren();$('five').textContent='—';$('twelve').textContent='—';$('window').textContent='Chưa có dữ liệu';$('watch-result').textContent='Chưa đủ dữ liệu để đối chiếu.';
    if(!current)return;
    const now=Math.floor(Date.now()/1000),age=now-current.retrieved_at;
    if(age>1800){$('status').className='status error';$('status').textContent='Dự báo đã quá 30 phút kể từ lần tải. Đang chờ cập nhật; không hiển thị số cũ như dữ liệu mới.';return;}
    const totals={5:windowTotal(current.data,now,5),12:windowTotal(current.data,now,12)};
    [5,12].forEach(h=>$(h===5?'five':'twelve').textContent=totals[h]===null?'—':totals[h].toFixed(1));
    $('status').className='status';$('status').textContent=`${current.source} · Cập nhật ${formatTime(current.retrieved_at)} (giờ Việt Nam). Dự báo theo ô lưới.`;
    $('window').textContent=formatTime(now)+' → '+formatTime(now+horizon*3600);
    const points=current.data.hourly.time.map((t,i)=>({t,v:current.data.hourly.precipitation[i]})).filter(p=>p.t>now&&p.t<=now+(horizon+1)*3600);
    const maximum=Math.max(1,...points.map(p=>p.v??0));
    points.forEach(p=>{const col=document.createElement('div');col.className='bar-col';const amount=document.createElement('span');amount.className='amount';amount.textContent=p.v===null?'Thiếu':p.v.toFixed(1);const bar=document.createElement('div');bar.className='bar';bar.style.height=(p.v===null?0:180*p.v/maximum)+'px';const tick=document.createElement('span');tick.className='tick';tick.textContent=new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit'}).format(new Date(p.t*1000));col.append(amount,bar,tick);$('chart').append(col);});
    const limit=Number($('watch-threshold').value),value=totals[horizon];
    $('watch-result').textContent=!Number.isFinite(limit)||limit<=0?'Nhập ngưỡng theo dõi lớn hơn 0.':value===null?'Thiếu giờ dự báo trong cửa sổ này.':value>=limit?`Vượt ngưỡng theo dõi tự chọn: ${value.toFixed(1)} / ${limit} mm trong ${horizon} giờ. Theo dõi thông báo chính thức.`:`Dưới ngưỡng mưa tự chọn: ${value.toFixed(1)} / ${limit} mm. Chưa có kết luận về ngập.`;
    $('grid').textContent=`Ô mô hình trả về: ${current.data.latitude.toFixed(3)}°N, ${current.data.longitude.toFixed(3)}°E.`;
    $('archive-note').textContent=current.browser_direct?'Đang truy cập trực tiếp từ trình duyệt; không có lưu trữ tự động. Chạy start.bat để lưu các bản dự báo phục vụ kiểm định.':'Máy chủ lưu bản dự báo tại thời điểm tải để đối chiếu quan trắc về sau.';
  }
  $('site').addEventListener('change',refresh);$('refresh').addEventListener('click',refresh);$('watch-threshold').addEventListener('input',render);
  document.querySelectorAll('[data-hours]').forEach(b=>b.addEventListener('click',()=>{horizon=Number(b.dataset.hours);document.querySelectorAll('[data-hours]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});render();}));
  setInterval(refresh,15*60*1000);setInterval(()=>{if(current)render();},60000);refresh();
})();
