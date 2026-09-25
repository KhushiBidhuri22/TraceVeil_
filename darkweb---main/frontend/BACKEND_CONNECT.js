/*
 * BACKEND TEAMMATE — START HERE
 *
 * This is the one file for connecting the existing frontend.
 * 1. SERVER: fill the real server address and API paths.
 * 2. RESPONSE: say where each response contains its data.
 * 3. FIELDS: match the backend's field names to the screen's field names.
 * 4. REQUESTS: adjust HTTP methods/query/body only if your API needs it.
 *
 * UI, CSS, animations and rendering are already connected to this file.
 * Leave unfinished endpoints null: the screen shows "Connection pending".
 * All strings below are field names/settings, not investigation data.
 */

// 1 — SERVER ADDRESS AND ENDPOINT PATHS
function resolveBaseUrl() {
  if (typeof window === 'undefined') return 'http://localhost:8000';
  
  if (window.__API_BASE_URL__) return window.__API_BASE_URL__;

  const hostname = window.location.hostname || '';
  const port = window.location.port || '';

  // If running locally on a separate dev server port (e.g. Live Server on 5500, Vite on 5173, etc.)
  if ((hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '') && port && port !== '8000') {
    return `${window.location.protocol}//${hostname}:8000`;
  }

  // Localtunnel
  if (hostname.includes('loca.lt')) {
    return '';
  }

  // When served directly by the backend (localhost:8000, Render, Docker, or any production cloud deployment),
  // return '' so all API requests use relative paths against the current domain.
  return '';
}

export const apiConfig = {
  get baseUrl() {
    return resolveBaseUrl();
  },
  set baseUrl(val) {
    if (typeof window !== 'undefined') window.__API_BASE_URL__ = val;
  },
  credentials: 'include', // Cookie session. Backend must authorize requests.
  timeoutMs: 15000,
  endpoints: {
    suggestions: '/api/suggestions', // "Try" dropdown
    search: '/api/search',      // Search results popup
    actor: '/api/actors/:id',   // Selected account: profile, graph and all six sections
    export: '/api/export/:id',  // CSV / JSON / report download
    session: '/api/auth/session', // Check the signed-in personnel account
    login: '/api/auth/login',   // Sign in
    logout: '/api/auth/logout', // Sign out
  },
};
// Paths can contain :id; the frontend substitutes the selected actor's ID.
// baseUrl '' uses the frontend origin. The local dev server is not an API proxy.

// 2 — WHERE IS THE DATA INSIDE THE JSON RESPONSE?
// Use a dot path for nested JSON, or '' if the whole response is the data.
// Example of a FIELD PATH only: 'data.results' reads response.data.results.
export const responsePaths = {
  suggestions: 'items', // Must point to the array for the Try dropdown
  search: 'items',      // Must point to the array of matching accounts
  actor: 'actor',       // Must point to the selected account object
  session: 'user',      // Must point to the user object, or null when signed out
  login: 'user',        // User object returned by successful sign-in
};

// 3 — FIELD NAMES
// LEFT = frontend name; RIGHT = your actual backend field name.
// Change the RIGHT side. A dot path is allowed, e.g. handle: 'profile.username'.
// Missing fields stay pending. Actual empty arrays mean "no records returned".
// A function is also allowed for conversions, but preserve missing values.
// Confidence is 0–100; timestamps should be ISO strings including timezone.
const recordFields = {
  id: 'id', title: 'title', detail: 'detail', source: 'source', date: 'date',
  confidence: 'confidence', nodeId: 'nodeId', url: 'url',
};

export const fields = {
  actor: {
    id: 'id',
    handle: 'handle',
    description: 'description',
    priority: 'priority',
    confidence: 'confidence',
    firstSeen: 'firstSeen',
    lastSeen: 'lastSeen',
    aliases: 'aliases',
    keys: 'keys',
    wallets: 'wallets',
    evidence: 'evidence',
    sources: 'sources',
    events: 'events',
    graph: 'graph',
  },
  // Each object below describes ONE item in the corresponding array.
  alias: {
    id: 'id', handle: 'handle', detail: 'detail',
    confidence: 'confidence', nodeId: 'nodeId',
  },
  key: { ...recordFields, value: 'value', algorithm: 'algorithm' },
  wallet: { ...recordFields, value: 'value', network: 'network' },
  evidence: { ...recordFields, method: 'method' },
  source: { ...recordFields, name: 'name', observedAt: 'observedAt' },
  event: { ...recordFields, label: 'label' },
  graph: { nodes: 'nodes', edges: 'edges' },
  node: {
    id: 'id', name: 'name', type: 'type', identifier: 'identifier',
    relation: 'relation', detail: 'detail', confidence: 'confidence',
    observedAt: 'observedAt', recordId: 'recordId', position: 'position',
  },
  edge: {
    id: 'id', from: 'from', to: 'to', kind: 'kind',
    confidence: 'confidence', observedAt: 'observedAt',
  },
  suggestion: { label: 'label', value: 'value', type: 'type' },
  user: { id: 'id', name: 'name', role: 'role' },
};
// Node type values: actor / alias / key / wallet / source.
// Suggestion type values: all / handle / key / wallet.
// IDs must be stable. Graph edges must reference actual returned node IDs.
// Link a record and graph node with record.nodeId or node.recordId.

// 4 — REQUESTS SENT TO THE BACKEND
// The shared request() function already handles fetch, cookies, timeouts and errors.
// Keep id and signal when editing: they preserve selection and cancellation.
export const backendCalls = {
  suggestions: (request, {signal}) =>
    request('suggestions', {signal}),

  search: (request, {q, type, signal}) =>
    request('search', {query: {q, type}, signal}),

  actor: (request, {id, signal}) =>
    request('actor', {id, signal}),

  session: (request, {signal}) =>
    request('session', {signal}),

  login: (request, {username, password, signal}) =>
    request('login', {method: 'POST', body: {username, password}, signal}),

  logout: (request, {signal}) =>
    request('logout', {method: 'POST', signal}),

  export: (request, {id, format, signal}) =>
    request('export', {id, query: {format}, file: true, signal}),
};
// If actor details use multiple endpoints, add their paths in apiConfig.endpoints
// and combine their responses inside backendCalls.actor above. Return the same
// response structure described by responsePaths.actor and fields.actor.

// OPTIONAL — HEADERS REQUIRED BY YOUR AUTHENTICATION SYSTEM
export async function getRequestHeaders() {
  return {}; // Add runtime CSRF/auth headers here when the backend requires them.
}
// Never hardcode service secrets or passwords in browser-visible configuration.
