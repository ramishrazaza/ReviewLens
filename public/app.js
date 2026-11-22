const $ = (id) => document.getElementById(id);
const state = {dashboard: null, page: 1, pageSize: 8, busy: false, reply: ''};
const TOPIC_LABELS = {quality:'Quality',delivery:'Delivery',price:'Price',packaging:'Packaging',support:'Support',size_fit:'Size & fit',other:'Other'};
const PRODUCT_ICONS = ['◈','◉','◇','⬡','◎','✦','▣'];
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const fmt = n => Number(n || 0).toLocaleString('en-IN');

function notify(message, isError=false) {
  const toast=$('toast'); toast.textContent=message;toast.classList.toggle('error', isError);toast.hidden=false;
  toast.scrollIntoView({behavior:'smooth',block:'nearest'});
}
function busy(value){state.busy=value; $('progressBar').hidden=!value;$('uploadInput').disabled=value;$('sampleButton').disabled=value;}
async function api(path, options={}){
  const response=await fetch(path,options);let payload;
  try{payload=await response.json();}catch{throw new Error('Unexpected response from the server.');}
  if(!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
  return payload;
}
async function uploadFile(file){
  if(state.busy)return;
  if(!file || !file.name.toLowerCase().endsWith('.csv'))return notify('Please choose a .csv review file.',true);
  if(file.size > 3*1024*1024)return notify('CSV must be smaller than 3 MB.',true);
  busy(true);$('toast').hidden=true;
  try{
    const outcome=await api('/api/upload',{method:'POST',headers:{'Content-Type':'text/csv','X-Filename':encodeURIComponent(file.name)},body:file});
    state.dashboard=outcome.dashboard;state.page=1;render();
    const s=outcome.stats;notify(`Analysis complete: ${s.analysed} unique reviews, ${s.duplicates} duplicate(s), ${s.skipped_empty} empty, ${s.failed} failed. ${s.cache_hits} served from cache.`);
  }catch(error){notify(error.message,true);}finally{busy(false);$('uploadInput').value='';}
}
async function loadSample(){try{const response=await fetch('/sample-reviews.csv');if(!response.ok)throw Error('Sample dataset unavailable');const blob=await response.blob();await uploadFile(new File([blob],'reviews.csv',{type:'text/csv'}));}catch(err){notify(err.message,true);}}
function render(){
  const d=state.dashboard;
  if(!d)return;
  const o=d.overview,p=o.percent,s=d.stats;
  $('datasetLabel').textContent=`${d.filename || 'Uploaded dataset'} · ${fmt(s.total)} imported · ${fmt(s.duplicates)} duplicates flagged · ${fmt(s.skipped_empty)} empty skipped`;
  $('statTotal').textContent=fmt(o.total);$('statPositive').textContent=`${p.positive}%`;
  $('statNegative').textContent=`${p.negative}%`;$('statReply').textContent=fmt(o.needs_reply);
  $('positiveCount').textContent=`${o.sentiment.positive} positive reviews`;$('negativeCount').textContent=`${o.sentiment.negative} negative reviews`;
  const pos=p.positive,neu=p.neutral;
  $('sentimentDonut').style.background=`conic-gradient(#42bf99 0% ${pos}%,#f2b85d ${pos}% ${pos+neu}%,#ea8293 ${pos+neu}% 100%)`;
  $('donutValue').textContent=fmt(o.total);$('legendPositive').textContent=`${pos}%`; $('legendNeutral').textContent=`${neu}%`;$('legendNegative').textContent=`${p.negative}%`;
  $('agreementNote').textContent=o.ratings_compared ? `✧ Rating agreement: ${o.rating_agreement}% across ${o.ratings_compared} reviews with known star ratings. Disagreements are flagged in the table.`:'No known ratings available to compare against sentiment.';
  renderInsights('complaints',d.complaints);renderInsights('praises',d.praises);renderProducts(d.products);
  $('productFilter').innerHTML='<option value="">All products</option>'+d.products.map(p=>`<option value="${esc(p.name)}">${esc(p.name)}</option>`).join('');
  $('reviewCountLabel').textContent=d.rows.length;$('exportBtn').disabled=false;renderTable();
}
function renderInsights(element,items){$(''+element).innerHTML=items.length ? items.map((x,i)=>`<div class="insight-item"><div><strong>${i+1}. ${esc(TOPIC_LABELS[x.topic]||x.topic)}</strong><b>${x.count} mention${x.count!==1?'s':''}</b></div><p>${esc(x.example)}</p></div>`).join(''):'<p class="empty-small">No insights for this sentiment yet.</p>';}
function renderProducts(items){
  $('productList').innerHTML=items.length ? items.map((p,index)=>{
    const percent=100/Math.max(p.count,1);
    return `<div class="product-row"><div class="product-info"><div class="product-icon">${PRODUCT_ICONS[index%PRODUCT_ICONS.length]}</div><span><strong>${esc(p.name)}</strong><small>${fmt(p.count)} analyzed reviews · ${esc(p.issues.map(x=>TOPIC_LABELS[x.topic]).join(', ') || 'No major issues')}</small></span></div><div class="product-track" title="Positive ${p.positive} · Neutral ${p.neutral} · Negative ${p.negative}"><span class="pos" style="width:${p.positive*percent}%"></span><span class="neu" style="width:${p.neutral*percent}%"></span><span class="neg" style="width:${p.negative*percent}%"></span></div><div class="product-score">${Math.round(p.positive*percent)}%<small>positive</small></div></div>`;
  }).join(''):'<div class="empty-center">No product performance data yet.</div>';
}
function filteredRows(){
  if(!state.dashboard)return [];
  const search=$('searchFilter').value.toLowerCase().trim(), product=$('productFilter').value, sentiment=$('sentimentFilter').value, topic=$('topicFilter').value,status=$('statusFilter').value;
  return state.dashboard.rows.filter(r=>(!search || [r.review_id,r.product,r.text,r.analysis?.summary].join(' ').toLowerCase().includes(search)) && (!product||r.product===product)&&(!sentiment||r.analysis?.sentiment===sentiment)&&(!topic||r.analysis?.topics.includes(topic))&&(!status||r.status===status));
}
function renderTable(){
  const rows=filteredRows(), totalPages=Math.max(1,Math.ceil(rows.length/state.pageSize));state.page=Math.min(state.page,totalPages);
  const visible=rows.slice((state.page-1)*state.pageSize,state.page*state.pageSize);
  $('reviewRows').innerHTML=visible.length?visible.map(r=>{
    const a=r.analysis, rating=r.rating;
    const stars=rating===null?'<span class="unknown-star">Unrated</span>':`<span class="stars">${'★'.repeat(rating)}<span>${'☆'.repeat(5-rating)}</span></span>`;
    const sentiment=r.status==='analysed'&&a?`<span class="sentiment-badge ${a.sentiment}">● ${esc(a.sentiment)}</span>`:`<span class="status-badge">${r.status==='analysis_failed'?'Analysis failed':esc(r.status)}</span>`;
    const topics=a?r.analysis.topics.map(t=>`<span class="topic-chip">${esc(TOPIC_LABELS[t])}</span>`).join(''):'—';
    const action=r.status==='analysed'&&a?.needs_reply?`<button class="reply-button" data-reply="${r.row_num}">↗ Generate reply</button>`:r.status==='analysis_failed'?`<span class="no-action" title="${esc(r.error)}">Failed</span>`:'<span class="no-action">—</span>';
    return `<tr><td><div class="review-first"><strong>${esc(r.review_id)}</strong>${r.rating_mismatch&&r.status==='analysed'?'<span class="mismatch-flag" title="Rating and sentiment disagree">⚑ Mismatch</span>':''}<p title="${esc(r.text)}">${esc(a?.summary || r.text || r.error || 'No review text')}${r.duplicate_of?' · Duplicate of '+esc(r.duplicate_of):''}</p></div></td><td><div class="review-product">${esc(r.product)}</div></td><td>${stars}</td><td>${sentiment}</td><td>${topics}</td><td>${action}</td></tr>`;
  }).join(''):'<tr><td class="table-empty" colspan="6">No reviews match these filters.</td></tr>';
  $('tableCount').textContent=rows.length?`Showing ${(state.page-1)*state.pageSize+1}–${Math.min(state.page*state.pageSize,rows.length)} of ${rows.length} reviews`:'No matching reviews';
  $('pageIndicator').textContent=`${state.page} / ${totalPages}`;$('prevPage').disabled=state.page<=1;$('nextPage').disabled=state.page>=totalPages;
}
async function showReply(rowNum){
  const row=state.dashboard?.rows.find(r=>r.row_num===rowNum);if(!row)return;
  state.reply='';$('copyReply').disabled=true;$('modalReview').textContent=`${row.review_id} · ${row.product}\n“${row.text}”`;$('modalReply').textContent='✦ Generating a thoughtful, helpful response…';$('replyModal').showModal();
  try{const result=await api('/api/reply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row_num:rowNum})});state.reply=result.reply;$('modalReply').textContent=result.reply;$('copyReply').disabled=false;}catch(err){$('modalReply').textContent='Unable to create a reply: '+err.message;}
}
function exportCsv(){const d=state.dashboard;if(!d)return;const cols=['review_id','product','rating','date','review_text','status','sentiment','topics','summary','needs_reply','rating_mismatch'];const values=d.rows.map(r=>[r.review_id,r.product,r.rating??'',r.date,r.text,r.status,r.analysis?.sentiment||'',r.analysis?.topics.join('|')||'',r.analysis?.summary||'',r.analysis?.needs_reply??'',r.rating_mismatch??'']);const body=[cols,...values].map(row=>row.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n');const url=URL.createObjectURL(new Blob(['\ufeff'+body],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='reviewlens-insights.csv';a.click();URL.revokeObjectURL(url);}
function bind(){
  $('uploadInput').addEventListener('change',e=>{if(e.target.files?.[0])uploadFile(e.target.files[0]);});$('sampleButton').addEventListener('click',loadSample);
  ['searchFilter','productFilter','sentimentFilter','topicFilter','statusFilter'].forEach(id=>$(id).addEventListener(id==='searchFilter'?'input':'change',()=>{state.page=1;renderTable();}));
  $('prevPage').addEventListener('click',()=>{state.page--;renderTable();});$('nextPage').addEventListener('click',()=>{state.page++;renderTable();});
  $('exportBtn').addEventListener('click',exportCsv);
  $('reviewRows').addEventListener('click',event=>{const button=event.target.closest('[data-reply]');if(button)showReply(Number(button.dataset.reply));});
  ['closeModal','doneModal'].forEach(id=>$(id).addEventListener('click',()=>$('replyModal').close()));
  $('copyReply').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(state.reply);$('copyReply').textContent='Copied ✓';setTimeout(()=>$('copyReply').textContent='Copy reply ↗',1400);}catch{notify('Copy failed. You can select the response text instead.',true);}});
  document.querySelectorAll('.side-nav a').forEach(link=>link.addEventListener('click',()=>{document.querySelectorAll('.side-nav a').forEach(a=>a.classList.remove('active'));link.classList.add('active');}));
}
async function init(){bind();try{const status=await api('/api/health');if(status.mode==='offline_preview'){$('modeBanner').textContent='OFFLINE PREVIEW MODE · This is a clearly labeled demonstration with illustrative, hand-written classifications. No AI requests are sent. Set REVIEWLENS_DEMO_MODE=0 and provide GEMINI_API_KEY to analyze with Gemini.';$('modeBanner').classList.add('preview');$('modeBanner').hidden=false;}else if(!status.configured){$('modeBanner').textContent='Setup needed: Add your Gemini API key to .env on the server, then restart to analyze new reviews. Your key is never sent to the browser.';$('modeBanner').hidden=false;}const data=await api('/api/dashboard');if(data.dashboard){state.dashboard=data.dashboard;render();}}catch(err){notify('Cannot connect to backend. Launch it with python run.py. '+err.message,true);}}
init();
