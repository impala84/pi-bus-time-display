// Sign-in uses only the public appearance setting, never private configuration.
fetch('/api/status', {cache:'no-store'}).then(response=>response.json()).then(data=>{
  document.body.dataset.theme=data.display_theme==='roon'?'roon':'fresh-mint';
}).catch(()=>{});
