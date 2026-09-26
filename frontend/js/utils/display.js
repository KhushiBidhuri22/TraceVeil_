export const PENDING = 'Connection pending';
export const text = value => value === null || value === undefined || value === '' ? PENDING : String(value);
export const h = value => text(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const percent = value => typeof value === 'number' && Number.isFinite(value) ? `${value}%` : PENDING;
// Use this helper for any future backend progress/confidence percentage too.
// It does not invent a value: null/undefined remain Connection pending.
export const percentMarkup = value => typeof value === 'number' && Number.isFinite(value)
  ? `<span class="technical-percent" style="--percent-characters:${String(value).length+1}">${h(percent(value))}</span>`
  : h(PENDING);
export const countLabel = (items, label) => Array.isArray(items) ? `${items.length} ${label}` : PENDING;
export const listText = (items, key) => !Array.isArray(items) ? PENDING : items.length ? items.map(item => text(key ? item[key] : item)).join(' · ') : 'None returned';
export function stamp(value, compact = false) {
  if (!value || !Number.isFinite(Date.parse(value))) return PENDING;
  return new Intl.DateTimeFormat('en-GB', {
    day:'2-digit', month:'short', year:'numeric', timeZone:'UTC',
    ...(compact ? {} : {hour:'2-digit', minute:'2-digit', hour12:false}),
  }).format(new Date(value)) + (compact ? '' : ' UTC');
}
export const facts = (rows, className = 'focus-facts') => `<dl class="${className}">${rows.map(([label,value]) => `<div><dt>${h(label)}</dt><dd>${h(value)}</dd></div>`).join('')}</dl>`;
export const statusMessage = resource => ({
  pending: PENDING,
  loading: 'Loading account records…',
  empty: 'No records returned',
  error: resource?.message || 'Unable to load records. Try again.',
  ready: '',
}[resource?.status ?? 'pending']);
export function safeLink(value) {
  if (typeof value !== 'string') return null;
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; }
  catch { return null; }
}
