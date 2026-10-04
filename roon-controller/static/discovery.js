let discoveryTab = 'recent';
let discoveryRequest = 0;
let discoveryTimer = null;
let discoveryMix = '';
let discoverySignature = '';
const discoverTabs = [['recent','RECENT'],['browse','BROWSE'],['daily','DAILY MIXES'],['releases','NEW RELEASES'],['surprise','SURPRISE']];
function initDiscover() {
  const css=document.createElement('link');css.rel='stylesheet';css.href='discovery.css?v=1104';document.head.append(css);
  const nav=document.createElement('nav');nav.id='discover-nav';nav.className='music-subnav';nav.setAttribute('aria-label','Discover');nav.hidden=true;
  for(const [id,label] of discoverTabs){const button=document.createElement('button');button.textContent=label;button.dataset.discover=id;button.onclick=()=>openDiscover(id);nav.append(button);} document.body.append(nav);
  const panel=document.createElement('section');panel.id='discovery-view';panel.className='discovery-view';panel.hidden=true;document.body.append(panel);
  const link=document.createElement('a');link.id='discover-link';link.href='#discover/recent';link.textContent='Discover';link.onclick=event=>{event.preventDefault();openDiscover('recent');};$('roon-link').after(link);
  $('roon-link').textContent='Now Playing';$('roon-link').onclick=event=>{event.preventDefault();setMusicView('now');};
}
function syncDiscoveryNavigation() {
  if(!$('discover-nav'))return;
  const exploring=musicView==='discover'||musicView==='browse';
  $('discover-nav').hidden=!exploring;$('music-nav').hidden=exploring;$('discovery-view').hidden=musicView!=='discover';
  $('browse-tab').hidden=true; $('browser-surprise').hidden=true;
  $('roon-link').classList.toggle('active',!exploring);$('discover-link').classList.toggle('active',exploring);
  $('roon-link').textContent='Now Playing';
  for(const button of $('discover-nav').children)button.classList.toggle('active',button.dataset.discover===discoveryTab);
}
function openDiscover(tab='recent', mix='', record=true) {
  if(!discoverTabs.some(([id])=>id===tab))tab='recent';
  discoveryTab=tab;discoveryMix=mix;discoverySignature='';discoveryRequest++;clearTimeout(discoveryTimer);
  setMusicView(['browse','surprise'].includes(tab)?'browse':'discover',false);
  const hash=`#discover/${tab}${mix?'?mix='+encodeURIComponent(mix):''}`;
  if(record){if(location.hash!==hash)history.pushState(null,'',hash);lastRestoredHash=hash;}
  if(tab==='browse'){browseCommand('section',{section:browserPlan.section==='search'?'albums':browserPlan.section||'albums'});return;}
  if(tab==='surprise'){browseCommand('surprise');return;}
  $('discovery-view').replaceChildren(discoveryMessage(mix?'Loading your mix…':'Loading your Roon recommendations…'));
  loadDiscover(discoveryRequest);
}
function discoveryMessage(text){const p=document.createElement('p');p.className='browser-message';p.textContent=text;return p;}
async function loadDiscover(request) {
  try {
    const section=discoveryMix?'mix':discoveryTab;
    const response=await fetch(api(`/api/discovery?section=${section}${discoveryMix?'&id='+encodeURIComponent(discoveryMix):''}`),{cache:'no-store'});
    const data=await response.json();if(!response.ok)throw new Error(data.error||'Discover is unavailable');
    if(request!==discoveryRequest||musicView!=='discover')return;
    const signature=JSON.stringify(data);if(signature!==discoverySignature){discoverySignature=signature;renderDiscover(data);}
    discoveryTimer=setTimeout(()=>loadDiscover(request),data.status==='loading'?1500:30000);
  }catch{if(request===discoveryRequest&&musicView==='discover')$('discovery-view').replaceChildren(discoveryMessage('Discover is unavailable. Your normal Roon controls are still available.'));}
}
function discoveryCard(item) {
  const card=document.createElement('button');card.className='discovery-card';card.setAttribute('aria-label',`${item.title} — ${item.artist||'Roon mix'}`);
  const art=document.createElement('span');art.className=`discovery-art${item.kind==='mix'?' mix-duotone':''}`;art.append(missingArtwork(false));
  if(item.artwork_key){const image=document.createElement('img');image.alt='';image.loading='lazy';image.src=api(`/api/discovery/image?key=${encodeURIComponent(item.artwork_key)}`);image.onerror=()=>art.replaceChildren(missingArtwork(false));art.replaceChildren(image);}
  const title=document.createElement('strong');title.textContent=item.title;
  const artist=document.createElement('small');artist.textContent=item.artist||item.context?.join(' · ')||'';
  card.append(art,title,artist);
  if(item.playedAt){const context=document.createElement('small');context.textContent=new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(item.playedAt));card.append(context);}
  card.onclick=()=>item.kind==='mix'?openDiscover('daily',item.id):openDiscoveryItem(item.key);
  return card;
}
function renderDiscover(data) {
  const panel=$('discovery-view');const scroll=panel.scrollTop;panel.replaceChildren();
  if(discoveryMix){const back=document.createElement('button');back.className='browser-back';back.textContent='BACK';back.onclick=()=>openDiscover('daily');panel.append(back);}
  if(data.status!=='ready'){panel.append(discoveryMessage(discoveryMix&&data.status==='loading'?'Loading your mix…':data.message||'Loading…'));return;}
  if(discoveryMix){const title=document.createElement('h1');title.className='mix-title';title.textContent=data.mix?.title||'Your Daily Mix';panel.append(title);}
  if(discoveryMix){const mix=discoveryMix;const controls=document.createElement('div');controls.className='mix-controls';for(const [action,label] of [['play','PLAY THIS MIX'],['queue','QUEUE THIS MIX']]){const button=document.createElement('button');button.textContent=label;button.onclick=async()=>{const buttons=[...controls.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);clearTimeout(discoveryTimer);try{const nonce=crypto.randomUUID();const response=await fetch(api('/api/discovery/mix-action'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:mix,action,nonce})});const result=await response.json();if(!response.ok)throw Error(result.error||'Request not confirmed. Check the Roon queue before retrying.');controls.append(discoveryMessage(`${action==='play'?'Play requested for':'Queued'} ${result.count} mix selections.`));}catch(error){controls.append(discoveryMessage(error.message));}finally{buttons.forEach(b=>b.disabled=false);}};controls.append(button);}panel.append(controls);}
  let content=panel;if(discoveryMix){content=document.createElement('details');const toggle=document.createElement('summary');toggle.textContent='VIEW TRACKS';content.append(toggle);panel.append(content);}
  const group=(title,items)=>{const section=document.createElement('section');if(title){const heading=document.createElement('h2');heading.className='browser-section';heading.textContent=title;section.append(heading);}const grid=document.createElement('div');grid.className='discovery-grid';for(const item of items)grid.append(discoveryCard(item));section.append(grid);content.append(section);};
  group(null,data.items||[]);
  for(const recommendation of data.groups||[]){const reason=recommendation.reason==='added'?'Because you added':recommendation.reason==='recent'?'Because you listened to':'Inspired by';group(recommendation.seed?`${reason} ${recommendation.seed.title}`:'Picked for you',recommendation.items||[]);}
  if(!data.items?.length&&!data.groups?.length)panel.append(discoveryMessage('Nothing available here yet.'));
  if(discoveryMix&&data.total>(data.items||[]).length)content.append(discoveryMessage(`Showing the first ${data.items.length} mix selections. The mix buttons request the whole mix.`));
  panel.scrollTop=scroll;
}
async function openDiscoveryItem(key, record=true, section=discoveryMix?'mix':discoveryTab, mix=discoveryMix) {
  const request=++discoveryRequest;clearTimeout(discoveryTimer);
  $('discovery-view').replaceChildren(discoveryMessage('Finding this item in Roon…'));
  try{const response=await fetch(api('/api/discovery/open'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,session:browserSession,section,id:mix})});const data=await response.json();if(!response.ok)throw new Error(data.error||'Could not open this item');if(request!==discoveryRequest||musicView!=='discover')return;
    setMusicView('browse',false);renderBrowser(data);if(record){const hash=`#discover/item?${new URLSearchParams({key,section,mix})}`;history.pushState(null,'',hash);lastRestoredHash=hash;}
  }catch(error){if(request===discoveryRequest&&musicView==='discover')$('discovery-view').replaceChildren(discoveryMessage(error.message));}
}
