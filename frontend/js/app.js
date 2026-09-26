// Entry point: shared state + navigation. Individual views live in /views.
import { DotBackground } from './components/background.js';
import { NetworkScene } from './components/network.js';
import { RecordExplorer } from './components/record-explorer.js';
import { createDialogs } from './components/dialogs.js';
import { SearchView } from './views/search.js';
import { ActorView } from './views/actor.js';
import { renderDetail } from './views/detail.js';
import { AccessView } from './views/access.js';
import { ExportView } from './views/exports.js';
import { api,pending,loading } from './services/traceveil-api.js';
import { destinationForNode,destinationForEdge } from './models/workspace.js';
import { text,PENDING } from './utils/display.js';

const $=selector=>document.querySelector(selector);
const $$=selector=>[...document.querySelectorAll(selector)];
const mediaMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
let motion=!mediaMotion.matches,route='login',detailRoute='detail/profile';
let actorResource=pending(),actorController=null,toastTimer=null;
// Glossy is fixed. Old prototype preferences and ?finish=matte are ignored.
// Motion follows the operating system's accessibility preference.
const dialogs=createDialogs(()=>motion);

const background=new DotBackground($('#ambient-canvas'),{onParallax:({x,y})=>{
  document.documentElement.style.setProperty('--surface-pitch',`${-y*1.1}deg`);
  document.documentElement.style.setProperty('--surface-yaw',`${x*1.3}deg`);
}});
const scene=new NetworkScene($('#network-canvas'),{
  actor:null,
  onSelect:id=>navigate(destinationForNode(actorResource.data,id)),
  onEdgeSelect:edge=>navigate(destinationForEdge(actorResource.data,edge)),
  onCamera:view=>{
    $('#orbit-toggle').textContent=view.orbit?'Stop automatic rotation':'Rotate automatically';
    $('#orbit-toggle').setAttribute('aria-pressed',String(view.orbit));
    $('#flatten-view').textContent=view.flat?'Switch to 3D':'Switch to 2D';
    $('#flatten-view').setAttribute('aria-pressed',String(view.flat));
    $('#graph-help').textContent=(view.flat?'Scroll to zoom':'Scroll to rotate')+' · Click a branch to inspect';
  },
});
const actorView=new ActorView({scene,navigate});
const explorer=new RecordExplorer($('#detail-content'),{
  getMotion:()=>motion,onNavigate:navigate,
  onMoment:(step,open)=>{actorView.step=step;actorView.updateGraph();if(open)navigate('actor');},
  onCopy:async value=>{try{await navigator.clipboard.writeText(value);notify('Identifier copied.');}catch{notify('Select the identifier text to copy it.');}},
});
const search=new SearchView({dialogs,getMotion:()=>motion,onSelect:selectActor,onStatus:connectionStatus});
const access=new AccessView({navigate,onChange:()=>{
  clearWorkspace();if(access.canRead())search.loadSuggestions();
}});
const exportsView=new ExportView({dialogs,getActor:()=>actorResource.data,canRead:()=>access.canRead(),onStatus:connectionStatus});

// Always wait for a real personnel session before opening the workspace.
$('#search-form').addEventListener('submit',event=>{
  if(!access.canRead()){event.preventDefault();event.stopImmediatePropagation();access.open();}
},true);

function notify(message) {
  clearTimeout(toastTimer);$('#toast').textContent=message;$('#toast').classList.add('visible');
  toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),3000);
}
function connectionStatus(resource) {
  if(resource.code===401){access.expire();clearWorkspace();access.open();return false;}
  $('#connection-status').textContent=resource.status==='ready'||resource.status==='empty'?'Response received':resource.status==='loading'?'Connecting…':resource.status==='error'?'Connection unavailable':PENDING;
}
function clearWorkspace() {
  actorController?.abort();actorController=null;search.clear();exportsView.cancel();explorer.leave();
  actorResource=pending();actorView.resetFilters();actorView.render(actorResource);
  $('#detail-content').replaceChildren();$('#connection-status').textContent=PENDING;
  navigate('search');
}
function navigate(next) {
  if(location.hash.slice(1)!==next)history.pushState(null,'','#'+next);
  showRoute(next,true);
}
function showRoute(next,focus=false) {
  // BACKEND CONNECT: AccessView reads the real session/login response.
  // Missing endpoints never grant access. The server also authorizes each API.
  if(!access.canRead())next='login';
  route=next==='login'?'login':next?.startsWith('detail/')?'detail':next==='actor'?'actor':'search';
  if(route==='login'&&location.hash!=='#login')history.replaceState(null,'','#login');
  search.cancel(false);dialogs.closeAll();explorer.leave();
  $$('.screen').forEach(screen=>screen.hidden=screen.id!==`screen-${route}`);
  document.body.dataset.screen=route;
  let title=route==='login'?'Personnel access':route==='search'?'Search':text(actorResource.data?.handle);
  if(route==='detail'){
    detailRoute=next;title=renderDetail(actorResource,detailRoute,explorer,scene,actorView.step);
    $('#detail-nav').href='#'+detailRoute;
  }
  scene.setActive(route==='actor');
  $$('[data-route]').forEach(link=>{if(link.dataset.route===route)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
  document.title=`TraceVeil / ${title}`;
  if(focus){
    const screen=$(`#screen-${route}`),heading=screen.querySelector('h1');
    heading.tabIndex=-1;heading.focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});
    screen.getAnimations().forEach(animation=>animation.cancel());
    if(motion)screen.animate([{opacity:0,transform:'translateY(8px)'},{opacity:1,transform:'translateY(0)'}],{duration:280,easing:'ease-out'});
  }
}
async function selectActor(summary) {
  if(!access.canRead()){access.open();return;}
  actorController?.abort();const controller=new AbortController();actorController=controller;
  actorResource={...loading(),data:summary}; // This summary is from the real search response.
  actorView.resetFilters();scene.reset();actorView.render(actorResource);detailRoute='detail/profile';
  $('#detail-nav').href='#detail/profile';navigate('actor');
  try {
    // BACKEND CONNECT: This endpoint returns all six detail sections + the graph.
    // Separate endpoints can be combined in BACKEND_CONNECT.js → backendCalls.actor.
    let result=await api.actor(summary.id,controller.signal);
    if(controller.signal.aborted||actorController!==controller)return;
    if(result.status==='ready'&&result.data.id!==summary.id)result={status:'error',data:null,message:'The returned actor ID does not match the selected account.'};
    if(result.code===401||result.code===403){clearWorkspace();connectionStatus(result);notify(result.message);return;}
    actorResource={...result,data:result.data??summary};actorController=null;
    actorView.render(actorResource);connectionStatus(result);
    if(route==='detail')renderDetail(actorResource,detailRoute,explorer,scene,actorView.step);
    if(route==='actor')document.title=`TraceVeil / ${text(actorResource.data?.handle)}`;
  } catch(error) {if(!controller.signal.aborted)notify(error.message);}
}

function applyFinish() {
  document.body.dataset.finish='glossy';background.setFinish('glossy');scene.setFinish('glossy');
  $('meta[name="theme-color"]').content='#040f0b';
}
function applyMotion() {
  document.body.classList.toggle('reduced-motion',!motion);background.setMotion(motion);scene.setMotion(motion);
  if(!motion){explorer.finishTurn();explorer.pause();}
}
mediaMotion.addEventListener('change',event=>{motion=!event.matches;applyMotion();});
window.addEventListener('hashchange',()=>showRoute(location.hash.slice(1),true));
$('.skip-link').addEventListener('click',event=>{event.preventDefault();$('#main').tabIndex=-1;$('#main').focus();});
$('#help-button').addEventListener('click',()=>dialogs.open($('#help-dialog')));
$('#filters-button').addEventListener('click',()=>dialogs.open($('#filters-dialog')));
applyFinish();applyMotion();actorView.render(actorResource);showRoute(location.hash.slice(1));
access.load().then(allowed=>{
  const firstRoute=allowed?'search':'login';
  history.replaceState(null,'','#'+firstRoute);showRoute(firstRoute);
  if(allowed)search.loadSuggestions();
});
