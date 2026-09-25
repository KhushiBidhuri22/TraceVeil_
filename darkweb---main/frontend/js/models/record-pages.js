import { PENDING, text, stamp, listText, countLabel } from '../utils/display.js';

const labels = {
  profile:['ACCOUNT','USERNAMES','RECORD DETAILS','REVIEW STATUS'],
  key:['SIGNING KEY','ACCOUNT LINKS','SOURCE','CONFIDENCE'],
  wallet:['WALLET','ACCOUNT LINKS','SOURCE','CONFIDENCE'],
  evidence:['EVIDENCE','METHOD','SOURCE','CONFIDENCE'],
  sources:['SOURCE','OBSERVATIONS','REFERENCE','COLLECTED AT'],
  timeline:['ACTIVITY','OBSERVED AT','SOURCE','GRAPH MOMENT'],
};
// These are named UI fields, not generated investigation records.
function pendingPages(topic, status = PENDING) {
  return labels[topic].map((label,i) => ({
    id:`field-${i}`, label, sub:status, title:label, kicker:status,
    body:status, facts:[['Record',status],['Source',status]], note:status, placeholder:true,
  }));
}
function emptyPage(topic) {
  return [{id:'empty',label:labels[topic][0],sub:'NO RECORDS',title:'No records returned',kicker:labels[topic][0],body:'The server returned no entries for this section.',note:'',empty:true}];
}
const review = 'Review the source context before accepting a suggested connection.';
const commonPage = (row, label) => ({
  id:row.id, nodeId:row.nodeId, label:text(row.title ?? label), sub:row.source ?? PENDING,
  title:text(row.title ?? label), body:text(row.detail), score:row.confidence,
  facts:[['Source',text(row.source)],['Observed at',stamp(row.date)]],
  note:review, url:row.url,
});

// BACKEND CONNECT: These view models read only the canonical actor from mappers.js.
// Never add example values here to make a missing response look complete.
export function buildRecordPages(actor, topic, {node=null,edge=null} = {}, resourceStatus=PENDING) {
  if (!actor) return pendingPages(topic, resourceStatus || PENDING);
  let pages;
  if (topic === 'profile') {
    pages = [
      {id:actor.id,label:'ACCOUNT',sub:text(actor.handle),title:text(actor.handle),kicker:'PRIMARY USERNAME',body:text(actor.description),score:actor.confidence,facts:[['Record ID',actor.id],['Review status',text(actor.priority)]],note:review},
      ...(actor.aliases === null ? [{...pendingPages('profile')[1],id:'aliases-pending'}] : actor.aliases.map(alias => ({
        id:alias.id,nodeId:alias.nodeId,label:text(alias.handle),sub:'CONNECTED USERNAME',title:text(alias.handle),kicker:'POSSIBLE ALIAS',body:text(alias.detail),score:alias.confidence,note:review,
        links:[{route:'detail/evidence',label:'Review evidence'}],
      }))),
      {id:'account-dates',label:'RECORD DETAILS',sub:'DATES & SOURCES',title:'Account record',kicker:text(actor.id),body:text(actor.description),facts:[['First seen',stamp(actor.firstSeen)],['Last seen',stamp(actor.lastSeen)],['Sources',listText(actor.sources,'name')],['Evidence',countLabel(actor.evidence,'records')]],note:'Usernames alone do not establish a verified real-world identity.'},
    ];
  } else {
    const collection = actor[{key:'keys',wallet:'wallets',evidence:'evidence',sources:'sources',timeline:'events'}[topic]];
    if (collection === null) pages = pendingPages(topic);
    else if (collection.length === 0) pages = emptyPage(topic);
    else pages = collection.map((row,index) => {
      const base = commonPage(row, labels[topic][0]);
      if (topic === 'key' || topic === 'wallet') return {
        ...base, label:row.title ?? row.value ?? labels[topic][0], kicker:topic === 'key' ? 'SIGNING KEY' : 'WALLET REFERENCE', identifier:row.value,
        facts:[...base.facts,[topic === 'key' ? 'Algorithm' : 'Network',text(topic === 'key' ? row.algorithm : row.network)]],
      };
      if (topic === 'evidence') return {...base,kicker:text(row.method),facts:[...base.facts,['Method',text(row.method)]]};
      if (topic === 'sources') return {...base,label:text(row.name),title:text(row.name),kicker:'SOURCE RECORD',facts:[['Record ID',row.id],['Collected at',stamp(row.observedAt)],['Observation date',stamp(row.date)]]};
      return {...base,label:row.date ? stamp(row.date,true) : 'DATE PENDING',sub:text(row.label),kicker:stamp(row.date),moment:index,note:row.date ? 'The snapshot includes only records with observation dates at or before this event.' : 'Connection pending'};
    });
  }
  // A graph branch has its own card, linked to the exact backend edge.
  if (edge && node) {
    const from = actor.graph?.nodes.find(n => n.id === edge.from);
    pages.unshift({id:`edge:${edge.id}`,label:'SELECTED BRANCH',sub:text(edge.kind),title:`${text(from?.name)} → ${text(node.name)}`,kicker:'CONNECTION RECORD',body:text(node.detail),score:edge.confidence,facts:[['Relationship',text(edge.kind)],['Observed at',stamp(edge.observedAt)],['Edge ID',edge.id]],note:review});
  } else if (node && !pages.some(p => p.nodeId === node.id || p.id === node.recordId || p.id === node.id)) {
    pages.unshift({id:`node:${node.id}`,nodeId:node.id,label:text(node.name),sub:'SELECTED NODE',title:text(node.name),kicker:node.type.toUpperCase(),body:text(node.detail),score:node.confidence,identifier:node.identifier,facts:[['Relationship',text(node.relation)],['Observed at',stamp(node.observedAt)]],note:review});
  }
  return pages;
}

export function initialPageIndex(pages, topic, {node=null,edge=null} = {}, step=null) {
  if (edge) return 0;
  if (topic === 'timeline' && step !== null) return Math.max(0,pages.findIndex(p => p.moment === step));
  if (node) return Math.max(0,pages.findIndex(p => p.nodeId === node.id || p.id === node.recordId || p.id === node.id));
  return 0;
}

// Show at most six branches at once without dropping any records.
export function pageWindow(total, page, size=6) {
  const start = Math.floor(page / size) * size;
  return Array.from({length:Math.min(size,total-start)}, (_,i) => start+i);
}
export function ringRadii(width,height,bookHeight) {
  return {rx:width*.42,ry:Math.min(height/2-40,Math.max(height*.43,bookHeight/2+70))};
}
export function ringGeometry(count,width,height,bookWidth,bookHeight) {
  const cx=width/2,cy=height/2,{rx,ry}=ringRadii(width,height,bookHeight);
  const angles=count===4?[-90,0,90,180]:Array.from({length:count},(_,i)=>-90+i*360/count);
  const compact=width<860,topCount=Math.ceil(count/2),bottomCount=count-topCount;
  return angles.map((deg,i)=>{
    const r=deg*Math.PI/180;
    const x=compact?(i<topCount?(i+1)*width/(topCount+1):(i-topCount+1)*width/(bottomCount+1)):cx+Math.cos(r)*rx;
    const y=compact?(i<topCount?45:height-45):cy+Math.sin(r)*ry;
    const dx=x-cx,dy=y-cy;
    const distance=Math.min((bookWidth/2+15)/Math.max(Math.abs(dx),.001),(bookHeight/2+15)/Math.max(Math.abs(dy),.001));
    return {x,y,startX:cx+dx*Math.min(distance,.99),startY:cy+dy*Math.min(distance,.99)};
  });
}
