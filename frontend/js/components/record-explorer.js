import {icon} from '../models/workspace.js';
import {buildRecordPages, initialPageIndex, ringGeometry, ringRadii, pageWindow} from '../models/record-pages.js';
import {filteredGraph} from '../models/graph.js';
import {h, text, percentMarkup, PENDING, facts as meta, safeLink} from '../utils/display.js';
const two = n => String(n).padStart(2,'0');

export function snapshotMarkup(actor, step) {
  if (!actor?.graph || !actor.events?.[step]?.date) return `<p class="resource-status">${PENDING}</p>`;
  const graph = filteredGraph(actor,{step});
  if (!graph.nodes.length) return '<p class="resource-status">No dated graph records at this moment.</p>';
  const positions = new Map(graph.nodes.map(n => [n.id,[240+n.position[0]*.8,142+n.position[1]*.65]]));
  const name = id => graph.nodes.find(n=>n.id===id)?.name ?? PENDING;
  const description = graph.edges.map(e=>`${name(e.from)}: ${text(e.kind)} ${name(e.to)}`).join('; ') || 'No connections returned.';
  return `<div class="snapshot-frame"><div class="snapshot-caption"><span>CONNECTIONS AT THIS MOMENT</span><span>${graph.edges.length} branches</span></div><svg class="moment-map" viewBox="0 0 480 285" role="img" aria-label="${h(description)}">${graph.edges.map(e=>{const a=positions.get(e.from),b=positions.get(e.to);return `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" class="snapshot-edge"/>`;}).join('')}${graph.nodes.map(n=>{const [x,y]=positions.get(n.id);return `<g class="snapshot-node"><circle cx="${x}" cy="${y}" r="${n.type==='actor'?10:6}"/><text x="${x}" y="${y+25}" text-anchor="middle">${h(n.name.length>18?n.name.slice(0,15)+'…':n.name)}</text></g>`;}).join('')}</svg></div>`;
}

export class RecordExplorer {
  constructor(root,{getMotion,onNavigate,onMoment,onCopy}) {
    Object.assign(this,{root,getMotion,onNavigate,onMoment,onCopy});
    this.timer=null;this.animations=[];this.page=0;this.viewGeneration=0;this.turnGeneration=0;
    this.resize=new ResizeObserver(()=>this.layout());
    root.addEventListener('click',e=>this.click(e));
    root.addEventListener('keydown',e=>this.keydown(e));
    root.addEventListener('input',e=>{if(e.target.matches('[data-time-range]'))this.select(Number(e.target.value));});
    document.addEventListener('visibilitychange',()=>{if(document.hidden){this.pause();this.finishTurn();}});
  }
  show(actor,resolved,step,status=PENDING) {
    this.pause();this.finishTurn();this.resize.disconnect();
    const generation=++this.viewGeneration;
    this.actor=actor;this.topic=resolved.record.id;this.record=resolved.record;
    this.pages=buildRecordPages(actor,this.topic,resolved,status);
    this.page=initialPageIndex(this.pages,this.topic,resolved,step,actor);
    const count=this.pages.length;
    this.windowIndices=pageWindow(count,this.page);
    this.hasEvents=this.topic==='timeline'&&this.pages.some(p=>p.moment!==undefined);
    const pending=this.pages.every(p=>p.placeholder);
    this.root.dataset.topic=this.topic;
    this.root.innerHTML=`<div class="orbit-instrument"><div class="orbit-brief"><p>Select a branch to open its card.</p><span>${pending ? h(status||PENDING) : `${count} CARDS`} / ${h(actor?.handle)}</span></div>
      <div class="orbit-workspace"><svg class="orbit-lines" aria-hidden="true"><ellipse class="orbit-track outer"/><ellipse class="orbit-track inner"/><ellipse class="orbit-highlight"/>${this.windowIndices.map(i=>`<g><path class="orbit-hit" data-ring-page="${i}"/><path class="orbit-link" data-ring-link="${i}"/></g>`).join('')}</svg>
      <div class="orbit-node-group" role="group" aria-label="Choose a ${this.record.title.toLowerCase()} card">${this.windowIndices.map(i=>{const p=this.pages[i];return `<button class="orbit-node" data-ring-page="${i}" aria-controls="ring-page" aria-pressed="${i===this.page}"><span class="orbit-node-index">${two(i+1)}</span><span class="orbit-node-text"><b>${h(p.label)}</b><small>${h(p.sub??'OPEN CARD')}</small></span></button>`;}).join('')}</div>
      <div class="orbit-book"><div class="book-stack-layer layer-back" aria-hidden="true"></div><div class="book-stack-layer layer-middle" aria-hidden="true"></div><div class="book-spine" aria-hidden="true">TRACEVEIL / ${this.record.number}</div><div id="ring-page" class="book-live" role="region" aria-labelledby="ring-page-title">${this.pageMarkup()}</div></div></div>
      ${this.hasEvents?`<div class="orbit-playback"><button class="quiet-button" data-play aria-pressed="false">▶ Play timeline</button><label class="sr-only" for="time-range">Choose an activity event</label><input id="time-range" data-time-range type="range" min="0" max="${count-1}" value="${this.page}" step="1"><button class="quiet-button" data-view-moment>View this graph moment ↗</button></div>`:''}
      <p id="ring-page-status" class="sr-only" role="status" aria-live="polite"></p></div>`;
    this.resize.observe(this.root.querySelector('.orbit-workspace'));
    this.resize.observe(this.root.querySelector('.orbit-book'));
    this.updateSelection();
    requestAnimationFrame(()=>{if(generation!==this.viewGeneration)return;this.layout();this.turn();});
  }
  pageMarkup() {
    const p=this.pages[this.page];
    const score=p.score===undefined?'':p.score===null?`<div class="clue-score score-pending"><b>${PENDING}</b><small>CONFIDENCE</small></div>`:`<div class="clue-score" style="--score-angle:${p.score*3.6}deg"><b>${percentMarkup(p.score)}</b><small>CONFIDENCE</small></div>`;
    const identifier='identifier' in p?`<div class="book-identifier"><code>${h(p.identifier)}</code><button class="copy-button" data-copy="${p.identifier?h(p.identifier):''}" ${p.identifier?'':'disabled'}>Copy</button></div>`:'';
    const sourceUrl=safeLink(p.url);
    const source=sourceUrl?`<a class="text-button" href="${h(sourceUrl)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>`:'';
    const links=p.links?.length?`<div class="book-related">${p.links.map(l=>`<button class="text-button" data-explore="${h(l.route)}">${h(l.label)} ↗</button>`).join('')}</div>`:'';
    return `<article class="focus-sheet book-sheet"><div class="sheet-kicker"><span>${p.placeholder?'FIELD':this.topic==='evidence'&&!p.empty?'CLUE':'PAGE'} ${two(this.page+1)} / ${two(this.pages.length)}</span><span>${h(p.kicker)}</span></div><div class="book-title"><h2 id="ring-page-title">${h(p.title)}</h2>${score}</div><p class="focus-copy">${h(p.body)}</p>${identifier}${p.facts?meta(p.facts):''}${p.moment!==undefined?snapshotMarkup(this.actor,p.moment):''}${links}${source}${p.note?`<p class="explorer-note">${h(p.note)}</p>`:''}<footer class="book-controls"><button class="quiet-button" data-book-step="-1" ${this.page===0?'disabled':''} aria-label="Previous card">← Previous</button><span>${this.page+1} / ${this.pages.length}</span><button class="quiet-button" data-book-step="1" ${this.page===this.pages.length-1?'disabled':''} aria-label="Next card">Next →</button></footer></article>`;
  }
  layout() {
    const stage=this.root.querySelector('.orbit-workspace'),book=this.root.querySelector('.orbit-book');
    if(!stage||!book||stage.clientWidth===0)return;
    const w=stage.clientWidth,ht=stage.clientHeight,cx=w/2,cy=ht/2;
    const svg=this.root.querySelector('.orbit-lines');svg.setAttribute('viewBox',`0 0 ${w} ${ht}`);
    const radii=ringRadii(w,ht,book.offsetHeight);
    for(const [selector,factor] of [['.outer',1],['.inner',.88],['.orbit-highlight',1]]){
      const ellipse=svg.querySelector(selector);ellipse.setAttribute('cx',cx);ellipse.setAttribute('cy',cy);ellipse.setAttribute('rx',radii.rx*factor);ellipse.setAttribute('ry',radii.ry*factor);
    }
    const positions=ringGeometry(this.windowIndices.length,w,ht,book.offsetWidth,book.offsetHeight);
    positions.forEach((p,visibleIndex)=>{
      const i=this.windowIndices[visibleIndex];
      const node=this.root.querySelector(`button[data-ring-page="${i}"]`);
      node.style.left=p.x+'px';node.style.top=p.y+'px';node.style.opacity='1';
      const path=`M ${p.startX} ${p.startY} L ${p.x} ${p.y}`;
      svg.querySelector(`.orbit-hit[data-ring-page="${i}"]`).setAttribute('d',path);
      svg.querySelector(`[data-ring-link="${i}"]`).setAttribute('d',path);
    });
  }
  updateWindow() {
    const indices=pageWindow(this.pages.length,this.page);
    if(indices.join(',')===this.windowIndices.join(','))return;
    this.windowIndices=indices;
    this.root.querySelector('.orbit-lines').innerHTML=`<ellipse class="orbit-track outer"/><ellipse class="orbit-track inner"/><ellipse class="orbit-highlight"/>${indices.map(i=>`<g><path class="orbit-hit" data-ring-page="${i}"/><path class="orbit-link" data-ring-link="${i}"/></g>`).join('')}`;
    this.root.querySelector('.orbit-node-group').innerHTML=indices.map(i=>{const p=this.pages[i];return `<button class="orbit-node" data-ring-page="${i}" aria-controls="ring-page"><span class="orbit-node-index">${two(i+1)}</span><span class="orbit-node-text"><b>${h(p.label)}</b><small>${h(p.sub)}</small></span></button>`;}).join('');
  }
  updateSelection() {
    this.root.querySelectorAll('button[data-ring-page]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.ringPage)===this.page)));
    this.root.querySelectorAll('[data-ring-link]').forEach(p=>p.classList.toggle('selected',Number(p.dataset.ringLink)===this.page));
    const range=this.root.querySelector('[data-time-range]');
    const viewMoment=this.root.querySelector('[data-view-moment]');
    if(viewMoment)viewMoment.disabled=!this.actor?.events?.[this.pages[this.page].moment]?.date;
    if(range){range.value=String(this.page);range.setAttribute('aria-valuetext',`${this.pages[this.page].label}: ${this.pages[this.page].title}`);}
    this.root.querySelector('#ring-page-status').textContent=`Card ${this.page+1} of ${this.pages.length}: ${this.pages[this.page].title}`;
  }
  finishTurn() {
    this.turnGeneration++;
    this.animations.forEach(a=>a.cancel());this.animations=[];
    this.root.querySelector('.book-turning-leaf')?.remove();
    const live=this.root.querySelector('.book-live');if(live){live.inert=false;live.setAttribute('aria-busy','false');}
    this.root.querySelector('.orbit-book')?.classList.remove('is-turning');
  }
  turn(focusSelector=null) {
    this.finishTurn();
    const live=this.root.querySelector('.book-live'),book=this.root.querySelector('.orbit-book');
    if(!live||!book)return;
    const restore=()=>{
      if(!focusSelector)return;
      const target=live.querySelector(focusSelector),fallback=live.querySelector('h2');
      const focus=target&&!target.disabled?target:fallback;
      if(focus){if(focus===fallback)focus.tabIndex=-1;focus.focus({preventScroll:true});}
    };
    if(!this.getMotion()||!book.animate){restore();return;}
    const generation=this.turnGeneration,p=this.pages[this.page];
    const leaf=document.createElement('div');leaf.className='book-turning-leaf';leaf.setAttribute('aria-hidden','true');
    leaf.innerHTML=`<div class="book-leaf-front"><div class="leaf-topline"><span>TRACEVEIL / ${h(this.actor?.id)}</span><span>${two(this.page+1)}</span></div><span class="leaf-icon">${icon(this.record.icon)}</span><span class="eyebrow">${h(this.record.title)}</span><strong>${h(p.label)}</strong><span class="leaf-bottom">RECORD / OPENING</span></div><div class="book-leaf-back"><span>${icon(this.record.icon)}</span></div>`;
    book.append(leaf);book.classList.add('is-turning');live.inert=true;live.setAttribute('aria-busy','true');
    const animation=leaf.animate([
      {transform:'rotateY(0deg)',opacity:1,offset:0},
      {transform:'rotateY(-12deg)',opacity:1,offset:.15},
      {transform:'rotateY(-85deg)',opacity:1,offset:.55},
      {transform:'rotateY(-132deg)',opacity:.85,offset:.83},
      {transform:'rotateY(-156deg)',opacity:0,offset:1}
    ],{duration:900,easing:'cubic-bezier(.25,.65,.25,1)',fill:'forwards'});
    this.animations=[animation];
    animation.finished.then(()=>{
      if(generation!==this.turnGeneration)return;
      this.finishTurn();restore();
    }).catch(()=>{});
  }
  select(index,{automatic=false,focusSelector=null}={}) {
    if(!automatic)this.pause();
    this.finishTurn();this.page=Math.max(0,Math.min(Number.isFinite(Number(index))?Math.trunc(Number(index)):0,this.pages.length-1));
    this.root.querySelector('.book-live').innerHTML=this.pageMarkup();
    this.updateWindow();this.updateSelection();this.layout();this.turn(focusSelector);
    if(this.hasEvents)this.onMoment(this.pages[this.page].moment,false);
  }
  leave() {
    this.viewGeneration++;this.pause();this.finishTurn();
  }
  pause() {
    clearInterval(this.timer);this.timer=null;
    const button=this.root.querySelector('[data-play]');
    if(button){button.textContent='▶ Play timeline';button.setAttribute('aria-pressed','false');}
  }
  togglePlayback() {
    if(!this.hasEvents||!this.getMotion())return;
    if(this.timer){this.pause();return;}
    if(this.page===this.pages.length-1)this.select(0);
    const button=this.root.querySelector('[data-play]');button.textContent='Ⅱ Pause timeline';button.setAttribute('aria-pressed','true');
    this.timer=setInterval(()=>{
      this.select(this.page+1,{automatic:true});
      if(this.page===this.pages.length-1)this.pause();
    },3300);
  }
  click(e) {
    const branch=e.target.closest('[data-ring-page]');
    if(branch){this.select(Number(branch.dataset.ringPage));return;}
    const button=e.target.closest('button');if(!button||button.disabled)return;
    const d=button.dataset;
    if(d.copy){this.onCopy(d.copy);return;}
    if(d.explore){this.onNavigate(d.explore);return;}
    if(d.bookStep){this.select(this.page+Number(d.bookStep),{focusSelector:`[data-book-step="${d.bookStep}"]`});return;}
    if('play' in d){this.togglePlayback();return;}
    if('viewMoment' in d){this.pause();this.onMoment(this.pages[this.page].moment,true);}
  }
  keydown(e) {
    const node=e.target.closest('button[data-ring-page]');if(!node)return;
    const count=this.pages.length,current=Number(node.dataset.ringPage);
    let target;
    if(['ArrowRight','ArrowDown'].includes(e.key))target=(current+1)%count;
    if(['ArrowLeft','ArrowUp'].includes(e.key))target=(current+count-1)%count;
    if(e.key==='Home')target=0;if(e.key==='End')target=count-1;
    if(target===undefined)return;
    e.preventDefault();this.select(target);this.root.querySelector(`button[data-ring-page="${target}"]`)?.focus({preventScroll:true});
  }
}
