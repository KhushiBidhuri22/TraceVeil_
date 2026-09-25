# TraceVeil — backend integration contract

This document specifies the frontend's expected contract. **It does not claim that these endpoints already exist.** All endpoint values in `BACKEND_CONNECT.js` initially equal `null`.

## Central integration points

| Change needed | Edit |
|---|---|
| API origin and endpoint paths | `BACKEND_CONNECT.js` |
| GET/POST, query names, request JSON | `BACKEND_CONNECT.js` → `backendCalls` |
| Backend response names/shape | `BACKEND_CONNECT.js` → `responsePaths` and `fields` |
| Credentials, cookies or CSRF headers | `BACKEND_CONNECT.js` → `apiConfig` and `getRequestHeaders` |

**Start with `BACKEND-START-HERE.md`. All integration settings now live in the root `BACKEND_CONNECT.js` file.**

Keep network calls out of visual components. With the contract below, the components do not need to know which backend framework is used.

## Endpoint configuration and requests

| Config key | Method | Frontend sends | Frontend expects |
|---|---|---|---|
| `suggestions` | GET | No query | `{ items: Suggestion[] }` |
| `search` | GET | Query `q` and `type` | `{ items: Actor[] }`; each entry may be a summary |
| `actor` | GET | Encoded actor ID substituted for `:id` in the configured path | `{ actor: Actor }` |
| `export` | GET | `:id` in path; query `format=csv` or `format=json` | The actual file bytes |
| `session` | GET | Session cookie | `{ user: User }` or `{ user: null }` |
| `login` | POST | JSON `{ username, password }` | `{ user: User }`, with server setting the session cookie |
| `logout` | POST | Session cookie; CSRF header if required | HTTP 204 or JSON success; server invalidates session |

Paths should start with `/`. For the default requests, include `:id` in the actor and export paths. If your backend accepts IDs in the body or query instead, adjust the corresponding `backendCalls` function in `BACKEND_CONNECT.js`. The backend teammate supplies the actual paths; the frontend does not guess them. Query values and path IDs are URL-encoded.

`baseUrl: ''` uses the frontend's origin. The included local server **does not proxy backend requests**. During development, use the real backend origin in `baseUrl`, or arrange a same-origin reverse proxy separately. The backend must allow the frontend origin, normally `http://localhost:5500`, when the two run on different origins. The frontend uses `credentials: 'include'` for a cookie session; credentialed CORS needs an explicit allowed origin. Do not use `mode: 'no-cors'` to hide configuration errors.

All JSON endpoints should return `Content-Type: application/json`. Unauthorized and forbidden requests should return HTTP 401 and 403 respectively. A malformed payload is an integration error; it is not treated as an empty result.

## Canonical types

These are type descriptions, not sample records. The project itself uses JavaScript; this notation documents the expected fields.

```ts
type IdentifierType = 'all' | 'handle' | 'wallet' | 'key';
type Suggestion = {
  label: string; // Human-readable option label from actual data
  value: string; // Actual identifier to put in the search input
  type?: IdentifierType;
};

type User = {
  id: string | number;
  name?: string | null;
  role?: string | null;
};

type Actor = {
  id: string | number;            // Required stable identifier
  handle?: string | null;
  description?: string | null;
  priority?: string | null;       // Displayed as review status, not inferred by UI
  confidence?: number | null;     // 0–100; backend supplied
  firstSeen?: string | null;      // ISO 8601 with timezone
  lastSeen?: string | null;       // ISO 8601 with timezone
  aliases?: Alias[] | null;
  keys?: SigningKey[] | null;
  wallets?: Wallet[] | null;
  evidence?: Evidence[] | null;
  sources?: Source[] | null;
  events?: ActivityEvent[] | null;
  graph?: Graph | null;
};

type Alias = {
  id: string | number;
  handle?: string | null;
  detail?: string | null;
  confidence?: number | null;
  nodeId?: string | number | null; // ID of the matching graph node
};

type RecordBase = {
  id: string | number;
  title?: string | null;
  detail?: string | null;
  source?: string | null;
  date?: string | null;           // Observation timestamp, ISO 8601 with timezone
  confidence?: number | null;
  nodeId?: string | number | null;
  url?: string | null;            // Actual source URL, if available
};
type SigningKey = RecordBase & { value?: string | null; algorithm?: string | null };
type Wallet = RecordBase & { value?: string | null; network?: string | null };
type Evidence = RecordBase & { method?: string | null };
type Source = RecordBase & { name?: string | null; observedAt?: string | null };
type ActivityEvent = RecordBase & { label?: string | null };

type Graph = { nodes: GraphNode[]; edges: GraphEdge[] };
type GraphNode = {
  id: string | number;            // Unique within graph
  name?: string | null;
  type: 'actor' | 'alias' | 'key' | 'wallet' | 'source';
  identifier?: string | null;
  relation?: string | null;
  detail?: string | null;
  confidence?: number | null;
  observedAt?: string | null;     // Needed for historical snapshots
  recordId?: string | number | null; // Corresponding alias/key/wallet/source ID
  position?: [number, number, number] | null; // Optional display coordinates
};
type GraphEdge = {
  id: string | number;            // Unique, required even for parallel edges
  from: string | number;          // Existing node ID
  to: string | number;            // Existing node ID
  kind?: string | null;
  confidence?: number | null;
  observedAt?: string | null;
};
```

Provide graph edges from the account toward the related alias/key/wallet/source where possible. Clicking an edge selects its `to` node's chapter and displays the exact edge record first. `recordId` on the node or `nodeId` on the record connects the graph selection to its matching card. IDs are safely encoded in routes; slashes and punctuation are supported.

Graph positions are optional. The renderer computes a visual layout for **only the returned nodes** if positions are absent or outside its coordinate range (−300 to 300 per axis). This is visual placement, not relationship inference. It never constructs extra edges.

## Missing, empty, loading and errors

| Input or condition | UI meaning |
|---|---|
| Endpoint is `null` | Connection pending; no request is made |
| Field omitted or `null` | Connection pending |
| Actual empty array `[]` | Connected section with no returned entries |
| Numeric confidence `0` | Actual 0% (not a pending value) |
| Numeric confidence outside 0–100, a string, or absent | Connection pending; update mapping if your API uses another scale |
| Request in flight | Loading or the search buffering overlay |
| HTTP/network/timeout error | Visible error; no fallback records |
| Invalid response structure | Visible integration error; do not silently show success |
| Cancelled request | Ignore its response and stop the associated animation |

`mapActor()` preserves `null` versus `[]`. Search requires an `items` array and stable actor IDs. Every nested record needs a stable ID. Graph node/edge IDs must be unique, and every edge endpoint must refer to an existing node. Numeric IDs are normalized to strings so HTML controls and routes agree.

The detailed actor endpoint should return the same actor ID selected in search. A different ID is treated as an error. Search results can contain only basic actor fields; their absent sections remain pending until detail loads. If the detail endpoint is not yet configured, the UI retains only the real summary that search returned.

If your backend exposes graph, evidence and activity separately, add their real paths to `apiConfig.endpoints` and combine their responses inside `backendCalls.actor` in `BACKEND_CONNECT.js`. Keep missing sections null. Return the combined response in the shape selected by `responsePaths.actor`; the internal mapper handles the rest.

## Timeline and confidence

- Events are sorted by actual date; undated events remain at the end.
- Use full ISO timestamps with timezone. UI dates are shown in UTC.
- A historical graph snapshot uses the selected event's date, not a fixed list of fabricated steps.
- Undated graph records are omitted from historical snapshots because their existence at that moment is unknown; they remain visible in the latest graph.
- A positive confidence threshold hides unscored edges. Threshold 0 includes unscored edges without inventing a percentage.
- The frontend displays backend confidence. It does not compute identity attribution or certify any link.

## Authentication and exports

- The frontend is a static browser application. Every protected backend endpoint must authenticate the personnel session and authorize record access.
- Personnel Login is the first screen. All workspace routes wait for a verified user from `session` or `login`. Unconfigured authentication stays pending. There is no client-side preview sign-in.
- A saved valid session opens Search automatically. A signed-out session may return a null user or HTTP 401. Other session errors show Retry connection.
- Configure session and login together. The server should set an appropriate secure session cookie. Add CSRF headers through `getRequestHeaders()` when required by the backend.
- Do not place database passwords, service secrets, private signing keys or permanent API tokens in client files. The browser can read frontend configuration.
- Logout only reports success after the backend response. It clears selected account and result data from the interface.
- Exports must return actual bytes. Only CSV and JSON are offered; there is no report/PDF option and no generated placeholder file.
- Supply `Content-Disposition: attachment; filename="..."` and expose that header through CORS if the frontend needs the server's filename. The frontend otherwise derives a file name from the actual actor ID and the selected CSV/JSON format.

## Integration acceptance checks

Check these with authorized backend data after configuring the paths:

1. Suggestions populate Try; selection fills the correct identifier/type.
2. Search returns zero, one and multiple results correctly; sorting and picker work.
3. Cancelling or repeating a search never opens a stale popup.
4. Actor ID, aliases, keys, wallets, sources, evidence and dates match the response.
5. Every graph branch opens its related card; cards beyond the first six remain reachable.
6. Historical graph snapshots filter by observed timestamps.
7. Missing fields remain pending; actual empty collections show no entries.
8. Login, denied access, expired session and logout are handled by the real backend.
9. Exports download the server's actual files; backend permissions apply to exports too.
