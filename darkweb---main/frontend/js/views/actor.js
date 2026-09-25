import { records,icon,destinationForNode,destinationForEdge,edgeId } from '../models/workspace.js';
import { h,text,stamp,listText,countLabel,percent,percentMarkup,PENDING,statusMessage } from '../utils/display.js';
const $ = selector => document.querySelector(selector);

export class ActorView {
  constructor({scene,navigate}) {
    this.scene=scene;this.navigate=navigate;this.actor=null;this.resetFilters();
    $('#screen-actor').addEventListener('click',event=>{
      const topic=event.target.closest('[data-open-detail]')?.dataset.openDetail;
      const destination=event.target.closest('[data-destination]')?.dataset.destination;
      if (topic) navigate('detail/'+topic);
      if (destination) navigate(destination);
      if (event.target.closest('[data-latest]')) {this.step=null;this.updateGraph();}
    });
    $('#node-select').addEventListener('change',event=>{
      const value=event.target.value;
      if (value.startsWith('node:')) navigate(destinationForNode(this.actor,value.slice(5)));
      if (value.startsWith('edge:')) {const edge=this.actor?.graph?.edges.find(e=>e.id===value.slice(5));if(edge)navigate(destinationForEdge(this.actor,edge));}
    });
    document.querySelectorAll('[data-node-type]').forEach(input=>input.addEventListener('change',()=>{
      if(input.checked)this.types.add(input.dataset.nodeType);else this.types.delete(input.dataset.nodeType);
      this.updateGraph();
    }));
    $('#threshold').addEventListener('input',event=>{this.threshold=Number(event.target.value);this.updateGraph();});
    $('#zoom-out').addEventListener('click',()=>scene.zoomBy(-.1));
    $('#zoom-in').addEventListener('click',()=>scene.zoomBy(.1));
    $('#reset-view').addEventListener('click',()=>scene.reset());
    $('#orbit-toggle').addEventListener('click',()=>scene.setOrbit(!scene.orbit));
    $('#flatten-view').addEventListener('click',()=>scene.setFlat(!scene.flat));
  }
  resetFilters() {
    this.step=null;this.threshold=0;this.types=new Set(['alias','key','wallet','source']);
    $('#threshold').value='0';
    document.querySelectorAll('[data-node-type]').forEach(input=>input.checked=true);
  }
  render(resource) {
    this.resource=resource;this.actor=resource.data;
    const a=this.actor;
    // BACKEND CONNECT: The entire view receives one mapped resource from app.js.
    $('#actor-title').textContent=text(a?.handle);$('#actor-id').textContent=text(a?.id);
    $('#actor-summary').textContent=text(a?.description);
    $('#linked-names').innerHTML=Array.isArray(a?.aliases)?a.aliases.length?a.aliases.map(alias=>`<button data-destination="${h(alias.nodeId?destinationForNode(a,alias.nodeId):'detail/profile')}">${h(alias.handle)}</button>`).join(''):'<span>No aliases returned</span>':PENDING;
    $('#overview-facts').innerHTML=[['FIRST SEEN',stamp(a?.firstSeen,true)],['LAST SEEN',stamp(a?.lastSeen,true)],['SOURCES',countLabel(a?.sources,'records')]].map(([label,value])=>`<div><dt>${label}</dt><dd>${h(value)}</dd></div>`).join('');
    $('#actor-status').textContent=statusMessage(resource);$('#actor-status').hidden=resource.status==='ready';
    const info={
      profile:{value:countLabel(a?.aliases,'linked usernames'),sub:listText(a?.aliases,'handle'),foot:'NAMES & ACCOUNT RECORD'},
      key:{value:countLabel(a?.keys,'signing keys'),sub:listText(a?.keys,'value'),foot:'REVIEW KEY RECORDS'},
      wallet:{value:countLabel(a?.wallets,'wallet references'),sub:listText(a?.wallets,'value'),foot:'TRACE THE REFERENCES'},
      evidence:{value:percent(a?.confidence),sub:countLabel(a?.evidence,'supporting records'),foot:'READ EVIDENCE & LIMITATIONS'},
      sources:{value:countLabel(a?.sources,'sources'),sub:listText(a?.sources,'name'),foot:'CHECK SOURCE RECORDS'},
      timeline:{value:countLabel(a?.events,'observations'),sub:a?.firstSeen&&a?.lastSeen?`${stamp(a.firstSeen,true)} — ${stamp(a.lastSeen,true)}`:PENDING,foot:'FOLLOW THE ACTIVITY'},
    };
    $('#detail-cards').innerHTML=records.map(r=>{const c=info[r.id];return `<button class="record-card" data-open-detail="${r.id}" aria-label="Open ${r.title.toLowerCase()}"><div class="card-head"><span class="card-index">${r.number}</span><span class="card-icon">${icon(r.icon)}</span></div><div class="card-main"><h3>${r.title}</h3><div class="card-value">${r.id==='evidence'?percentMarkup(a?.confidence):h(c.value)}</div><p class="card-subtext">${h(c.sub)}</p></div><div class="card-footer"><span>${c.foot}</span><span aria-hidden="true">↗</span></div></button>`;}).join('');
    this.scene.setActor(a);this.updateGraph();
  }
  updateGraph() {
    const actor=this.actor;
    this.scene.setFilters({step:this.step,threshold:this.threshold,types:this.types});
    const graph=this.scene.getGraph(),select=$('#node-select');
    $('#threshold-value').textContent=this.threshold+'%';
    select.disabled=!graph.nodes.length;
    if (!actor?.graph) {
      const message=this.resource?.status==='loading'?'Loading graph…':PENDING;
      select.innerHTML=`<option value="">${message}</option>`;
      $('#graph-pending').textContent=message;$('#graph-pending').hidden=false;$('#graph-status').textContent=message;
    } else {
      $('#graph-pending').hidden=graph.nodes.length>0;
      $('#graph-pending').textContent=actor.graph.nodes.length?'No connections match these filters':'No graph records returned';
      const name=id=>text(actor.graph.nodes.find(n=>n.id===id)?.name);
      select.innerHTML='<option value="">Choose a connection…</option><optgroup label="Accounts and identifiers">'+graph.nodes.map(n=>`<option value="node:${h(n.id)}">${h(n.name)}</option>`).join('')+'</optgroup><optgroup label="Branches">'+graph.edges.map(edge=>`<option value="edge:${h(edgeId(edge))}">${h(name(edge.from))} → ${h(name(edge.to))}</option>`).join('')+'</optgroup>';
      $('#graph-status').innerHTML=`${graph.nodes.filter(n=>n.type!=='actor').length} connected items · ${graph.edges.length} branches${this.step!==null?` · ${stamp(actor.events?.[this.step]?.date,true)} <button class="text-button" data-latest>Show latest</button>`:''}`;
    }
    for (const id of ['filters-button','zoom-out','zoom-in','reset-view']) $('#'+id).disabled=!actor?.graph;
  }
}
