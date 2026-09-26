import { records,icon,resolveDetail } from '../models/workspace.js';
import { statusMessage } from '../utils/display.js';
export function renderDetail(resource,route,explorer,scene,step) {
  const actor=resource.data,resolved=resolveDetail(actor,route),record=resolved.record;
  document.querySelector('#detail-title').textContent=record.title;
  document.querySelector('#related-records').innerHTML=records.map(r=>`<a href="#detail/${r.id}" ${r.id===record.id?'aria-current="page"':''}><span>${icon(r.icon)}</span>${r.title}</a>`).join('');
  scene.setSelected(resolved.node?.id??'');
  explorer.show(actor,resolved,step,statusMessage(resource));
  return record.title;
}
