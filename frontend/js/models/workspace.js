export const records = [
  {id:'profile', number:'01', title:'ACCOUNT PROFILE', icon:'profile'},
  {id:'key', number:'02', title:'SIGNING KEY', icon:'key'},
  {id:'wallet', number:'03', title:'WALLET REFERENCE', icon:'wallet'},
  {id:'evidence', number:'04', title:'EVIDENCE & CONFIDENCE', icon:'evidence'},
  {id:'sources', number:'05', title:'SOURCE RECORDS', icon:'sources'},
  {id:'timeline', number:'06', title:'ACTIVITY TIMELINE', icon:'timeline'}
];

const iconPaths = {
  profile:'M8 20v-3l4-3h8l4 3v3M20 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z M5 3H2v7M27 3h3v7M2 22v7h7M30 22v7h-7',
  key:'M13 16a7 7 0 1 1-2-9 7 7 0 0 1 2 9ZM13 16l15 0v5h-5v-5M8 10h.01',
  wallet:'M4 9V5h21v4M3 9h26v18H3ZM21 15h8v7h-8zM24 18h.01',
  evidence:'M5 27V16h5v11M14 27V9h5v18M23 27V3h5v24M2 29h29',
  sources:'M4 3h10l5 5v17H4ZM14 3v6h5M22 10h6v19H10v-1M8 13h7M8 17h7',
  timeline:'M4 26V5M4 9h9M4 17h17M4 25h25M15 6v6M23 14v6M29 22v6'
};
export const icon = name => `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="miter" aria-hidden="true"><path d="${iconPaths[name] ?? iconPaths.profile}"/></svg>`;

export const topicForNode = node => ({actor:'profile',alias:'profile',key:'key',wallet:'wallet',source:'sources'}[node?.type] ?? 'profile');
export const edgeId = edge => edge.id;
export function destinationForNode(actor, id) {
  const node = actor?.graph?.nodes.find(n => n.id === id);
  return node ? `detail/${topicForNode(node)}/node/${encodeURIComponent(id)}` : 'detail/profile';
}
export function destinationForEdge(actor, edge) {
  const node = actor?.graph?.nodes.find(n => n.id === edge.to);
  return node ? `detail/${topicForNode(node)}/edge/${encodeURIComponent(edge.id)}` : 'detail/profile';
}
export function resolveDetail(actor, raw = 'detail/profile') {
  const [,proposed='profile',kind='',encoded=''] = raw.split('/');
  const record = records.find(r => r.id === proposed) ?? records[0];
  let id = '';
  try { id = decodeURIComponent(encoded); } catch { /* Malformed links fall back to the chapter. */ }
  const edge = kind === 'edge' ? actor?.graph?.edges.find(e => e.id === id) ?? null : null;
  const node = actor?.graph?.nodes.find(n => n.id === (edge?.to ?? (kind === 'node' ? id : null))) ?? null;
  const consistent = node && topicForNode(node) === record.id;
  return {record,edge:consistent ? edge : null,node:consistent ? node : null};
}
