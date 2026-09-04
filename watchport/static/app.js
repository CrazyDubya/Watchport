const $=(id)=>document.getElementById(id);
let csrf=null;
let streaming=false;
let heartbeatTimer=null;

function b64ToBytes(v){v=v.replace(/-/g,'+').replace(/_/g,'/');v+='='.repeat((4-v.length%4)%4);return Uint8Array.from(atob(v),c=>c.charCodeAt(0));}
function bytesToB64(buf){return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');}
function prep(o){o.challenge=b64ToBytes(o.challenge);if(o.user?.id)o.user.id=b64ToBytes(o.user.id);if(o.excludeCredentials)o.excludeCredentials=o.excludeCredentials.map(c=>({...c,id:b64ToBytes(c.id)}));if(o.allowCredentials)o.allowCredentials=o.allowCredentials.map(c=>({...c,id:b64ToBytes(c.id)}));return o;}
function credentialJSON(c){const r=c.response;const out={id:c.id,rawId:bytesToB64(c.rawId),type:c.type,response:{clientDataJSON:bytesToB64(r.clientDataJSON)}};if(r.attestationObject)out.response.attestationObject=bytesToB64(r.attestationObject);if(r.authenticatorData)out.response.authenticatorData=bytesToB64(r.authenticatorData);if(r.signature)out.response.signature=bytesToB64(r.signature);if(r.userHandle)out.response.userHandle=bytesToB64(r.userHandle);if(r.getTransports)out.response.transports=r.getTransports();return out;}
async function api(path,options={}){const r=await fetch(path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(data.detail||`HTTP ${r.status}`);return data;}
function csrfHeaders(extra={}){return {'X-Watchport-CSRF':csrf,...extra};}

function setStreaming(active){
  streaming=active;
  $('startButton').hidden=active;
  $('stopButton').hidden=!active;
  $('live').textContent=active?'LIVE · VIEW ONLY':'READY';
  $('live').classList.toggle('live',active);
  if(active&&!heartbeatTimer){heartbeatTimer=setInterval(heartbeat,3000);}
  if(!active&&heartbeatTimer){clearInterval(heartbeatTimer);heartbeatTimer=null;}
}

async function status(){
  const s=await api('/api/status');
  csrf=s.csrf;
  $('health').textContent=`indicator ${s.indicatorHealthy?'ready':'offline'} · ${s.viewers} viewer${s.viewers===1?'':'s'}`;
  $('bootstrap').hidden=s.enrolled;
  $('registerButton').hidden=s.enrolled;
  $('authButton').hidden=!s.enrolled||s.authenticated;
  $('auth').hidden=s.authenticated;
  $('viewer').hidden=!s.authenticated;
  if(s.authenticated){
    const serverStreaming=s.state==='streaming';
    if(streaming&&!serverStreaming){$('stream').src='about:blank';$('streamHealth').textContent='view closed by safety watchdog';}
    setStreaming(serverStreaming);
    if(!s.streamConfigured)$('streamHealth').textContent='host/app setup required';
    else if(!s.adapterHealthy)$('streamHealth').textContent='stream adapter degraded';
    else if(!serverStreaming)$('streamHealth').textContent='';
  } else {
    setStreaming(false);
    $('stream').src='about:blank';
  }
}

async function register(){
  const token=$('bootstrapToken').value.trim();
  if(!token){$('message').textContent='Enter the one-time bootstrap token shown on the host.';return;}
  const headers={'X-Watchport-Bootstrap':token};
  try{
    const x=await api('/api/passkeys/register/options',{method:'POST',headers});
    const c=await navigator.credentials.create({publicKey:prep(x.options)});
    await api('/api/passkeys/register/verify',{method:'POST',headers,body:JSON.stringify({challengeKey:x.challengeKey,credential:credentialJSON(c)})});
    $('bootstrapToken').value='';
    $('message').textContent='Passkey enrolled. Use it to unlock Watchport.';
    await status();
  }catch(e){$('message').textContent=e.message;}
}

async function authenticate(){
  try{
    const x=await api('/api/passkeys/auth/options',{method:'POST'});
    const c=await navigator.credentials.get({publicKey:prep(x.options)});
    const result=await api('/api/passkeys/auth/verify',{method:'POST',body:JSON.stringify({challengeKey:x.challengeKey,credential:credentialJSON(c)})});
    csrf=result.csrf;
    $('message').textContent='';
    await status();
  }catch(e){$('message').textContent=e.message;}
}

async function start(){
  try{
    $('streamHealth').textContent='opening secure Viewer slot…';
    const x=await api('/api/view/start',{method:'POST',headers:csrfHeaders()});
    $('stream').src=x.viewerUrl;
    $('streamHealth').textContent='host indicator active';
    setStreaming(true);
  }catch(e){$('streamHealth').textContent=e.message;}
}

async function heartbeat(){
  if(!streaming||!csrf)return;
  try{
    await api('/api/view/heartbeat',{method:'POST',headers:csrfHeaders()});
  }catch(e){
    setStreaming(false);
    $('stream').src='about:blank';
    $('streamHealth').textContent='view revoked: '+e.message;
  }
}

async function stop(){
  try{await api('/api/view/stop',{method:'POST',headers:csrfHeaders()});}
  catch(e){$('streamHealth').textContent=e.message;return;}
  $('stream').src='about:blank';
  setStreaming(false);
  $('streamHealth').textContent='';
  await status();
}

async function logout(){
  try{await api('/api/logout',{method:'POST',headers:csrfHeaders()});}
  catch(e){$('streamHealth').textContent=e.message;return;}
  $('stream').src='about:blank';
  setStreaming(false);
  location.reload();
}

$('registerButton').onclick=register;
$('authButton').onclick=authenticate;
$('startButton').onclick=start;
$('stopButton').onclick=stop;
$('logoutButton').onclick=logout;
window.addEventListener('pagehide',()=>{if(streaming&&csrf)fetch('/api/view/stop',{method:'POST',credentials:'same-origin',keepalive:true,headers:csrfHeaders()}).catch(()=>{});});
status().catch(e=>$('message').textContent=e.message);
setInterval(()=>status().catch(()=>{}),3000);
