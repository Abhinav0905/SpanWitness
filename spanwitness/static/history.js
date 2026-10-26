const historyState = {asset:'',records:[],comparisons:[],examples:[],pendingRecords:[],pendingComparisons:[],busy:false,request:0};
const historyDate = value => value ? new Date(value).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'}) : 'Capture date unknown';
const historyAngle = value => value == null ? 'Unmeasured' : `${value.toFixed(1)}°`;

function setHistoryBusy(value){
  historyState.busy=value;
  document.querySelectorAll('#history button,#history select,#history input').forEach(element=>element.disabled=value);
  if(!value){$('historyAdd').disabled=!historyState.asset;updateHistoryPair(false);}
}

async function loadAssets(preferred){
  try{
    const response=await api('/api/assets');
    const assets=response.assets;
    for(const record of historyState.pendingRecords){
      if(!assets.some(asset=>asset.asset_id===record.asset_id))assets.unshift({asset_id:record.asset_id,observation_count:0,location_label:record.location_label});
    }
    const selected=preferred||historyState.asset||assets[0]?.asset_id||'';
    $('historyAsset').innerHTML=assets.length?assets.map(asset=>`<option value="${esc(asset.asset_id)}">${esc(asset.asset_id)}</option>`).join(''):'<option value="">No saved assets yet</option>';
    $('historyAsset').value=assets.some(asset=>asset.asset_id===selected)?selected:assets[0]?.asset_id||'';
    historyState.asset=$('historyAsset').value;
    $('historyAdd').disabled=!historyState.asset;
    $('historyWorkspace').hidden=!historyState.asset;
    if(historyState.asset)await loadAssetHistory(historyState.asset);
  }catch(error){toast(`History could not be loaded: ${error.message}`);}
}

async function loadAssetHistory(asset){
  const request=++historyState.request;
  const response=await api(`/api/assets/history?asset_id=${encodeURIComponent(asset)}`);
  if(request!==historyState.request||asset!==historyState.asset)return;
  const merge=(remote,pending)=>[...new Map([...pending,...remote].map(record=>[record.id,record])).values()];
  historyState.pendingRecords=historyState.pendingRecords.filter(record=>!response.records.some(saved=>saved.id===record.id));
  historyState.pendingComparisons=historyState.pendingComparisons.filter(record=>!response.comparisons.some(saved=>saved.id===record.id));
  historyState.records=merge(response.records,historyState.pendingRecords.filter(record=>record.asset_id===asset));
  historyState.records.sort((a,b)=>(b.observed_at||b.created_at).localeCompare(a.observed_at||a.created_at));
  historyState.comparisons=merge(response.comparisons,historyState.pendingComparisons.filter(record=>record.asset_id===asset));
  historyState.comparisons.sort((a,b)=>b.created_at.localeCompare(a.created_at));
  const records=historyState.records;
  $('historyAssetContext').textContent=records.find(record=>record.location_label)?.location_label||'No location context supplied';
  $('historyScope').textContent='Newest 100 observations and 100 comparisons. Asset identity, capture dates and location are operator-supplied.';
  $('historyCount').textContent=records.length;
  $('historyTimeline').innerHTML=records.length?records.map(record=>{
    const angle=record.report.pole_alignment?.relative_angle_deg;
    return `<article class="timeline-observation"><span class="timeline-dot"></span><div><strong>${esc(historyDate(record.observed_at))}</strong><p>${record.observed_at?'Supplied observation date':`Saved ${esc(historyDate(record.created_at))}`}</p><span class="priority-pill ${esc(record.plan.priority)}">${esc(record.plan.label)}</span><p>${record.report.pole_alignment?`Reference-relative angle: ${esc(historyAngle(angle))}`:'Conductor / vegetation inspection'}</p><small>${record.source_kind==='synthetic'?'Controlled synthetic observation':record.source_kind==='public_image'?'Licensed field photograph':'Operator observation'} · <a href="/api/observations/${record.id}/export">Evidence JSON ↗</a></small></div></article>`;
  }).join(''):'<p class="muted">This asset has no observations in the current history window.</p>';
  const eligible=records.filter(record=>record.observed_at&&record.report.pole_alignment);
  const options=eligible.map(record=>`<option value="${record.id}">${esc(historyDate(record.observed_at))} · ${esc(historyAngle(record.report.pole_alignment.relative_angle_deg))}</option>`).join('');
  $('baselineSelect').innerHTML=options||'<option value="">No dated pole observation</option>';
  $('currentSelect').innerHTML=options||'<option value="">No dated pole observation</option>';
  if(eligible.length){
    const saved=historyState.comparisons.find(record=>eligible.some(item=>item.id===record.baseline_id)&&eligible.some(item=>item.id===record.current_id));
    $('baselineSelect').value=saved?.baseline_id||eligible.at(-1).id;
    $('currentSelect').value=saved?.current_id||eligible[0].id;
  }
  updateHistoryPair(true);
}

function updateHistoryPair(resetConfirmation=true){
  const baseline=historyState.records.find(record=>record.id===$('baselineSelect').value);
  const current=historyState.records.find(record=>record.id===$('currentSelect').value);
  for(const [prefix,record] of [['baseline',baseline],['current',current]]){
    const image=$(prefix+'Image');
    if(record){image.src=record.overlay_url;image.hidden=false;$(prefix+'Meta').textContent=`${historyDate(record.observed_at)} · ${historyAngle(record.report.pole_alignment?.relative_angle_deg)} relative to marked reference`;}
    else{image.hidden=true;image.removeAttribute('src');$(prefix+'Meta').textContent='Analyze a photo with marked pole and reference axes, and supply its observation date.';}
  }
  if(resetConfirmation)$('repeatableCapture').checked=false;
  const eligible=baseline&&current&&baseline.id!==current.id&&baseline.observed_at<current.observed_at;
  $('historyEligibility').textContent=eligible?'3° is a declared image-change review threshold. It is not a utility standard or a physical lean measurement.':'Choose two dated pole observations, with the current observation later than the baseline.';
  $('compareHistory').disabled=historyState.busy||!eligible||!$('repeatableCapture').checked;
  const saved=historyState.comparisons.find(record=>record.baseline_id===baseline?.id&&record.current_id===current?.id);
  $('historyResult').hidden=!saved;
  if(saved)renderHistoryResult(saved);
}

function renderHistoryResult(record){
  const comparison=record.comparison;
  const titles={change_detected:'Apparent alignment change',no_material_change:'No change above the review threshold',not_comparable:'Another observation is needed'};
  const element=$('historyResult');
  element.hidden=false;element.className=`history-result ${esc(comparison.status)}`;
  element.innerHTML=`<div class="history-result-heading"><div><span class="eyebrow">SAVED COMPARISON · ${esc(historyDate(record.created_at))}</span><h2>${esc(titles[comparison.status]||comparison.status)}</h2></div><span class="priority-pill ${esc(record.plan.priority)}">${esc(record.plan.label)}</span></div>
    <p>${esc(comparison.reason)}</p>
    ${comparison.change_deg!=null?`<div class="history-change-values"><div><span>BASELINE</span><strong>${historyAngle(comparison.baseline_angle_deg)}</strong></div><div><span>CURRENT</span><strong>${historyAngle(comparison.current_angle_deg)}</strong></div><div><span>APPARENT CHANGE</span><strong>${comparison.change_deg>0?'+':''}${historyAngle(comparison.change_deg)}</strong></div></div>`:''}
    <div class="history-next"><span class="eyebrow">NEXT STEP</span><strong>${esc(record.plan.action)}</strong><p>${esc(record.plan.reason)}</p></div>
    <p class="history-limit">${esc(comparison.meaning)}</p>
    <details class="history-method"><summary>Why this comparison was accepted or declined</summary><p>${esc(comparison.capture_setup==='fixture_declared_repeatable_view'?'Controlled case: the capture setup is supplied by the fixture. Refusal controls deliberately break it.':comparison.capture_setup==='operator_confirmed_repeatable_view'?'Repeatable setup confirmed by the operator.':'Capture setup not confirmed.')}</p><dl><div><dt>Background inliers</dt><dd>${comparison.inliers} / ${comparison.matches} matches</dd></div>${comparison.estimated_camera_rotation_deg!=null?`<div><dt>Estimated image rotation</dt><dd>${historyAngle(comparison.estimated_camera_rotation_deg)}</dd></div>`:''}${comparison.median_registration_error_px!=null?`<div><dt>Median registration error</dt><dd>${comparison.median_registration_error_px} px</dd></div>`:''}${comparison.reason_code?`<div><dt>Comparison gate</dt><dd>${esc(comparison.reason_code.replaceAll('_',' '))}</dd></div>`:''}</dl><p>Background matching excludes the marked pole. A fit to the background cannot prove a shared 3D camera pose. The result remains conditional on the declared capture setup.</p></details>
    <div class="history-result-actions"><button id="historyReview" class="button dark">Stage a change review</button><a class="button secondary" href="${esc(record.export_url)}">Download comparison ↓</a></div>`;
  $('historyReview').onclick=()=>{
    renderRecord(record.current);state.reviewComparison=record;
    $('ticketSummary').textContent=`${record.asset_id} · ${record.plan.label} · Historical comparison`;
    $('reviewNote').value=`${record.plan.action}. ${comparison.reason}`;
    $('confirmPriority').checked=false;$('ticketDialog').showModal();
  };
}

async function compareSelectedHistory(){
  if(historyState.busy)return;
  const payload={baseline_id:$('baselineSelect').value,current_id:$('currentSelect').value,repeatable_capture:$('repeatableCapture').checked};
  setHistoryBusy(true);
  try{
    const record=await api('/api/history/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    historyState.pendingComparisons.unshift(record);historyState.comparisons.unshift(record);renderHistoryResult(record);
  }catch(error){toast(error.message);}finally{setHistoryBusy(false);}
}

async function runHistoryExample(caseId){
  if(historyState.busy)return;
  const example=historyState.examples.find(item=>item.id===caseId);
  if(!example)return;
  setHistoryBusy(true);$('historyDemoStatus').textContent='Saving and analyzing the baseline observation…';
  try{
    const records=[];
    for(const view of ['baseline','current']){
      $('historyDemoStatus').textContent=`Analyzing the ${view} synthetic observation…`;
      const sample=example.views[view];const response=await fetch(sample.image_url);if(!response.ok)throw new Error('The controlled image could not be loaded.');
      const form=new FormData();form.append('image',await response.blob(),'controlled-history.jpg');
      form.append('asset_id',example.asset_id);form.append('source_kind','synthetic');form.append('span','null');
      form.append('pole',JSON.stringify(sample.geometry.pole));form.append('vertical_reference',JSON.stringify(sample.geometry.vertical_reference));
      form.append('observed_at',sample.observed_at);form.append('location_label','Controlled model scene · illustrative inspection dates');
      records.push(await api('/api/analyze',{method:'POST',body:form}));
    }
    $('historyDemoStatus').textContent='Checking the scene correspondence and measured alignment change…';
    const comparison=await api('/api/history/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({baseline_id:records[0].id,current_id:records[1].id,repeatable_capture:true,capture_setup_source:'controlled_fixture'})});
    historyState.pendingRecords.unshift(...records);historyState.pendingComparisons.unshift(comparison);
    await loadAssets(example.asset_id);renderHistoryResult(comparison);refreshCounts();
    $('historyDemoStatus').textContent='Two synthetic observations and their comparison were saved. The dates are illustrative; no field inspection or physical movement is claimed.';
  }catch(error){$('historyDemoStatus').textContent=`The controlled comparison did not finish: ${error.message}`;toast(error.message);}finally{setHistoryBusy(false);}
}

$('historyRefresh').onclick=()=>loadAssets();
$('historyAsset').onchange=async()=>{historyState.asset=$('historyAsset').value;try{await loadAssetHistory(historyState.asset);}catch(error){toast(error.message);}};
$('baselineSelect').onchange=()=>updateHistoryPair();$('currentSelect').onchange=()=>updateHistoryPair();
$('repeatableCapture').onchange=()=>updateHistoryPair(false);$('compareHistory').onclick=compareSelectedHistory;
$('historyAdd').onclick=()=>{
  const asset=historyState.asset,context=historyState.records.find(record=>record.location_label)?.location_label||'';
  resetResult();state.points=[];state.pole=null;state.verticalReference=null;state.rawUrl=null;state.example=null;
  $('assetId').value=asset;$('locationLabel').value=context;$('observedAt').value='';$('observationDetails').open=true;
  $('sceneImage').removeAttribute('src');$('spanCanvas').getContext('2d').clearRect(0,0,$('spanCanvas').width,$('spanCanvas').height);
  $('imageMeta').textContent='Add a new image';$('sourceBadge').textContent='New observation';$('analyzeButton').disabled=true;
  tab('inspect');$('uploadButton').click();
};

async function initHistory(){
  try{
    historyState.examples=await api('/api/history/examples');
    $('historyExamples').innerHTML=historyState.examples.map((example,index)=>`<button class="history-example" data-history-example="${esc(example.id)}"><span class="eyebrow">CONTROL ${String(index+1).padStart(2,'0')}</span><strong>${esc(example.name)}</strong><span>${esc(example.description)}</span><small>Run comparison ↗</small></button>`).join('');
    document.querySelectorAll('[data-history-example]').forEach(button=>button.onclick=()=>runHistoryExample(button.dataset.historyExample));
  }catch(error){$('historyDemoStatus').textContent=`Controlled cases are unavailable: ${error.message}`;}
}
initHistory();
