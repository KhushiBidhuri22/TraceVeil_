import { request, ConnectionPending } from './http.js';
import { mapActorResponse, mapSearch, mapSuggestions, mapSession } from './mappers.js';
import { backendCalls } from '../../BACKEND_CONNECT.js';

export const pending = () => ({status:'pending', data:null, message:'Connection pending'});
export const loading = () => ({status:'loading', data:null});

// Internal adapter. Request settings are in frontend/BACKEND_CONNECT.js.
// Errors are displayed honestly; they never fall back to made-up records.
export async function resource(operation, signal) {
  try {
    const data = await operation();
    if (signal?.aborted) throw new DOMException('Cancelled', 'AbortError');
    return {status:Array.isArray(data) && data.length === 0 ? 'empty' : 'ready', data};
  } catch (error) {
    if (signal?.aborted || error.name === 'AbortError') throw error;
    if (error instanceof ConnectionPending) return pending();
    return {status:'error', data:null, message:error.message, code:error.status ?? 0};
  }
}
export const api = {
  suggestions: signal => resource(async () => mapSuggestions(await backendCalls.suggestions(request,{signal})), signal),
  search: (q,type,signal) => resource(async () => mapSearch(await backendCalls.search(request,{q,type,signal})), signal),
  actor: (id,signal) => resource(async () => mapActorResponse(await backendCalls.actor(request,{id,signal})), signal),
  session: signal => resource(async () => mapSession(await backendCalls.session(request,{signal})), signal),
  login: (username,password,signal) => resource(async () => mapSession(await backendCalls.login(request,{username,password,signal}),'login'), signal),
  logout: signal => resource(() => backendCalls.logout(request,{signal}), signal),
  export: (id,format,signal) => resource(() => backendCalls.export(request,{id,format,signal}), signal),
};
