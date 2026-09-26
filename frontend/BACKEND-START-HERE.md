# Backend teammate: start here

**Open `frontend/BACKEND_CONNECT.js`. It contains all connection settings.**

The other files draw the pages, cards, graph and animations. They already receive data through this connection file. You do not need to attach an API separately to every card.

## What goes in that one file?

| Section | What you supply |
|---|---|
| **1 — Server** | Your actual backend origin and endpoint paths |
| **2 — Response** | Where each JSON response contains its results |
| **3 — Fields** | The backend's field names for the account, graph and records |
| **4 — Requests** | HTTP method, query or body changes, if your API differs |

The settings are initially unconnected. No API URLs or investigation records have been invented.

## Connect authentication first

The first screen is now Personnel Login. Configure `session`, `login` and `logout` in `BACKEND_CONNECT.js`. Set `responsePaths.session` and `responsePaths.login` to the user object, and match `fields.user` to its `id`, `name` and `role`. A signed-out session may return a null user or HTTP 401. Sign-in must return the actual user and establish the backend session.

Unconfigured authentication stays **Connection pending**. There is no preview account or fake login. A valid session opens Search; logout returns to Login.

## Then connect Search

1. Put your backend origin in `apiConfig.baseUrl`.
2. Set `apiConfig.endpoints.search` to its actual search route.
3. Look at one real search response. Set `responsePaths.search` to the path of its result array. Use `''` if the response itself is the array.
4. Match the account's field names in `fields.actor`. The left side is the frontend name; edit the right side to match your API.
5. Search from the running frontend. The real results should appear in the popup.

For example, **if** your API calls the username field `username`, the mapping is `handle: 'username'`. This describes a field name, not sample account data. Nested paths such as `profile.username` are supported. A function can be used when your backend requires an explicit value conversion.

## Then connect the remaining features

| Endpoint setting | Screen that receives its response |
|---|---|
| `suggestions` | Options in the **Try** dropdown |
| `actor` | Selected account, graph, evidence, sources and activity cards |
| `session`, `login`, `logout` | Authorized personnel access |
| `export` | Actual CSV / JSON downloads |

The actor response supplies the whole account workspace. If those sections come from separate APIs, combine their responses inside `backendCalls.actor` in the same file. Additional paths can be added to `apiConfig.endpoints`.

Leave an unfinished endpoint as `null`; its UI stays **Connection pending**. Leave absent data fields missing or null. An actual empty array means the server returned no entries.

## What we need from the backend

- Real endpoint paths and HTTP methods.
- A real response shape for search, account detail and suggestions.
- The session/authentication approach.

The backend must enforce personnel permissions. The frontend does not create secure access by itself. If frontend and backend use different origins, configure CORS on the backend for the frontend's origin; the provided local frontend server is not a proxy.

For the complete supported field list, see `API-CONTRACT.md`. Start with authentication, then Search; connect the other endpoints as they become available.
