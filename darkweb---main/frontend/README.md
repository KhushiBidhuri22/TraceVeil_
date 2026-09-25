# TraceVeil — frontend

This is the actual frontend source for your team's `darkweb-attribution/frontend/` folder. It preserves the approved glossy green/red design, animated background, search transition, popup dossier, graph beside the username, six account cards, and the book-opening card stack inside the ring. Glossy is now fixed, with no surface or pause-motion switches. Motion still respects the operating system’s reduced-motion setting. CSV and JSON are the only export formats.

There are **no sample accounts, usernames, wallets, keys, sources, scores or investigation records** in this package. Unconnected data fields say **Connection pending**.

## 1. Put the files in VS Code

1. Extract the downloaded ZIP.
2. Open the extracted `frontend` folder.
3. Copy **its contents** into the `frontend` folder that already exists in your cloned `darkweb-attribution` repository.
4. The correct location is `darkweb-attribution/frontend/index.html`. Avoid an extra `frontend/frontend/` folder.
5. The existing `.gitkeep` can be deleted after adding these files. It only helped Git retain the previously empty folder; it contains no application code.
6. Keep working in your feature branch. These steps do not push anything to GitHub.

## 2. Run it

Install the current [Node.js LTS](https://nodejs.org/en/download) if it is not already installed. This package uses Node 24 or newer. Reopen VS Code after installation.

In VS Code, choose **Terminal → New Terminal**. If the terminal opens at your repository root, run:

```bash
cd frontend
node --version
npm run dev
```

If the terminal is already inside `frontend`, skip `cd frontend`.

Open **http://localhost:5500** in your browser. Keep that terminal running. Stop it with **Ctrl+C**.

- **No `npm install` is needed:** the local server uses Node's built-in modules, and the interface uses browser JavaScript.
- Save changes in VS Code and refresh the browser. This simple server does not implement automatic hot reload.
- If port 5500 is busy, run `npm run dev -- --port 5501` and open `http://localhost:5501`.
- If PowerShell blocks `npm.ps1`, run `npm.cmd run dev` or choose **Command Prompt** as the VS Code terminal. There is no need to change the machine's execution policy.
- Opening `index.html` by double-clicking is insufficient: JavaScript modules should be served through the local URL.
- The original Google Fonts remain in `index.html`; they need internet. If they cannot load, the interface uses its monospace fallbacks. The segmented percentage font is bundled locally in `css/fonts/traceveil-segment.woff` and does not need internet or installation.

## 3. What you will see before backend integration

| Place | Initial behavior |
|---|---|
| First page | Personnel login with the glossy animated background. Unconnected sign-in shows **Connection pending**. |
| Search page | Opens after the server confirms a personnel session. No account is prefilled. |
| **Try** dropdown | Shows **Connection pending**, disabled until suggestions arrive from the backend. |
| Search action | Runs the visible transition, then shows a pending dossier when the search endpoint is unconfigured. It never invents a successful match. |
| Actor workspace | All data fields remain pending. The six record-category cards remain clickable. |
| Graph | Shows **Connection pending**; no invented graph nodes or connections. |
| Detail screen | The centre card stack and ring interaction work; unconnected fields remain pending. |
| Personnel access | First screen; sign-in stays disabled until session and login endpoints are configured. A saved, valid server session opens Search automatically. |
| Export (CSV / JSON) | Disabled with **Connection pending** until there is an actual selected actor and export endpoint. |

Connect authentication first to enter the workspace. Pending search/actor/detail sections remain available after a verified session, while their respective endpoints are still unconnected. Direct hashes such as `#actor` cannot skip the login screen. The background is decorative geometry; it does not represent collected data.

## 4. File map — what goes where

**For backend integration, open `BACKEND_CONNECT.js` in the frontend root.** The files inside `js/services/` are internal helpers. Their settings now come from that one file. Read `BACKEND-START-HERE.md` for the short handoff.


| File | Responsibility |
|---|---|
| `BACKEND_CONNECT.js` | **Backend teammate: edit here.** Server origin, API paths, response paths, field names and request formats. |
| `BACKEND-START-HERE.md` | Short guide for connecting the backend. |
| `index.html` | Login and the three workspace screen structures, forms, dialogs and stylesheet/script links. |
| `package.json` | Defines the `npm run dev` command. No external dependencies. |
| `dev-server.mjs` | Serves this frontend locally. It is not the backend. |
| `css/base.css` | Layout, spacing, typography, inputs, account cards and responsive rules. |
| `css/finishes.css` | Fixed glossy surface treatment. |
| `css/interactions.css` | Glitch overlay, dossier, and detail interaction styling. |
| `css/orbit-book.css` | Circular record selector, 3D book hinge, card stack and enhanced gloss. |
| `css/connections.css` | Pending, loading and disabled states, Try dropdown and access form. |
| `css/access.css` | Responsive glossy personnel login screen. |
| `css/numbers.css` | Shared segmented percentage typography. |
| `css/fonts/traceveil-segment.woff` | Local numeric font; copy this binary from the ZIP. |
| `js/app.js` | Starts the app; coordinates selected actor, navigation, verified-session gate, motion preference and views. |
| `js/config/api.js` | Internal bridge to the settings in `BACKEND_CONNECT.js`. |
| `js/services/http.js` | The one shared `fetch()` wrapper: timeout, cancellation, cookies, HTTP errors. |
| `js/services/traceveil-api.js` | Internal service runner; reads request functions from `BACKEND_CONNECT.js`. |
| `js/services/mappers.js` | Internal validation and normalization; reads field mappings from `BACKEND_CONNECT.js`. |
| `js/views/search.js` | Try dropdown, search submission, sorting and the detailed result popup. |
| `js/views/actor.js` | Account summary, six record cards, graph controls and filters. |
| `js/views/detail.js` | Selects a detail chapter and hands it to the book/ring component. |
| `js/views/access.js` | Personnel sign-in and sign-out UI using the backend session. |
| `js/views/exports.js` | Requests and downloads actual files from the backend. |
| `js/components/background.js` | Shared 3D green particle ribbons and dot field. |
| `js/components/network.js` | Draws actual graph nodes/edges and handles wheel rotation and clicking. |
| `js/components/record-explorer.js` | Ring selection, centre stack, book opening and timeline playback. |
| `js/components/search-transition.js` | Search animation timing and cancellation. |
| `js/components/dialogs.js` | Opening and closing dialogs with focus-aware native modal behavior. |
| `js/models/workspace.js` | Six record categories, icons and branch-to-detail navigation. |
| `js/models/graph.js` | Positions actual nodes and applies graph/time/confidence filters. |
| `js/models/record-pages.js` | Turns actual account fields into the individual book pages. |
| `js/utils/display.js` | Shared safe text, dates, percentages, links and pending-state formatting. |
| `API-CONTRACT.md` | The full handoff document for the backend teammate. |

All paths in this table are relative to `frontend/`.

## 5. How the code works — the simple version

**HTML decides where an element exists. CSS decides how it looks. JavaScript decides what happens when you interact with it.**

Example: the search input in `index.html` has `id="query"`. In `js/views/search.js`, `document.querySelector('#query')` finds that input. Its `.value` is what the user typed.

Before searching, `access.js` checks `api.session()`. Without a verified user it shows Login. `api.login()` sends the credentials; a successful response opens Search. Logout clears the account and returns to Login. These requests are all configured in `BACKEND_CONNECT.js`.

The complete search flow is:

1. `search.js` reads the identifier and identifier type.
2. It starts the glitch/buffering overlay and asks `api.search()` for results.
3. `traceveil-api.js` calls the shared `request()` function in `http.js`.
4. `http.js` reads the endpoint settings from `BACKEND_CONNECT.js` through the config bridge and makes the request.
5. `mappers.js` reads your field-name settings in `BACKEND_CONNECT.js` and translates the response into the frontend's model.
6. The search view waits for both the response and the short visual transition before opening the popup. A slow request keeps the overlay open until a response, cancellation or timeout.
7. Selecting a real result loads the actor detail endpoint and updates the overview, graph, cards and book pages.

The **Try** dropdown follows a smaller flow: suggestions API → mapper → dropdown options. Choosing an option fills the input and identifier type. The user still clicks **Search**.

The word `import` at the top of a JavaScript file means “use a function or class from another file.” `export` means “make this function or class available to other files.” That is how the modules connect without one enormous script.

`null` means a field has not been supplied. It does **not** mean zero, false, an empty username, or a successful empty result. The formatter turns missing display values into **Connection pending**. An actual `[]` from a connected endpoint means the backend returned an empty collection.

`async` and `await` let the app wait for network work without freezing the interface. `AbortController` cancels work when a search or selected account changes, so an old response cannot replace a new selection.

## 6. Backend teammate: start here

1. Open `BACKEND-START-HERE.md` for the short handoff.
2. Open `BACKEND_CONNECT.js` in the frontend root.
3. Fill the actual server address and endpoint paths in section 1.
4. Match response paths and field names in sections 2 and 3, where they differ.
5. Adjust request methods/query/body in section 4 only if the API requires it.
6. Connect `session`, `login` and `logout` first. A missing auth connection deliberately keeps the first page pending.
7. Leave unfinished endpoints and fields unconnected; they remain pending.

The longer `API-CONTRACT.md` lists supported fields and behavior. Common integration edits now stay in `BACKEND_CONNECT.js`. Even if actor data comes from several endpoints, they can be combined in that file's `backendCalls.actor` function.

The default config makes no API requests. The frontend has no embedded credentials, token, backend URL or dataset. Login and data authorization must be implemented and enforced by the backend. The provided access form expects a cookie-based session unless your team adapts the shared HTTP layer.

## 7. Checks and remaining integration work

This handoff is frontend code with connection hooks, not a connected investigation service. Backend URLs and payloads have not been provided yet. Full login/search/export behavior must be checked against your team's real services after integration.

The source is checked for JavaScript syntax, local imports and assets, absence of prototype records, pending-state behavior, cancellation, response mapping, graph filtering, detail routing and the local static-file handler. The UI update is additionally checked with controlled DOM tests for login behavior, removed controls and export restrictions. Browser visual QA could not run in this workspace; review the layout after applying the update locally. The team’s real backend is still required for end-to-end integration validation.

For a very large actor graph, a backend query should bound the returned graph or the team should add graph pagination/clustering. The renderer displays the actual returned nodes; it does not fabricate a smaller graph. Detail cards are reachable through groups of up to six ring branches and Previous/Next controls.

## Percentage styling

`percentMarkup(value)` in `js/utils/display.js` wraps a supplied number in `.technical-percent`. The shared CSS applies the local segmented font in search dossiers, evidence cards and the centre book. Missing scores still show **Connection pending** in the normal font. Use the same helper if a real analysis-progress endpoint is added later. The search buffer stays indeterminate until an actual progress value is available.
