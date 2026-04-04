const CHUNK=60;
const base=(location.protocol==='http:'||location.protocol==='https:')?location.origin:'http://192.168.4.1';
const $=id=>document.getElementById(id);

function san(t){
return t.replace(/\u2014|\u2013/g,'-').replace(/[\u201c\u201d]/g,'"').replace(/[\u2018\u2019]/g,"'")
.replace(/\u2026/g,'...').replace(/\r/g,'').split('').filter(c=>c.charCodeAt(0)<128).join('');
}

function buildScript(raw){
const iw=+$('initWait').value||0,tw=+$('tabWait').value||0,rw=+$('rowWait').value||0,xw=+$('typeWait').value||0;
const s=[];
if(iw>0)s.push(`WAIT ${iw}`);
for(const row of raw.split('\n')){
if(!row.trim()){s.push('ENTER');if(rw>0)s.push(`WAIT ${rw}`);continue;}
const cells=row.split('\t');
for(let i=0;i<cells.length;i++){
let c=cells[i].replace(/\n/g,' ').trim();
if(c){s.push(`TYPE ${c}`);if(xw>0)s.push(`WAIT ${xw}`);}
if(i<cells.length-1){s.push('TAB');if(tw>0)s.push(`WAIT ${tw}`);}
}
s.push('ENTER');if(rw>0)s.push(`WAIT ${rw}`);
}
return s;
}

function chunkMs(chunk){
let ms=0,sp=+$('charSpeed').value||15;
for(const ln of chunk){
if(ln.startsWith('WAIT')){
const p=ln.split(' ');
if(p[1]&&!isNaN(+p[1]))ms+=+p[1];
}else if(ln.startsWith('TYPE'))ms+=(ln.length-5)*sp;
}
return ms+2500;
}

function logLine(m){
const el=$('log'),t=new Date().toLocaleTimeString();
el.textContent+=`[${t}] ${m}\n`;
el.scrollTop=el.scrollHeight;
}

async function postChunk(lines,signal){
const r=await fetch(`${base}/execute`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:lines.join('\n')}),signal});
const j=await r.json().catch(()=>({}));
if(!r.ok)throw new Error(j.message||r.statusText||String(r.status));
return j.message||'done';
}

async function pokeStop(){
try{await fetch(`${base}/stop`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});}catch(e){logLine('stop ping: '+e.message);}
}

let feeding=false,haltRun=false,abortCtl=null;

function setPreview(){
const raw=$('payloadData').value.trim();
const pv=$('preview');
if(!raw){pv.textContent='';return;}
const rows=raw.split('\n').length;
const sc=buildScript(san(raw));
const n=Math.ceil(sc.length/CHUNK)||0;
let total=0;
for(let i=0;i<sc.length;i+=CHUNK)total+=chunkMs(sc.slice(i,i+CHUNK));
pv.textContent=`${rows} row(s) → ${sc.length} script line(s) → ${n} chunk(s) → ~${(total/1000/60).toFixed(1)} min est.`;
}

['initWait','tabWait','rowWait','typeWait','charSpeed','payloadData'].forEach(id=>{
const el=$(id);
el.addEventListener(id==='payloadData'?'input':'change',setPreview);
});

function uiRun(on){
feeding=on;
$('go').disabled=on;
$('stop').disabled=!on;
$('progBox').hidden=!on;
if(!on){$('prog').style.width='0%';}
}

async function run(){
const raw=$('payloadData').value.trim();
if(!raw){$('stat').className='stat err';$('stat').textContent='Paste data first.';return;}
haltRun=false;
const st=$('stat'),prog=$('prog');
st.className='stat run';
st.textContent='Starting…';
$('log').textContent='';
logLine('begin');

const text=san(raw),full=buildScript(text);
const chunks=[];
for(let i=0;i<full.length;i+=CHUNK)chunks.push(full.slice(i,i+CHUNK));
const total=chunks.length;
let i=0;
uiRun(true);

for(;i<total;i++){
if(!feeding)break;
abortCtl=new AbortController();
const ch=chunks[i],wait=chunkMs(ch);
st.textContent=`Chunk ${i+1}/${total} — sending, then ~${(wait/1000).toFixed(1)}s pause for device`;
logLine(`POST chunk ${i+1}/${total} (${ch.length} lines, ~${wait}ms budget)`);
try{
const msg=await postChunk(ch,abortCtl.signal);
logLine(`chunk ${i+1} device: ${msg}`);
}catch(e){
if(e.name==='AbortError'){logLine('fetch aborted');break;}
logLine('error: '+e.message);
st.className='stat err';
st.textContent='Network error — check you are on the Pico AP.';
uiRun(false);
return;
}
prog.style.width=`${((i+1)/total)*100}%`;
if(!feeding)break;
st.textContent=`Chunk ${i+1}/${total} — waiting ${(wait/1000).toFixed(1)}s before next`;
await new Promise(r=>{
let d=0;const f=()=>{if(d)return;d=1;clearTimeout(to);clearInterval(iv);r();};
const to=setTimeout(f,wait),iv=setInterval(()=>{(haltRun||!feeding)&&f()},40);
});
if(haltRun||!feeding)break;
}

uiRun(false);
if(haltRun){
st.className='stat stop';
st.textContent='Stopped — no further chunks will be sent. Device may finish current line.';
logLine('halted');
}else if(i>=total){
st.className='stat ok';
st.textContent='All chunks sent — host may still be catching up on the last lines.';
logLine('done');
}
}

function stop(){
if(!feeding)return;
haltRun=true;
feeding=false;
abortCtl?.abort();
pokeStop();
logLine('stop requested (client + server)');
}

$('go').onclick=run;
$('stop').onclick=stop;
setPreview();
