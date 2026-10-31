"""Native interactive charts; no iframes, remote libraries, or telemetry."""

BODY = r"""
<div id="soc-dashboard" data-api="__API__">
<div class="page-heading"><div><div class="eyebrow">SOC ANALYTICS / CONNECTED EXPLORATION</div>
<h1>Your SOC.<br><span>In focus.</span></h1><p>One dataset. Linked charts. Evidence you can investigate.</p></div>
<div class="dashboard-actions"><label class="button quiet file-button">Open dashboard JSON
<input id="dashboard-import" type="file" accept=".json,application/json" aria-label="Open dashboard JSON"></label>
<button id="export-selection" class="button primary" type="button">Export selection ↓</button></div></div>
<div class="dataset-strip"><span class="pill" id="source-mode">Loading snapshot</span>
<span id="connection-state" role="status" aria-live="polite"></span>
<div id="live-controls" hidden><label>Batch <select id="run-picker" aria-label="Batch"></select></label>
<label><input id="auto-refresh" type="checkbox" checked> Refresh every 30s</label>
<label><input id="follow-latest" type="checkbox" checked> Follow latest batch</label>
<button id="refresh-dashboard" class="button quiet" type="button">Refresh now</button></div></div>
<div id="dashboard-error" class="dashboard-error" role="alert" hidden></div>
<p id="provenance" class="muted compact"></p>
<section class="panel dashboard-filter-panel" aria-label="Dashboard filters">
<div class="filters dashboard-filters">
<label><span>From · UTC</span><input id="date-from" type="date" aria-label="From UTC"></label>
<label><span>To · UTC</span><input id="date-to" type="date" aria-label="To UTC"></label>
<label class="search-field"><span>Identity or alert ID</span><input id="dashboard-search" type="search" placeholder="Search evidence…" autocomplete="off"></label>
<label><span>ATT&CK hypothesis</span><select id="dashboard-technique"><option value="">All techniques</option></select></label>
<label class="score-filter"><span>Minimum ranking score <b id="score-label">0.00</b></span>
<input id="minimum-score" type="range" min="0" max="1" step="0.01" value="0" aria-label="Minimum ranking score"></label>
<button id="clear-dashboard" class="button quiet" type="button">Clear filters</button></div>
<div id="filter-summary" class="filter-summary" role="status" aria-live="polite"></div></section>
<section class="metrics dashboard-metrics" aria-label="Filtered dashboard metrics">
<div class="metric accent"><span>Alert windows</span><strong id="kpi-alerts">0</strong><small id="kpi-total">In the selected batch</small></div>
<div class="metric"><span>Identities</span><strong id="kpi-identities">0</strong><small>Distinct identities matching filters</small></div>
<div class="metric"><span>Mapped windows</span><strong id="kpi-mapped">0</strong><small>At least one curated ATT&CK hypothesis</small></div>
<div class="metric"><span>Peak daily queue</span><strong id="kpi-peak">0</strong><small>Filtered alert windows / UTC day</small></div></section>
<div class="dashboard-grid">
<section class="panel trend-panel"><div class="section-heading"><div><span class="eyebrow">TIME / DRILL DOWN</span>
<h2>Alert activity</h2></div><span class="chart-hint">Select a bar to focus its UTC dates</span></div>
<div id="activity-chart" class="native-chart"></div><div class="panel-foot"><span id="activity-bucket"></span><span>Queued windows, not raw sign-ins</span></div></section>
<section class="panel"><span class="eyebrow">ATT&CK / CANDIDATE SIGNALS</span><h2>Technique distribution</h2>
<p class="muted compact">Select a technique to filter every chart.</p><div id="technique-chart" class="bar-list"></div>
<p class="muted chart-note">One window may have several hypotheses. Counts overlap; they are not detection coverage.</p></section>
<section class="panel"><div class="section-heading"><div><span class="eyebrow">UTC / TEMPORAL PATTERNS</span><h2>When activity clusters</h2></div>
<span class="chart-hint">Select an hour and weekday</span></div><div id="heatmap" class="heatmap-scroll"></div>
<div class="panel-foot"><span>Mon → Sun · 00:00 → 23:00 UTC</span><span>All weeks in the current selection</span></div></section>
<section class="panel"><span class="eyebrow">IDENTITY / INVESTIGATE</span><h2>Top identities</h2>
<p class="muted compact">Top eight by matching alert windows. Select to investigate.</p><div id="identity-chart" class="bar-list"></div></section>
<section class="panel score-panel"><span class="eyebrow">MODEL / RANKING</span><h2>Score distribution</h2>
<div id="score-chart" class="bar-list"></div><p class="muted chart-note">Ranking scores are not probabilities or incident severity. Select a bin to filter the queue.</p></section>
<section class="panel context-panel"><span class="eyebrow">SOURCE / EVALUATION CONTEXT</span><h2>Know the scope</h2>
<dl id="run-context" class="context-list"></dl><p id="benchmark-context" class="muted compact"></p>
<p class="muted chart-note">Only queued windows are available here. This dashboard cannot measure all activity, missed attacks or real-world effectiveness.</p></section></div>
<section id="export-panel" class="panel dashboard-export" hidden><div class="section-heading"><div><span class="eyebrow">PORTABLE SELECTION</span><h2>Selection export</h2></div>
<button id="close-export" class="button quiet" type="button">Close export</button></div><p id="export-status" class="muted compact" role="status"></p>
<textarea id="export-json" readonly aria-label="Selection JSON" spellcheck="false"></textarea></section>
<section class="panel dashboard-queue"><div class="section-heading"><div><span class="eyebrow">LINKED EVIDENCE</span><h2>Investigation queue</h2></div>
<label class="dashboard-order">Order <select id="dashboard-sort" aria-label="Queue order"><option value="score">Highest score</option><option value="time">Most recent</option></select></label></div>
<div id="dashboard-alerts"></div><div class="pagination"><span id="dashboard-queue-status" role="status" aria-live="polite"></span>
<div><button id="dashboard-previous" class="button quiet" type="button">Previous</button><button id="dashboard-next" class="button quiet" type="button">Next</button></div></div></section>
<noscript><p class="notice">JavaScript is required for linked dashboard charts. The overview report retains static evidence.</p></noscript></div>
"""

STYLE = r"""
.dashboard-export{margin-bottom:20px}.dashboard-export textarea{margin-top:15px;width:100%;height:180px;resize:vertical;padding:14px;border:1px solid #344257;border-radius:6px;background:#0e1520;color:#c5dda8;font:11px/1.7 ui-monospace,monospace}.sidebar nav a[hidden]{display:none}
.dashboard-actions{display:flex;flex-wrap:wrap;gap:10px;justify-content:flex-end;max-width:310px}.file-button{position:relative;overflow:hidden;cursor:pointer}.file-button input{position:absolute;inset:0;width:100%;opacity:0;cursor:pointer}.file-button:focus-within{outline:2px solid var(--lime);outline-offset:4px}.dataset-strip{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin:12px 0 14px;color:var(--muted);font-size:11px}.dataset-strip select,.dashboard-order select{background:#101721;border:1px solid #344257;color:var(--text);border-radius:5px;padding:7px;font-size:11px;max-width:210px}.dataset-strip #live-controls{display:flex;flex-wrap:wrap;align-items:center;gap:12px}.dataset-strip #live-controls[hidden]{display:none}.dataset-strip label{display:flex;align-items:center;gap:6px}.dataset-strip .button{font-size:10px;padding:7px 10px}.dashboard-error{border:1px solid #a95351;color:#ffcfca;background:#3a2026;padding:13px;border-radius:7px;font-size:12px}.dashboard-filter-panel{margin:19px 0}.dashboard-filters{margin:0;flex-wrap:wrap}.dashboard-filters .search-field{min-width:150px}.dashboard-filters label{min-width:120px}.dashboard-filters .score-filter{min-width:135px;flex:1}.dashboard-filters input[type=range]{padding:0;accent-color:var(--lime);border:0}.score-filter b{float:right;color:var(--lime);font-variant-numeric:tabular-nums}.filter-summary{font-size:11px;color:#bed5b3;padding-top:15px;line-height:1.6;overflow-wrap:anywhere}.dashboard-metrics{margin-bottom:20px}.dashboard-grid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(0,1fr);gap:18px;margin-bottom:20px}.dashboard-grid>.panel{min-width:0;overflow:hidden}.chart-hint{font-size:10px;color:var(--muted);max-width:160px;text-align:right;line-height:1.6}.native-chart svg{width:100%;display:block;height:auto;max-height:275px;margin-top:16px}.native-chart svg text{font:11px system-ui,sans-serif;fill:#a9b8cd}.native-chart svg .chart-bar{cursor:pointer;fill:#b8ef65}.native-chart svg .chart-bar:hover,.native-chart svg [role=button]:focus .chart-bar{fill:#ddffa3}.native-chart svg [role=button]:focus{outline:2px solid #e3f7c7;outline-offset:3px}.bar-list{display:grid;gap:12px;margin-top:23px}.bar-item{position:relative;text-align:left;background:#101923;border:1px solid #2b3b4c;color:var(--text);padding:11px 12px 14px;border-radius:6px;min-width:0;width:100%;overflow:hidden}.bar-item>span{display:flex;justify-content:space-between;gap:15px;font-size:11px;position:relative;z-index:1}.bar-item small{font-size:9px;color:var(--muted);display:block;margin-top:5px;overflow-wrap:anywhere}.bar-item b{font-variant-numeric:tabular-nums;color:var(--lime)}.bar-item i{position:absolute;bottom:0;left:0;height:3px;background:#9ccb5a;min-width:2px}.bar-item:hover{background:#1e3025;border-color:#719952}.chart-note{font-size:10px;margin-top:20px;line-height:1.7}.heatmap-scroll{overflow:auto;margin:24px 0 17px}.heatmap-grid{display:grid;grid-template-columns:28px repeat(24,minmax(12px,1fr));gap:3px;min-width:380px}.heatmap-grid>span{font-size:8px;color:var(--muted);align-self:center}.heat-cell{border:1px solid #304139;background:#17251f;min-height:18px;border-radius:3px;padding:0;cursor:pointer}.heat-cell:hover{outline:1px solid #e4ffbe;outline-offset:1px}.heat-cell:disabled{opacity:.45;cursor:default}.context-list{display:grid;grid-template-columns:100px minmax(0,1fr);font-size:11px;gap:14px;margin:22px 0}.context-list dt{color:var(--muted)}.context-list dd{margin:0;overflow-wrap:anywhere}.context-list code{font-size:10px;color:#c3dcaa}.dashboard-queue details{border-bottom:1px solid var(--edge);padding:15px 0}.dashboard-queue summary{list-style:none;display:grid;grid-template-columns:minmax(0,1fr) 85px 82px;gap:10px;align-items:center}.dashboard-queue summary strong{display:block;overflow-wrap:anywhere;font-size:12px}.dashboard-queue summary small{display:block;font-size:10px;color:var(--muted);margin-top:7px}.dashboard-queue summary b{color:var(--lime);font-size:12px;text-align:right}.dashboard-queue summary>span:last-child{font-size:10px;color:#b7c8de;text-align:right}.dashboard-queue .queue-evidence{background:#101722;border-radius:7px;padding:15px;margin-top:15px;font-size:11px;overflow-wrap:anywhere;line-height:1.8}.dashboard-queue .queue-evidence ul{padding-left:18px;color:#bdcddd}.dashboard-queue .tag{margin-top:9px}.dashboard-order{color:var(--muted);font-size:10px}.dashboard-metrics .metric strong{font-variant-numeric:tabular-nums}.dashboard-order select{margin-left:8px}.dashboard-grid .section-heading{gap:10px;align-items:start}.dashboard-grid h2{margin-bottom:7px}
@media(max-width:1000px){.dashboard-grid{grid-template-columns:minmax(0,1.2fr) minmax(0,1fr)}.dashboard-actions{max-width:245px}.dashboard-actions .button{font-size:10px}.dashboard-filters .search-field{min-width:140px}.dataset-strip #live-controls{gap:10px}.chart-hint{max-width:110px;font-size:9px}}
@media(max-width:800px){.sidebar{flex-wrap:wrap}.sidebar nav{flex-wrap:wrap}.dashboard-grid{grid-template-columns:1fr}.dashboard-grid .chart-hint{max-width:150px}.dashboard-actions{justify-content:start;max-width:none;margin-top:14px}.dashboard-filters label{min-width:130px;flex:1}.dashboard-filters .search-field{flex-basis:100%}.dataset-strip select{max-width:180px}.dataset-strip #live-controls{align-items:start}.dataset-strip #live-controls>label:first-child{flex-basis:100%}.dataset-strip .pill{white-space:normal}.dashboard-grid .panel-foot{font-size:9px;gap:10px}.context-list{grid-template-columns:85px minmax(0,1fr)}}
@media(max-width:420px){.sidebar .brand{font-size:18px}.sidebar nav a{font-size:9px;padding:6px}.dashboard-queue summary{grid-template-columns:minmax(0,1fr) 45px 45px;gap:6px}.dashboard-queue summary>span:last-child{font-size:9px}.dashboard-filter-panel .filters label{min-width:110px}.dashboard-actions .button{margin-top:0}.dashboard-grid h2{font-size:17px}.context-list{font-size:10px}}
"""

SCRIPT = r"""
(() => {
  'use strict';
  const root = document.getElementById('soc-dashboard');
  if (!root) return;
  const $ = id => document.getElementById(id);
  const text = (tag, value, cls) => { const e = document.createElement(tag); e.textContent = String(value); if(cls)e.className=cls; return e; };
  const svg = (tag, attributes, value) => {const e=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attributes||{}).forEach(([k,v])=>e.setAttribute(k,String(v)));if(value!==undefined)e.textContent=String(value);return e;};
  const group = (rows, key) => {const m=new Map();rows.forEach(row=>{const k=key(row);m.set(k,(m.get(k)||0)+1);});return m;};
  const sorted = map => [...map].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
  let dataset, selected=[], page=0, hour=null, weekday=null, scoreBin=null, exactIdentity=null, selectedKey='', runs=[], request=0, imported=false;
  const api=root.dataset.api==='true', size=8, dayMs=86400000;
  const controls=['date-from','date-to','dashboard-search','dashboard-technique','minimum-score'];
  function validate(value) {
    if (!value || value.schema!=='aegislake.dashboard.v1' || !value.run || typeof value.run.run_id!=='string' || value.run.run_id.length>512 || !Array.isArray(value.alerts) || value.alerts.length>20000) throw Error('Unsupported dashboard JSON. Open an AegisLake dashboard.json export.');
    if(!value.techniques || typeof value.techniques!=='object' || Array.isArray(value.techniques) || Object.keys(value.techniques).length>128)throw Error('Invalid technique catalog.');
    Object.entries(value.techniques).forEach(([id,t])=>{if(id.length>128||!t||typeof t.name!=='string'||t.name.length>512||!Array.isArray(t.candidate_tactics)||t.candidate_tactics.length>32||t.candidate_tactics.some(c=>!c||typeof c.tactic_id!=='string'||c.tactic_id.length>128||typeof c.tactic_name!=='string'||c.tactic_name.length>512))throw Error('Invalid candidate tactics.');});
    if(value.run.benchmark&&['precision','recall'].some(k=>value.run.benchmark[k]!==null&&(typeof value.run.benchmark[k]!=='number'||value.run.benchmark[k]<0||value.run.benchmark[k]>1)))throw Error('Invalid evaluation metrics.');
    const seen=new Set();
    value.alerts.forEach(a=>{
      if(!a || typeof a.alert_id!=='string' || !a.alert_id.trim() || a.alert_id.length>512 || seen.has(a.alert_id) || typeof a.user!=='string' || !a.user.trim() || a.user.length>512 || typeof a.score!=='number' || !Number.isFinite(a.score) || a.score<0 || a.score>1 || typeof a.window_start!=='string' || !/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(a.window_start) || !Number.isFinite(Date.parse(a.window_start)) || !Array.isArray(a.attack_hypotheses) || a.attack_hypotheses.length>64 || a.attack_hypotheses.some(t=>typeof t!=='string'||t.length>128) || !Array.isArray(a.reasons) || a.reasons.length>100 || a.reasons.some(r=>typeof r!=='string'||r.length>4096)) throw Error('Invalid or duplicate alert record. Current dashboard has been preserved.');
      seen.add(a.alert_id);a.window_start=new Date(a.window_start).toISOString();
    });
    if(!['synthetic','labeled','unlabeled','unavailable'].includes(value.run.data_kind))throw Error('Dashboard data provenance is missing.');
    if(value.run.data_kind==='unlabeled'&&value.run.benchmark)throw Error('Unlabeled scoring batches cannot claim precision or recall.');
    if(value.run.bounds){Object.values(value.run.bounds).forEach(value=>{if(typeof value!=='string'||value.length>64||!Number.isFinite(Date.parse(value))||new Date(value).getUTCFullYear()<2000||new Date(value).getUTCFullYear()>2200)throw Error('Invalid dashboard time bounds.');});}
    return value;
  }
  function fail(message) {$('dashboard-error').textContent=message;$('dashboard-error').hidden=false;}
  function reset() {controls.forEach(id=>$(id).value=id==='minimum-score'?'0':'');hour=null;weekday=null;scoreBin=null;exactIdentity=null;page=0;}
  function activate(value, preserve=false) {
    dataset=validate(value);
    const old=$('dashboard-technique').value;
    $('dashboard-technique').replaceChildren(new Option('All techniques',''));
    const techniques=new Set(dataset.alerts.flatMap(a=>a.attack_hypotheses));
    [...techniques].sort().forEach(id=>$('dashboard-technique').append(new Option(id+' · '+(dataset.techniques?.[id]?.name||'Unregistered hypothesis'),id)));
    $('dashboard-technique').append(new Option('Without a curated mapping','unmapped'));
    if(!preserve) reset(); else if([...$('dashboard-technique').options].some(o=>o.value===old))$('dashboard-technique').value=old;
    $('dashboard-error').hidden=true;
    const label={synthetic:'Synthetic demonstration',labeled:'Labeled offline evaluation',unlabeled:'Unlabeled scoring batch',unavailable:'No batch available'}[dataset.run.data_kind];
    $('source-mode').textContent=label;
    document.querySelectorAll('.sidebar nav a').forEach(a=>{const base=a.getAttribute('href').split('?')[0];if(base==='report.html'||base==='mitre.html')a.hidden=imported;});
    $('export-panel').hidden=true;
    if(api)document.querySelector('.side-foot').textContent='Local batch API · Read only';
    document.querySelector('.topbar .pill').textContent=label;
    document.querySelector('footer code').textContent=dataset.run.run_id;
    $('provenance').textContent=dataset.run.data_notice||'Collection scope is unverified. Review the data source before drawing conclusions.';
    $('run-context').replaceChildren();
    const context=[['Batch',dataset.run.run_id],['Source',imported?'Browser-local JSON':api?'Local read-only API':'Embedded snapshot'],['Model',dataset.run.model||'Unavailable'],['Daily cap',dataset.run.capacity==null?'Unavailable':dataset.run.capacity+' windows'],['Input events',dataset.run.quality?.input_lines??'Unavailable']];
    context.forEach(([name,value])=>{$('run-context').append(text('dt',name),text('dd',value));});
    const b=dataset.run.benchmark;
    $('benchmark-context').textContent=b&&typeof b.precision==='number'&&typeof b.recall==='number'
      ? 'Full-batch held-out evaluation: precision '+(b.precision*100).toFixed(1)+'%, recall '+(b.recall*100).toFixed(1)+'%. These metrics do not change with dashboard filters.'
      : 'Precision and recall unavailable for this batch. Unlabeled operational alerts do not establish detection effectiveness.';
    render();
  }
  function render() {
    page=Math.max(0,page);
    const from=$('date-from').value,to=$('date-to').value,q=$('dashboard-search').value.trim().toLowerCase(),tech=$('dashboard-technique').value,min=Number($('minimum-score').value);
    $('score-label').textContent=min.toFixed(2);
    const invalid=from&&to&&from>to;
    if(dataset.run.data_kind==='unavailable'){
      selected=[];['kpi-alerts','kpi-identities','kpi-mapped','kpi-peak'].forEach(id=>$(id).textContent='—');$('kpi-total').textContent='No completed batch loaded';$('filter-summary').textContent='Load a dashboard JSON or generate a completed batch.';
      ['activity-chart','technique-chart','identity-chart','heatmap','score-chart','dashboard-alerts'].forEach(id=>empty($(id),'No batch loaded.'));
      $('dashboard-queue-status').textContent='No batch loaded';$('dashboard-previous').disabled=true;$('dashboard-next').disabled=true;$('export-selection').disabled=true;return;
    }
    $('export-selection').disabled=false;
    selected=dataset.alerts.filter(a=>{
      const d=a.window_start.slice(0,10),stamp=new Date(a.window_start),known=a.attack_hypotheses.some(t=>Object.hasOwn(dataset.techniques||{},t));
      return !invalid&&(!from||d>=from)&&(!to||d<=to)&&(exactIdentity?a.user===exactIdentity:(!q||a.user.toLowerCase().includes(q)||a.alert_id.toLowerCase().includes(q)))&&(!tech||(tech==='unmapped'?!known:a.attack_hypotheses.includes(tech)))&&a.score>=min&&(hour===null||stamp.getUTCHours()===hour)&&(weekday===null||(stamp.getUTCDay()+6)%7===weekday)&&(scoreBin===null||Math.min(4,Math.floor(a.score*5))===scoreBin);
    });
    const days=group(selected,a=>a.window_start.slice(0,10));
    $('kpi-alerts').textContent=selected.length.toLocaleString();$('kpi-total').textContent='of '+dataset.alerts.length.toLocaleString()+' queued windows';
    $('kpi-identities').textContent=new Set(selected.map(a=>a.user)).size.toLocaleString();
    $('kpi-mapped').textContent=selected.filter(a=>a.attack_hypotheses.some(t=>Object.hasOwn(dataset.techniques||{},t))).length.toLocaleString();
    $('kpi-peak').textContent=Math.max(0,...days.values());
    const parts=[];if(from||to)parts.push((from||'Start')+' → '+(to||'End'));if(q)parts.push('Search: '+q);if(tech)parts.push(tech);if(min)parts.push('Score ≥ '+min.toFixed(2));if(hour!==null)parts.push(['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][weekday]+' '+String(hour).padStart(2,'0')+':00 UTC');if(scoreBin!==null)parts.push('Score bin '+(scoreBin/5).toFixed(1)+'–'+((scoreBin+1)/5).toFixed(1));
    $('filter-summary').textContent=invalid?'From date must be on or before the To date.':parts.length?'Active filters · '+parts.join(' · '):'All queued windows · Select any chart to filter the entire dashboard.';
    activity(days);techniqueChart();identities();heatmap();scores();queue();
  }
  function empty(target,message='No matching alert windows.') {target.replaceChildren(text('p',message,'chart-empty'));}
  function bar(target,label,count,max,callback,note) {
    const button=text('button','', 'bar-item');button.type='button';button.setAttribute('aria-label',label+': '+count+' alert windows');
    const line=document.createElement('span');line.append(text('span',label),text('b',count));button.append(line);if(note)button.append(text('small',note));
    const indicator=document.createElement('i');indicator.style.width=(max?count/max*100:0)+'%';button.append(indicator);button.addEventListener('click',callback);target.append(button);
  }
  function activity(days) {
    const target=$('activity-chart');target.replaceChildren();
    if(!days.size){empty(target);$('activity-bucket').textContent='UTC dates';return;}
    const stamps=[...days.keys()].sort(),bounds=dataset.run.bounds||{},start=$('date-from').value||String(bounds.test_first_window||'').slice(0,10),end=$('date-to').value||String(bounds.test_last_window_end||'').slice(0,10);
    const first=Number.isFinite(Date.parse(start))?Math.min(Date.parse(start),Date.parse(stamps[0])):Date.parse(stamps[0]),last=Number.isFinite(Date.parse(end))?Math.max(Date.parse(end),Date.parse(stamps.at(-1))):Date.parse(stamps.at(-1)),step=Math.max(1,Math.ceil(((last-first)/dayMs+1)/40)),bins=[];
    for(let start=first;start<=last;start+=step*dayMs){const end=Math.min(last,start+(step-1)*dayMs);let count=0;for(let day=start;day<=end;day+=dayMs)count+=days.get(new Date(day).toISOString().slice(0,10))||0;bins.push({from:new Date(start).toISOString().slice(0,10),to:new Date(end).toISOString().slice(0,10),count});}
    const max=Math.max(1,...bins.map(b=>b.count)),chart=svg('svg',{viewBox:'0 0 760 230',role:'group','aria-label':'Interactive alert activity chart'}),slot=690/bins.length;
    [0,.5,1].forEach(n=>{chart.append(svg('path',{d:'M45 '+(180-140*n)+'H735',stroke:'#2a3544'}),svg('text',{x:8,y:184-140*n},Math.round(max*n)));});
    bins.forEach((b,i)=>{const x=45+i*slot+slot*.18,h=b.count/max*140,g=svg('g',{role:'button',tabindex:'0','aria-label':b.from+(b.from!==b.to?' to '+b.to:'')+': '+b.count+' alert windows'});g.append(svg('title',{},b.from+' → '+b.to+': '+b.count),svg('rect',{x,y:180-Math.max(2,h),width:slot*.64,height:Math.max(2,h),rx:3,class:'chart-bar'}));const select=()=>{$('date-from').value=b.from;$('date-to').value=b.to;page=0;render();};g.addEventListener('click',select);g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});chart.append(g);if(bins.length<=9||i%Math.ceil(bins.length/7)===0)chart.append(svg('text',{x:x+slot*.32,y:207,'text-anchor':'middle'},b.from.slice(5)));});
    target.append(chart);$('activity-bucket').textContent=step===1?'Daily buckets · UTC':step+'-day buckets · UTC';
  }
  function techniqueChart() {
    const target=$('technique-chart');target.replaceChildren();const counts=new Map();
    selected.forEach(a=>{const values=[...new Set(a.attack_hypotheses)];if(!values.some(t=>Object.hasOwn(dataset.techniques||{},t)))values.push('unmapped');values.forEach(t=>counts.set(t,(counts.get(t)||0)+1));});
    if(!counts.size)return empty(target);
    const maximum=Math.max(...counts.values());sorted(counts).forEach(([id,count])=>bar(target,id==='unmapped'?'Unmapped':id,count,maximum,()=>{$('dashboard-technique').value=id;page=0;render();},dataset.techniques?.[id]?.name||'No registered curated technique'));
  }
  function identities() {const target=$('identity-chart');target.replaceChildren();const counts=sorted(group(selected,a=>a.user));if(!counts.length)return empty(target);counts.slice(0,8).forEach(([id,count])=>bar(target,id,count,counts[0][1],()=>{exactIdentity=id;$('dashboard-search').value=id;page=0;render();}));}
  function heatmap() {
    const target=$('heatmap');target.replaceChildren();if(!selected.length)return empty(target);
    const counts=Array.from({length:7},()=>Array(24).fill(0));selected.forEach(a=>{const d=new Date(a.window_start);counts[(d.getUTCDay()+6)%7][d.getUTCHours()]++;});const max=Math.max(1,...counts.flat()),grid=text('div','','heatmap-grid');grid.append(text('span','UTC'));
    for(let h=0;h<24;h++)grid.append(text('span',h%3===0?String(h).padStart(2,'0'):''));
    counts.forEach((hours,d)=>{grid.append(text('span',['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][d]));hours.forEach((count,h)=>{const button=text('button','','heat-cell');button.type='button';button.disabled=!count;const label=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][d]+' '+String(h).padStart(2,'0')+':00 UTC: '+count+' alert windows';button.setAttribute('aria-label',label);button.title=label;button.style.backgroundColor='rgba(184,239,101,'+(count ? .15+.8*count/max : .04)+')';button.addEventListener('click',()=>{hour=h;weekday=d;page=0;render();});grid.append(button);});});target.append(grid);
  }
  function scores() {const target=$('score-chart');target.replaceChildren();if(!selected.length)return empty(target);const counts=Array(5).fill(0);selected.forEach(a=>counts[Math.min(4,Math.floor(a.score*5))]++);const max=Math.max(1,...counts);counts.forEach((count,i)=>bar(target,(i/5).toFixed(1)+' ≤ score '+(i===4?'≤':'<')+' '+((i+1)/5).toFixed(1),count,max,()=>{scoreBin=i;page=0;render();}));}
  function queue() {
    const target=$('dashboard-alerts');target.replaceChildren();const ordered=[...selected].sort($('dashboard-sort').value==='time'?(a,b)=>b.window_start.localeCompare(a.window_start)||b.score-a.score:(a,b)=>b.score-a.score||a.alert_id.localeCompare(b.alert_id));
    page=Math.min(page,Math.max(0,Math.ceil(ordered.length/size)-1));
    if(!ordered.length)empty(target);
    ordered.slice(page*size,(page+1)*size).forEach(a=>{const details=document.createElement('details'),summary=document.createElement('summary'),identity=document.createElement('span');identity.append(text('strong',a.user),text('small',a.window_start.slice(0,16).replace('T',' / ')+' UTC'));summary.append(identity,text('b',a.score.toFixed(3)),text('span','Inspect ↗'));details.append(summary);const body=text('div','','queue-evidence');body.append(text('p','Alert '+a.alert_id));const list=document.createElement('ul');a.reasons.forEach(reason=>list.append(text('li',reason)));if(!a.reasons.length)list.append(text('li','No textual evidence supplied; inspect source telemetry.'));body.append(list);const tactics=new Map();a.attack_hypotheses.forEach(id=>{body.append(text('span',id,'tag'));(dataset.techniques?.[id]?.candidate_tactics||[]).forEach(t=>tactics.set(t.tactic_id,t.tactic_name));});body.append(text('p','Candidate tactics: '+([...tactics].map(([id,name])=>id+' / '+name).join(' · ')||'Unmapped')));body.append(text('p','Hypothesis for human review. Tactical membership does not confirm an objective or incident.'));details.append(body);target.append(details);});
    $('dashboard-queue-status').textContent=ordered.length?(page*size+1)+'–'+Math.min((page+1)*size,ordered.length)+' of '+ordered.length+' matching alert windows':'0 matching alert windows';$('dashboard-previous').disabled=page===0;$('dashboard-next').disabled=(page+1)*size>=ordered.length;
  }
  controls.forEach(id=>$(id).addEventListener(id==='dashboard-technique'?'change':'input',()=>{if(id==='dashboard-search')exactIdentity=null;page=0;render();}));
  $('clear-dashboard').addEventListener('click',()=>{reset();render();});$('dashboard-sort').addEventListener('change',queue);
  $('dashboard-previous').addEventListener('click',()=>{page--;queue();});$('dashboard-next').addEventListener('click',()=>{page++;queue();});
  $('dashboard-import').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>20*1024*1024)throw Error('Dashboard JSON exceeds 20 MiB.');const value=validate(JSON.parse(await file.text()));request++;imported=true;activate(value);$('connection-state').textContent='Browser-local file · API refresh paused';}catch(error){fail(error.message);}finally{e.target.value='';}});
  $('export-selection').addEventListener('click',()=>{const value={...dataset,run:{...dataset.run,benchmark:null},alerts:selected,selection:{from:$('date-from').value,to:$('date-to').value,search:$('dashboard-search').value,exact_identity:exactIdentity,technique:$('dashboard-technique').value,minimum_score:Number($('minimum-score').value),hour_utc:hour,weekday_monday_first:weekday,score_bin:scoreBin}},encoded=JSON.stringify(value,null,2);$('export-json').value=encoded;$('export-panel').hidden=false;$('export-status').textContent=selected.length+' alert windows ready. Save the download or copy this JSON.';const url=URL.createObjectURL(new Blob([encoded],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='aegislake-dashboard-selection.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  $('close-export').addEventListener('click',()=>{$('export-panel').hidden=true;});
  async function refresh(explicit=false) {
    if(!api)return;const token=++request;
    try{const response=await fetch('/api/runs',{cache:'no-store'});if(!response.ok)throw Error('Local API unavailable ('+response.status+').');const body=await response.json();if(token!==request)return;runs=body.runs;if(!Array.isArray(runs)||runs.some(r=>!r||!/^([a-f0-9]{20})$/.test(r.key)||!r.run||typeof r.run.run_id!=='string'))throw Error('Invalid batch catalog.');
      $('run-picker').replaceChildren(...runs.map(r=>new Option(r.run.run_id+' · '+r.run.data_kind+' · '+r.alerts+' alerts',r.key)));
      if(!runs.length){$('connection-state').textContent='API connected · No completed dashboard batches yet';return;}
      const query=new URLSearchParams(location.search).get('run');if(!selectedKey&&runs.some(r=>r.key===query)){selectedKey=query;$('follow-latest').checked=false;}
      const nextKey=$('follow-latest').checked||!runs.some(r=>r.key===selectedKey)?runs[0].key:selectedKey;
      const result=await fetch('/api/runs/'+encodeURIComponent(nextKey)+'/dashboard',{cache:'no-store'});if(!result.ok)throw Error('Selected batch unavailable ('+result.status+').');const value=validate(await result.json());if(token!==request)return;
      const same=selectedKey===nextKey&&dataset.run.run_id===value.run.run_id&&!imported;selectedKey=nextKey;imported=false;$('run-picker').value=selectedKey;activate(value,same);$('connection-state').textContent='API connected · Read '+new Date().toISOString().slice(11,19)+' UTC · Batch updates';history.replaceState(null,'','?run='+selectedKey);
      document.querySelectorAll('.sidebar a').forEach(a=>{const base=a.getAttribute('href').split('?')[0];if(base==='report.html'||base==='mitre.html')a.href=base+'?run='+selectedKey;});
    }catch(error){if(token===request){fail(error.message+' Last successfully loaded data remain visible.');$('connection-state').textContent='API unavailable · Showing last loaded snapshot';}}
  }
  $('live-controls').hidden=!api;$('refresh-dashboard').addEventListener('click',()=>refresh(true));$('run-picker').addEventListener('change',()=>{selectedKey=$('run-picker').value;$('follow-latest').checked=false;refresh(true);});
  try{activate(JSON.parse($('dashboard-data').textContent));$('connection-state').textContent=api?'Connecting to local API…':'Embedded snapshot · Import dashboard.json to explore another batch';}catch(error){fail(error.message);}
  if(api){refresh();setInterval(()=>{if($('auto-refresh').checked&&!imported)refresh();},30000);}
})();
"""
