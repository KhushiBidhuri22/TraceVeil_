import { apiConfig, getRequestHeaders } from '../config/api.js';

export class ConnectionPending extends Error {}
export class ApiError extends Error {
  constructor(message, status = 0) { super(message); this.status = status; }
}
export const isConnected = name => typeof apiConfig.endpoints[name] === 'string' && apiConfig.endpoints[name].trim() !== '';

// Every network request goes through here. Components never contain fetch().
export async function request(name, {id, query, body, method = 'GET', signal, file = false} = {}) {
  if (!isConnected(name)) throw new ConnectionPending('Connection pending');
  const path = apiConfig.endpoints[name].replaceAll(':id', encodeURIComponent(id ?? ''));
  if (apiConfig.endpoints[name].includes(':id') && !id) throw new ConnectionPending('Connection pending');
  const base = apiConfig.baseUrl.trim().replace(/\/$/, '');
  const address = /^https?:\/\//i.test(path) ? path : base + '/' + path.replace(/^\//, '');
  const url = new URL(address, globalThis.location?.origin ?? 'http://localhost');
  if (!['http:', 'https:'].includes(url.protocol)) throw new ApiError('Unsupported API address.');
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== null && value !== undefined && value !== '') url.searchParams.set(key, String(value));
  }
  const controller = new AbortController();
  const cancel = () => controller.abort(signal?.reason);
  if (signal?.aborted) cancel();
  signal?.addEventListener('abort', cancel, {once:true});
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, apiConfig.timeoutMs);
  try {
    const headers = {
      Accept: file ? '*/*' : 'application/json',
      'Bypass-Tunnel-Reminder': 'true',
      ...await getRequestHeaders(),
    };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const response = await fetch(url, {
      method, headers, credentials:apiConfig.credentials, signal:controller.signal,
      cache:'no-store', ...(body !== undefined ? {body:JSON.stringify(body)} : {}),
    });
    if (!response.ok) {
      const message = response.status === 401 ? 'Sign in to access these records.'
        : response.status === 403 ? 'Your account does not have access to these records.'
        : response.status === 404 ? 'The requested record or endpoint was not found.'
        : `The server returned an error (${response.status}). Try again.`;
      throw new ApiError(message, response.status);
    }
    if (file) return {blob:await response.blob(), disposition:response.headers.get('Content-Disposition')};
    if (response.status === 204) return null;
    if (!response.headers.get('Content-Type')?.includes('json')) {
      throw new ApiError('Expected JSON. Check the endpoint and response format.');
    }
    return await response.json();
  } catch (error) {
    if (signal?.aborted) throw error;
    if (timedOut) throw new ApiError('The request timed out. Try again.');
    if (error instanceof ApiError) throw error;
    throw new ApiError('Could not reach the server. Check the connection and try again.');
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}
