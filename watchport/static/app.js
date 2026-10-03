const $ = (id) => document.getElementById(id);
let csrf = null;
let streaming = false;
let wantsView = false;
let opening = false;
let statusBusy = false;
let epoch = 0;
let reconnectAttempts = 0;
let reconnectTimer = null;

function b64ToBytes(v){v=v.replace(/-/g,'+').replace(/_/g,'/');v+='='.repeat((4-v.length%4)%4);return Uint8Array.from(atob(v),c=>c.charCodeAt(0));}
function bytesToB64(buf){return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');}
function prep(o){o.challenge=b64ToBytes(o.challenge);if(o.user?.id)o.user.id=b64ToBytes(o.user.id);if(o.excludeCredentials)o.excludeCredentials=o.excludeCredentials.map(c=>({...c,id:b64ToBytes(c.id)}));if(o.allowCredentials)o.allowCredentials=o.allowCredentials.map(c=>({...c,id:b64ToBytes(c.id)}));return o;}
function credentialJSON(c){const r=c.response;const out={id:c.id,rawId:bytesToB64(c.rawId),type:c.type,response:{clientDataJSON:bytesToB64(r.clientDataJSON)}};if(r.attestationObject)out.response.attestationObject=bytesToB64(r.attestationObject);if(r.authenticatorData)out.response.authenticatorData=bytesToB64(r.authenticatorData);if(r.signature)out.response.signature=bytesToB64(r.signature);if(r.userHandle)out.response.userHandle=bytesToB64(r.userHandle);if(r.getTransports)out.response.transports=r.getTransports();return out;}
async function api(path, options = {}) {
  const response = await fetch(path, {credentials: 'same-origin', ...options,
    headers: {'Content-Type': 'application/json', ...(options.headers || {})}});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return data;
}
const csrfHeaders = () => ({'X-Watchport-CSRF': csrf});
function message(text) { $('streamHealth').textContent = text; }
function setState(label, detail = '') {
  $('live').textContent = label;
  message(detail);
  $('startButton').hidden = streaming || opening;
  $('stopButton').hidden = !streaming && !opening;
  $('fullscreenButton').disabled = !streaming;
  $('reconnectButton').hidden = !streaming;
}
function clearFrame() {
  streaming = false;
  $('stream').src = 'about:blank';
}
function cancelReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = null;
}
async function revoke() {
  if (csrf) await api('/api/view/stop', {method: 'POST', headers: csrfHeaders()});
}
async function status() {
  if (statusBusy) return;
  statusBusy = true;
  const generation = epoch;
  try {
    const s = await api('/api/status');
    if (generation !== epoch) return;
    csrf = s.csrf;
    $('health').textContent = `${s.indicatorHealthy ? 'Host ready' : 'Host warning offline'} · ${s.viewers} viewer${s.viewers === 1 ? '' : 's'}`;
    $('bootstrap').hidden = s.enrolled;
    $('registerButton').hidden = s.enrolled;
    $('authButton').hidden = !s.enrolled || s.authenticated;
    $('auth').hidden = s.authenticated;
    $('viewer').hidden = !s.authenticated;
    if (!s.authenticated) {
      wantsView = false;
      epoch++;
      cancelReconnect();
      clearFrame();
      setState('LOCKED');
      return;
    }
    if (opening) return;
    if (s.state === 'streaming' && (!wantsView || document.hidden)) {
      clearFrame();
      await revoke();
      setState('PAUSED', 'Open the desktop when you are ready.');
    } else if (streaming && s.state !== 'streaming') {
      clearFrame();
      wantsView = false;
      setState('CLOSED', 'The host closed this view. Open it again to request access.');
    } else if (!streaming && !wantsView) {
      setState('READY', !s.streamConfigured ? 'Desktop setup is required on the host.' :
        !s.adapterHealthy ? 'Host cleanup is pending. Viewing is unavailable.' : '');
    }
  } finally { statusBusy = false; }
}
async function register() {
  const token = $('bootstrapToken').value.trim();
  if (!token) { $('message').textContent = 'Enter the one-time token shown on the host.'; return; }
  const headers = {'X-Watchport-Bootstrap': token};
  try {
    const x = await api('/api/passkeys/register/options', {method: 'POST', headers});
    const c = await navigator.credentials.create({publicKey: prep(x.options)});
    await api('/api/passkeys/register/verify', {method: 'POST', headers,
      body: JSON.stringify({challengeKey: x.challengeKey, credential: credentialJSON(c)})});
    $('bootstrapToken').value = '';
    $('message').textContent = 'Passkey enrolled. Unlock Watchport to continue.';
    await status();
  } catch (error) { $('message').textContent = error.message; }
}
async function authenticate() {
  try {
    const x = await api('/api/passkeys/auth/options', {method: 'POST'});
    const c = await navigator.credentials.get({publicKey: prep(x.options)});
    const result = await api('/api/passkeys/auth/verify', {method: 'POST',
      body: JSON.stringify({challengeKey: x.challengeKey, credential: credentialJSON(c)})});
    csrf = result.csrf;
    $('message').textContent = '';
    await status();
  } catch (error) { $('message').textContent = error.message; }
}
async function start(automatic = false) {
  if (opening || document.hidden || !navigator.onLine) return;
  if (!automatic) { wantsView = true; reconnectAttempts = 0; }
  if (!wantsView) return;
  opening = true;
  const generation = ++epoch;
  setState('CONNECTING', 'Waiting for the host warning…');
  try {
    const x = await api('/api/view/start', {method: 'POST', headers: csrfHeaders()});
    if (generation !== epoch || document.hidden || !navigator.onLine || !wantsView) {
      await revoke();
      return;
    }
    $('stream').src = x.viewerUrl;
    streaming = true;
    reconnectAttempts = 0;
    setState('VIEW OPEN', 'Choose quality and join in the player below.');
    $('admissionTime').textContent = `Access granted in ${(x.admissionMs / 1000).toFixed(1)}s`;
  } catch (error) {
    clearFrame();
    if (error.status) {
      wantsView = false;
      setState('UNAVAILABLE', error.message);
      if (error.status === 401) await status();
    } else {
      setState('CONNECTION LOST', 'Waiting for the network…');
      scheduleReconnect();
    }
  } finally {
    opening = false;
    $('startButton').hidden = streaming;
    $('stopButton').hidden = !streaming;
  }
}
function scheduleReconnect() {
  if (!wantsView || document.hidden || !navigator.onLine || reconnectTimer) return;
  if (reconnectAttempts >= 3) {
    wantsView = false;
    setState('DISCONNECTED', 'Open the desktop to try again.');
    return;
  }
  const delay = 1000 * (2 ** reconnectAttempts++);
  reconnectTimer = setTimeout(async () => {
    reconnectTimer = null;
    if (!wantsView || document.hidden) return;
    try {
      // Always revoke the old grant and request fresh admission before a retry.
      await revoke();
      await start(true);
    } catch (error) {
      if (error.status) { wantsView = false; setState('CLOSED', error.message); }
      else scheduleReconnect();
    }
  }, delay);
}
async function heartbeat() {
  if (!streaming || !wantsView || document.hidden || !csrf) return;
  try { await api('/api/view/heartbeat', {method: 'POST', headers: csrfHeaders()}); }
  catch (error) {
    clearFrame();
    if (error.status) {
      wantsView = false;
      setState('CLOSED', 'Viewing authorization ended. Open the desktop to continue.');
    } else { setState('CONNECTION LOST', 'Reconnecting securely…'); scheduleReconnect(); }
  }
}
async function stop() {
  wantsView = false;
  epoch++;
  cancelReconnect();
  clearFrame();
  setState('CLOSING', 'Confirming the host stopped this view…');
  try { await revoke(); setState('READY'); return true; }
  catch (error) { setState('DISCONNECTED', 'Stop is not yet confirmed. The host watchdog will reclaim the view.'); return false; }
}
function pause() {
  const active = streaming || opening || wantsView;
  wantsView = false;
  epoch++;
  cancelReconnect();
  clearFrame();
  setState('PAUSED', 'Open the desktop to resume.');
  if (active && csrf) fetch('/api/view/stop', {method: 'POST', credentials: 'same-origin',
    keepalive: true, headers: csrfHeaders()}).catch(() => {});
}
async function logout() {
  await stop();
  try {
    await api('/api/logout', {method: 'POST', headers: csrfHeaders()});
    csrf = null;
    location.reload();
  } catch (error) { setState('LOCK INCOMPLETE', 'The host has not confirmed revocation. Try Lock again.'); }
}
async function fullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else if ($('viewer').requestFullscreen) await $('viewer').requestFullscreen();
    else message('Use the player fullscreen button or rotate your phone.');
  } catch (_) { message('Use the player fullscreen button or rotate your phone.'); }
}
$('registerButton').onclick = register;
$('authButton').onclick = authenticate;
$('startButton').onclick = () => start();
$('stopButton').onclick = stop;
$('logoutButton').onclick = logout;
$('fullscreenButton').onclick = fullscreen;
$('reconnectButton').onclick = async () => { if (await stop()) await start(); };
window.addEventListener('pagehide', pause);
document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); else status().catch(() => {}); });
window.addEventListener('offline', () => { epoch++; clearFrame(); setState('OFFLINE', 'Waiting for the network…'); });
window.addEventListener('online', () => { if (wantsView) scheduleReconnect(); else status().catch(() => {}); });
status().catch(() => { $('message').textContent = 'Cannot reach the host. Check Tailscale and try again.'; });
setInterval(() => { status().catch(() => {}); heartbeat(); }, 3000);
