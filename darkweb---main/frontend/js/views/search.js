import { api, pending } from '../services/traceveil-api.js';
import { h, text, percentMarkup, stamp, countLabel, listText, PENDING } from '../utils/display.js';
import { waitForSearchEffect } from '../components/search-transition.js';

const $ = selector => document.querySelector(selector);
export class SearchView {
  constructor({dialogs,getMotion,onSelect,onStatus}) {
    Object.assign(this,{dialogs,getMotion,onSelect,onStatus});
    this.result=pending();this.selectedId=null;this.controller=null;this.suggestionsController=null;
    $('#search-form').addEventListener('submit',event => {
      event.preventDefault(); const query=$('#query').value.trim();
      if (query) this.search(query,$('#search-type').value); else $('#query').focus();
    });
    $('#cancel-search').addEventListener('click',()=>this.cancel());
    $('#scan-dialog').addEventListener('cancel',event=>{event.preventDefault();this.cancel();});
    $('#sort').addEventListener('change',()=>this.renderResults());
    $('#result-select').addEventListener('change',event=>{this.selectedId=event.target.value;this.renderResults();});
    $('#search-results').addEventListener('click',event=>{
      const button=event.target.closest('button[data-result]');
      if (!button || button.disabled) return;
      const actor=this.result.data?.find(item=>item.id===button.dataset.result);
      if (actor) this.dialogs.close($('#search-dialog'),()=>this.onSelect(actor));
    });
    $('#try-select').addEventListener('change',event=>{
      const item=this.suggestions?.[Number(event.target.value)];
      if (!item || event.target.value==='') return;
      $('#query').value=item.value; $('#search-type').value=item.type; $('#query').focus();
    });
  }
  async loadSuggestions() {
    this.suggestionsController?.abort();
    const controller=new AbortController();this.suggestionsController=controller;
    const select=$('#try-select');select.disabled=true;
    select.innerHTML='<option value="">Loading options…</option>';
    try {
      // BACKEND CONNECT: Only api.suggestions supplies these options.
      const result=await api.suggestions(controller.signal);
      if (controller.signal.aborted) return;
      if(result.code===401){this.onStatus(result);return;}
      this.suggestions=result.data;
      const prompt=result.status==='ready'?'Choose an identifier':result.status==='empty'?'No identifiers available':result.status==='error'?'Unable to load identifiers':PENDING;
      select.innerHTML=`<option value="">${h(prompt)}</option>`+(result.data??[]).map((item,index)=>`<option value="${index}">${h(item.label)}</option>`).join('');
      select.disabled=result.status!=='ready';
      $('#try-status').textContent=result.message??prompt;
    } catch (error) { if (error.name!=='AbortError') throw error; }
  }
  setBusy(busy) {
    document.body.classList.toggle('is-scanning',busy);
    $('#search-form').classList.toggle('is-searching',busy);
    $('#search-form').setAttribute('aria-busy',String(busy));
    $('#search-submit').disabled=busy;$('#query').readOnly=busy;
  }
  cancel(focus=true) {
    this.controller?.abort();this.controller=null;
    this.setBusy(false);this.dialogs.close($('#scan-dialog'),null,true);
    if (focus) $('#query').focus({preventScroll:true});
  }
  clear() {
    this.cancel(false);this.suggestionsController?.abort();
    this.result=pending();this.suggestions=null;this.selectedId=null;
    $('#query').value='';$('#search-results').replaceChildren();
    $('#try-select').innerHTML=`<option value="">${PENDING}</option>`;$('#try-select').disabled=true;
  }
  async search(query,type) {
    this.cancel(false);
    const controller=new AbortController();this.controller=controller;
    this.query=query;this.setBusy(true);this.selectedId=null;
    $('#scan-query').textContent=query;
    $('#scan-dialog').dataset.phase='search';
    $('#scan-title').textContent='SEARCHING';$('#scan-title').dataset.echo='SEARCHING';
    $('#scan-step').textContent='WAITING FOR RESPONSE';
    $('#search-status').textContent='Waiting for the account search response…';
    this.dialogs.open($('#scan-dialog'));$('#cancel-search').focus();
    this.onStatus({status:'loading'});
    try {
      const [result]=await Promise.all([
        api.search(query,type,controller.signal),
        waitForSearchEffect(this.getMotion(),controller.signal),
      ]);
      if (controller.signal.aborted || this.controller!==controller) return;
      this.controller=null;this.setBusy(false);this.dialogs.close($('#scan-dialog'),null,true);
      this.result=result;if(this.onStatus(result)===false)return;this.renderResults();
      this.dialogs.open($('#search-dialog'));
      $('#search-results button[data-result]:not(:disabled)')?.focus({preventScroll:true});
    } catch (error) {
      if (!controller.signal.aborted) {this.cancel(false);this.onStatus({status:'error',message:error.message});}
    }
  }
  renderResults() {
    const data=[...(this.result.data??[])],status=this.result.status;
    const sort=$('#sort').value;
    data.sort((a,b)=>sort==='name'?text(a.handle).localeCompare(text(b.handle)):sort==='recent'?(Date.parse(b.lastSeen)||0)-(Date.parse(a.lastSeen)||0):(b.confidence??-1)-(a.confidence??-1));
    const actor=data.find(item=>item.id===this.selectedId)??data[0]??null;
    this.selectedId=actor?.id??null;
    $('#results-title').textContent=status==='pending'?PENDING:status==='error'?'SEARCH UNAVAILABLE':data.length?`${data.length} ${data.length===1?'ACCOUNT':'ACCOUNTS'} FOUND`:'NO ACCOUNTS FOUND';
    $('#search-message').textContent=status==='error'?this.result.message:status==='pending'?PENDING:`Matches for “${this.query}”`;
    $('#sort-field').hidden=data.length<2;$('#result-picker').hidden=data.length<2;
    $('#result-select').innerHTML=data.map((a,i)=>`<option value="${h(a.id)}">${i+1} / ${data.length} · ${h(a.handle)}</option>`).join('');
    if (actor) $('#result-select').value=actor.id;
    $('#search-dialog .modal-hint').hidden=!actor;
    if (status==='empty') {$('#search-results').innerHTML='<div class="empty-result">No matching account was returned. Try another identifier.</div>';return;}
    // BACKEND CONNECT: A missing field stays visibly pending, even in a real match.
    $('#search-results').innerHTML=`<article class="result-dossier" aria-label="Account dossier">
      <div class="result-card-top"><span>TRACEVEIL / ACCOUNT DOSSIER</span><span>${h(actor?.id)}</span></div>
      <div class="dossier-hero"><div class="identity-mark" aria-hidden="true">${actor?.initials?h(actor.initials):'⌕'}</div><div class="dossier-name"><span class="eyebrow">PRIMARY USERNAME</span><h3>${h(actor?.handle)}</h3><p>${h(actor?.description)}</p></div><div class="dossier-score ${actor?.confidence===null||actor?.confidence===undefined?'is-pending':''}"><b>${percentMarkup(actor?.confidence)}</b><span>LINK CONFIDENCE</span></div></div>
      <div class="dossier-aliases"><span>POSSIBLE ALIASES</span><strong>${h(listText(actor?.aliases,'handle'))}</strong></div>
      <dl class="dossier-facts">${[['FIRST SEEN',stamp(actor?.firstSeen)],['LAST SEEN',stamp(actor?.lastSeen)],['REVIEW STATUS',text(actor?.priority)],['EVIDENCE',countLabel(actor?.evidence,'records')]].map(([label,value])=>`<div><dt>${label}</dt><dd>${h(value)}</dd></div>`).join('')}</dl>
      <div class="dossier-identifiers"><div><span>SIGNING KEYS</span><code>${h(listText(actor?.keys,'value'))}</code></div><div><span>WALLET REFERENCES</span><code>${h(listText(actor?.wallets,'value'))}</code></div></div>
      <p class="dossier-sources"><span>SOURCE RECORDS</span>${h(listText(actor?.sources,'name'))}</p>
      <div class="result-card-foot"><span class="dossier-review">${actor?'Suggested links · Analyst review needed':PENDING}</span><button class="primary-button" data-result="${actor?h(actor.id):''}" ${actor?'':'disabled'}>${actor?'Open actor workspace →':PENDING}</button></div>
    </article>`;
  }
}
