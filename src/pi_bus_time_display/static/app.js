const byId = id => document.getElementById(id);
const mins = n => n === 0 ? 'Due' : `${n}<small>min</small>`;
function tick(){const value=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Singapore',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date());byId('clock').textContent=value;byId('rest-clock').textContent=value}
function render(data){
  byId('roon-link').textContent=data.roon_display_name||'Roon';
  byId('app').hidden=!data.window_active;byId('resting').hidden=data.window_active;
  byId('stop').textContent=`${data.stop_name} · ${data.stop_code}`;
  byId('services').innerHTML=data.services.length?data.services.map(s=>`<article class="service service-${s.colour||({40:'blue',42:'green',401:'violet'}[s.service])||'amber'}"><span class="service-no">${s.service}</span><div class="arrivals">${s.arrivals.length?s.arrivals.map((a,i)=>`<div class="arrival ${i===0?'first':''}">${mins(a.minutes)}<small>${i===0?(a.monitored?'LIVE':'SCHEDULED'):'AFTER'}</small></div>`).join(''):'<span class="empty">No estimate</span>'}</div></article>`).join(''):'<p class="empty">No services are currently reporting.</p>';
  const label=data.status==='ok'?(data.stale?'Data is stale':'Live from LTA DataMall'):'Offline — showing last known arrivals';byId('status').textContent=label;byId('status').className=data.status==='ok'&&!data.stale?'':'offline';byId('updated').textContent=data.updated_at?`Updated ${new Date(data.updated_at).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'})}`:'';
}
async function refresh(){try{const response=await fetch('/api/status',{cache:'no-store'});render(await response.json())}catch(e){byId('status').textContent='Display service unavailable';byId('status').className='offline'}}
tick();refresh();setInterval(tick,1000);setInterval(refresh,5000);
