// Internal normalization and validation.
// Backend teammate: field names and response paths live in BACKEND_CONNECT.js.
// Missing/null data remains null. An actual [] means the server returned none.
import { layoutGraph } from '../models/graph.js';
import { fields, responsePaths } from '../../BACKEND_CONNECT.js';

// Read a configured JSON path without traversing inherited properties.
export function readField(source, selector) {
  if (typeof selector === 'function') return selector(source);
  if (selector === '') return source;
  if (typeof selector !== 'string') return undefined;
  return selector.split('.').reduce((value, key) => value !== null && value !== undefined && Object.hasOwn(Object(value), key) ? value[key] : undefined, source);
}
const renameFields = (row, mapping) => Object.fromEntries(
  Object.entries(mapping).map(([frontendName, backendName]) => [frontendName, readField(row, backendName)])
);

const string = v => typeof v === 'string' && v.trim() ? v : null;
const id = v => typeof v === 'number' && Number.isFinite(v) ? String(v) : string(v);
const score = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 100 ? v : null;
const date = v => string(v) && Number.isFinite(Date.parse(v)) ? v : null;
const object = (v, label) => {
  if (!v || typeof v !== 'object' || Array.isArray(v)) throw new Error(`Invalid ${label} response. Check fields in BACKEND_CONNECT.js.`);
  return v;
};
const array = (value, map, label, fieldNames) => {
  if (value === undefined || value === null) return null;
  if (!Array.isArray(value)) throw new Error(`Expected an array for ${label}. Check fields in BACKEND_CONNECT.js.`);
  return value.map((item, index) => map(renameFields(object(item, label), fieldNames), index));
};
function requiredId(value, label) {
  const result = id(value);
  if (!result) throw new Error(`${label} needs a stable id. Check fields in BACKEND_CONNECT.js.`);
  return result;
}
const common = row => ({
  id:requiredId(row.id, 'Record'), title:string(row.title), detail:string(row.detail),
  source:string(row.source), date:date(row.date), confidence:score(row.confidence),
  nodeId:id(row.nodeId), url:string(row.url),
});

export function mapActor(raw) {
  const row = renameFields(object(raw, 'actor'), fields.actor);
  const handle = string(row.handle);
  const actor = {
    id:requiredId(row.id, 'Actor'), handle,
    initials:handle ? handle.replace(/[^a-z0-9]/gi, '').slice(0,2).toUpperCase() : null,
    description:string(row.description), priority:string(row.priority),
    confidence:score(row.confidence), firstSeen:date(row.firstSeen), lastSeen:date(row.lastSeen),
    aliases:array(row.aliases, alias => ({id:requiredId(alias.id,'Alias'), handle:string(alias.handle), detail:string(alias.detail), confidence:score(alias.confidence), nodeId:id(alias.nodeId)}), 'aliases', fields.alias),
    keys:array(row.keys, key => ({...common(key), value:string(key.value), algorithm:string(key.algorithm)}), 'keys', fields.key),
    wallets:array(row.wallets, wallet => ({...common(wallet), value:string(wallet.value), network:string(wallet.network)}), 'wallets', fields.wallet),
    evidence:array(row.evidence, clue => ({...common(clue), method:string(clue.method)}), 'evidence', fields.evidence),
    sources:array(row.sources, source => ({...common(source), name:string(source.name), observedAt:date(source.observedAt)}), 'sources', fields.source),
    events:array(row.events, event => ({...common(event), label:string(event.label)}), 'events', fields.event),
    graph:null,
  };
  // Sort real timestamps; undated events remain present, at the end.
  actor.events?.sort((a,b) => (a.date ? Date.parse(a.date) : Infinity) - (b.date ? Date.parse(b.date) : Infinity));
  if (row.graph !== undefined && row.graph !== null) {
    const graph = renameFields(object(row.graph, 'graph'), fields.graph);
    if (!Array.isArray(graph.nodes) || !Array.isArray(graph.edges)) throw new Error('Graph needs nodes and edges arrays. Check fields in BACKEND_CONNECT.js.');
    const nodes = array(graph.nodes, node => {
      if (!['actor','alias','key','wallet','source'].includes(node.type)) throw new Error('Unsupported graph node type. Check fields in BACKEND_CONNECT.js.');
      return ({
      id:requiredId(node.id,'Graph node'), name:string(node.name) ?? 'Connection pending',
      type:node.type,
      identifier:string(node.identifier), relation:string(node.relation), detail:string(node.detail),
      confidence:score(node.confidence), observedAt:date(node.observedAt), recordId:id(node.recordId),
      position:Array.isArray(node.position) && node.position.length === 3 && node.position.every(n => typeof n === 'number' && Number.isFinite(n) && Math.abs(n) <= 300) ? node.position : null,
    }); }, 'graph.nodes', fields.node);
    const ids = new Set(nodes.map(node => node.id));
    if (ids.size !== nodes.length) throw new Error('Graph node ids must be unique. Check fields in BACKEND_CONNECT.js.');
    const edges = array(graph.edges, edge => ({
      id:requiredId(edge.id,'Graph edge'), from:requiredId(edge.from,'Edge origin'), to:requiredId(edge.to,'Edge target'),
      kind:string(edge.kind), confidence:score(edge.confidence), observedAt:date(edge.observedAt),
    }), 'graph.edges', fields.edge);
    if (edges.some(edge => !ids.has(edge.from) || !ids.has(edge.to))) throw new Error('Graph edge references a missing node. Check fields in BACKEND_CONNECT.js.');
    if (new Set(edges.map(edge => edge.id)).size !== edges.length) throw new Error('Graph edge ids must be unique.');
    actor.graph = {nodes:layoutGraph(nodes), edges};
  }
  return actor;
}

export function mapSearch(payload) {
  const rows = readField(payload, responsePaths.search);
  if (!Array.isArray(rows)) throw new Error('Search needs an account array. Check responsePaths.search in BACKEND_CONNECT.js.');
  const items = rows.map(mapActor);
  if (new Set(items.map(item => item.id)).size !== items.length) throw new Error('Search result ids must be unique.');
  return items;
}
export function mapSuggestions(payload) {
  const rows = readField(payload, responsePaths.suggestions);
  if (!Array.isArray(rows)) throw new Error('Suggestions need an array. Check responsePaths.suggestions in BACKEND_CONNECT.js.');
  return rows.map(raw => {
    const item = renameFields(object(raw, 'suggestion'), fields.suggestion);
    if (!string(item.value) || !string(item.label)) throw new Error('A suggestion needs label and value.');
    return {label:item.label, value:item.value, type:['handle','wallet','key'].includes(item.type) ? item.type : 'all'};
  });
}
export function mapActorResponse(payload) { return mapActor(readField(payload, responsePaths.actor)); }
export function mapSession(payload, responseType='session') {
  const raw = readField(payload, responsePaths[responseType]);
  if (raw === null) return null;
  const user = renameFields(object(raw, 'session user'), fields.user);
  return {id:requiredId(user.id,'User'), name:string(user.name), role:string(user.role)};
}
