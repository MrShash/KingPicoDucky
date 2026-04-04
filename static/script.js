const CHUNK = 60;
const base = (location.protocol === 'http:' || location.protocol === 'https:') ? location.origin : 'http://192.168.4.1';
const $ = id => document.getElementById(id);

function san(t) {
  return t.replace(/\u2014|\u2013/g, '-').replace(/[\u201c\u201d]/g, '"').replace(/[\u2018\u2019]/g, "'")
    .replace(/\u2026/g, '...').replace(/\r/g, '').split('').filter(c => c.charCodeAt(0) < 128).join('');
}

function buildScript(raw) {
  const iw = +$('initWait').value || 0, tw = +$('tabWait').value || 0, rw = +$('rowWait').value || 0, xw = +$('typeWait').value || 0;
  const s = [];
  if (iw > 0) s.push(`WAIT ${iw}`);
  for (const row of raw.split('\n')) {
    if (!row.trim()) { s.push('ENTER'); if (rw > 0) s.push(`WAIT ${rw}`); continue; }
    const cells = row.split('\t');
    for (let i = 0; i < cells.length; i++) {
      let c = cells[i].replace(/\n/g, ' ').trim();
      if (c) { s.push(`TYPE ${c}`); if (xw > 0) s.push(`WAIT ${xw}`); }
      if (i < cells.length - 1) { s.push('TAB'); if (tw > 0) s.push(`WAIT ${tw}`); }
    }
    s.push('ENTER'); if (rw > 0) s.push(`WAIT ${rw}`);
  }
  return s;
}

async function waitChunkDone() {
  while (feeding && !haltRun) {
    try {
      const r = await fetch(`${base}/status`);
      if (r.ok) {
        const j = await r.json();
        if (!j.busy) return j.abort ? 'aborted' : 'done';
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, 500));
  }
  return haltRun ? 'halted' : 'done';
}

function logLine(m) {
  const el = $('log'), t = new Date().toLocaleTimeString();
  el.textContent += `>_ [${t}] ${m}\n`;
  el.scrollTop = el.scrollHeight;
}

function fmtMs(ms) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000), s = Math.floor((ms % 60000) / 1000);
  return `${m}m ${s}s`;
}

function updateEta(done, total, chunkMs) {
  const remaining = total - done;
  const etaMs = remaining * chunkMs;
  const pct = Math.round((done / total) * 100);
  $('prog').style.width = `${pct}%`;
  $('progLabel').textContent = `Chunk ${done} / ${total}  (${pct}%)`;
  $('etaLabel').textContent = etaMs > 0 ? `ETA  ~${fmtMs(etaMs)}` : 'Finishing…';
}

async function postChunk(lines, signal) {
  const hzF = +$('hzFreq').value / 100;
  const hzP = +$('hzPx').value;
  const r = await fetch(`${base}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: lines.join('\n'), humanize: $('humanize').checked, hz_freq: hzF, hz_px: hzP }),
    signal
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.message || r.statusText || String(r.status));
  return j.message || 'done';
}

async function pokeStop() {
  try { await fetch(`${base}/stop`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }); }
  catch (e) { logLine('stop ping failed: ' + e.message); }
}

let feeding = false, haltRun = false, abortCtl = null;

async function updateJiggler() {
  const on = $('jigToggle').checked;
  $('jigConfig').style.display = on ? 'flex' : 'none';
  try {
    await fetch(`${base}/jiggler`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: on, distance: +$('jigDist').value, interval: +$('jigInt').value, random: $('jigRand').checked })
    });
    logLine(on ? `jiggler ARMED — every ${$('jigInt').value}s, up to ${$('jigDist').value}px` : 'jiggler disarmed');
  } catch (e) { logLine('jiggler error: ' + e.message); }
}

['jigToggle', 'jigDist', 'jigInt', 'jigRand'].forEach(id => {
  $(id).addEventListener('change', updateJiggler);
});

function setPreview() {
  const raw = $('payloadData').value.trim();
  const pv = $('preview');
  if (!raw) { pv.textContent = ''; return; }
  const rows = raw.split('\n').length;
  const sc = buildScript(san(raw));
  const n = Math.ceil(sc.length / CHUNK) || 0;
  const tw = +$('tabWait').value || 0, rw = +$('rowWait').value || 0;
  const roughMs = rows * (rw + 100) + (sc.length * tw / CHUNK);
  pv.textContent = `${rows} rows  ·  ${sc.length} instructions  ·  ${n} chunk${n !== 1 ? 's' : ''}  ·  est. ~${fmtMs(roughMs)}`;
}

['initWait', 'tabWait', 'rowWait', 'typeWait', 'payloadData', 'humanize', 'hzFreq', 'hzPx'].forEach(id => {
  const el = $(id);
  el.addEventListener(id === 'payloadData' ? 'input' : 'change', setPreview);
});

$('speedSlider').addEventListener('input', () => {
  const val = parseInt($('speedSlider').value, 10);
  $('speedLbl').textContent = `${val}%`;
  const inv = 1 - (val / 100);
  $('tabWait').value = Math.round(50 + (inv * 750));
  $('rowWait').value = Math.round(50 + (inv * 1450));
  $('typeWait').value = Math.round(10 + (inv * 140));
  if (val === 100) $('humanize').checked = false;
  setPreview();
});

function uiRun(on) {
  feeding = on;
  $('go').disabled = on;
  $('stop').disabled = !on;
  $('humanize').disabled = on;
  $('hzFreq').disabled = on;
  $('hzPx').disabled = on;
  $('speedSlider').disabled = on;
  $('jigToggle').disabled = on;
  $('jigDist').disabled = on;
  $('jigInt').disabled = on;
  $('jigRand').disabled = on;
  $('progBox').hidden = !on;
  if (!on) {
    $('prog').style.width = '0%';
    $('progLabel').textContent = '—';
    $('etaLabel').textContent = 'ETA —';
  }
}

async function run() {
  const raw = $('payloadData').value.trim();
  if (!raw) { $('stat').className = 'stat err'; $('stat').textContent = '⚠ No payload — paste data first.'; return; }
  haltRun = false;
  const st = $('stat');
  st.className = 'stat run';
  st.textContent = 'Initialising…';
  $('log').textContent = '';

  const text = san(raw), full = buildScript(text);
  const chunks = [];
  for (let i = 0; i < full.length; i += CHUNK) chunks.push(full.slice(i, i + CHUNK));
  const total = chunks.length;
  let i = 0;

  logLine(`PAYLOAD LOADED — ${full.length} instructions across ${total} chunk${total !== 1 ? 's' : ''}`);
  if ($('humanize').checked) logLine(`mouse jiggler ACTIVE — ${$('hzFreq').value}% chance per key, ±${$('hzPx').value}px`);
  logLine(`start countdown: ${$('initWait').value}ms — click target field NOW`);
  logLine('─'.repeat(48));

  uiRun(true);
  const chunkTimes = [];

  for (; i < total; i++) {
    if (!feeding) break;
    abortCtl = new AbortController();
    const ch = chunks[i];
    const chunkStart = Date.now();

    st.textContent = `⟶ Sending chunk ${i + 1} of ${total}…`;
    logLine(`SEND  chunk ${String(i + 1).padStart(3)} / ${total}  [${ch.length} lines]`);

    try {
      const msg = await postChunk(ch, abortCtl.signal);
      logLine(`ACK   chunk ${String(i + 1).padStart(3)}  →  ${msg}`);
    } catch (e) {
      if (e.name === 'AbortError') { logLine('ABORT fetch cancelled'); break; }
      logLine(`ERR   ${e.message}`);
      st.className = 'stat err';
      st.textContent = '✖ Network error — are you connected to the Pico Wi-Fi?';
      uiRun(false);
      return;
    }

    st.textContent = `⏳ Executing chunk ${i + 1} of ${total} on device…`;
    if (!feeding) break;
    const doneMsg = await waitChunkDone();

    const elapsed = Date.now() - chunkStart;
    chunkTimes.push(elapsed);
    const avgChunkMs = chunkTimes.reduce((a, b) => a + b, 0) / chunkTimes.length;

    logLine(`DONE  chunk ${String(i + 1).padStart(3)}  [${fmtMs(elapsed)}]  status: ${doneMsg}`);
    updateEta(i + 1, total, avgChunkMs);

    if (haltRun || !feeding) break;
  }

  uiRun(false);
  logLine('─'.repeat(48));

  if (haltRun) {
    st.className = 'stat stop';
    st.textContent = '⏹ Aborted — device will finish its current line then stop.';
    logLine('SESSION ABORTED by user');
  } else if (i >= total) {
    st.className = 'stat ok';
    st.textContent = '✔ All chunks delivered — host may still be catching up.';
    logLine('SESSION COMPLETE ✓');
  }
}

function stop() {
  if (!feeding) return;
  haltRun = true;
  feeding = false;
  abortCtl?.abort();
  pokeStop();
  logLine('ABORT signal sent to device');
}

$('go').onclick = run;
$('stop').onclick = stop;
setPreview();
