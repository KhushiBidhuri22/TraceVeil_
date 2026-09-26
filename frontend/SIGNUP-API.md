# Connect personnel signup

This update adds the form, frontend API call, response mapping and login handoff.
The registration server/storage must be implemented by the backend team. No
accounts, endpoints or successful server responses are fabricated by the UI.

## One connection file

Open `frontend/BACKEND_CONNECT.js`, section **5 — Personnel signup**. Existing
base URL, login/session paths, headers and data mappings stay in that file.

1. Set `apiConfig.endpoints.signup` to your real POST endpoint. Replace the
   `null` in the section-5 assignment, or add `signup` to `endpoints` in section 1.
2. Adjust `backendCalls.signup` if your API uses different outgoing field names.
3. Set `responsePaths.signup` to the acknowledgement object. Use `''` when the
   entire response is the acknowledgement.
4. Match `fields.registration` to your response's names.

Section 5 uses `??=` so any existing, non-null signup settings take precedence.
All signup configuration lives in this file; no API URL belongs in the view.

## Default request

Method: **POST**. Body is JSON, with these fields:

| Field | Type | Meaning |
|---|---|---|
| `fullName` | string | Name entered by the user; trimmed |
| `email` | string | Email entered by the user; trimmed |
| `organization` | string | Optional organization, or an empty string |
| `password` | string | The entered password, preserved exactly |

Confirmation is checked in the form and is not sent. The browser requires a
name, valid email format, a password of at least 8 characters, and matching
confirmation. Align this client rule with the real server policy; the backend
must validate independently. The form sends no role or approval flag.

## Default response shape (type specification, not account data)

```typescript
type SignupResponse = {
  registration: {
    status: 'created' | 'pending_approval' | 'verification_required';
    message?: string;
    loginIdentifier?: string;
  };
};
```

Return a successful HTTP status and `Content-Type: application/json` only when
the real operation succeeds. The adapter requires one of the three explicit
statuses; a blank 204 response or unknown status cannot produce a success UI.
`loginIdentifier`, if supplied, fills the login username field; otherwise the
submitted email is used. `message` is rendered as text, never HTML.

| Registration status | UI behaviour |
|---|---|
| `created` | Open Login and ask the user to sign in |
| `pending_approval` | Open Login with the backend's pending-approval explanation |
| `verification_required` | Open Login with an email-verification explanation |

Signup does **not** create a frontend session, set `access.user`, or navigate to
Search. Keep login/session/logout configured with your existing auth service.
The backend decides authorization, approval and any email-verification policy.

## Errors and cancellation

- HTTP 409: explain that the account/details already exist and suggest Sign in.
- HTTP 400/422: ask the user to check the form and password requirements.
- Network/timeouts/malformed responses: remain on Signup with an inline error.
- Missing endpoint: Create account stays disabled with Connection pending in
  the form. There is no global status banner.
- A duplicate submit is blocked while a request is running. Leaving Signup
  cancels the pending client request and clears password inputs. Cancellation
  does not undo a request already processed by the server.
- Passwords are never saved to localStorage/sessionStorage or logged by the UI.

The backend should store password hashes, protect account creation appropriately
and enforce permissions on every protected API. CORS/cookies/CSRF must match the
existing authentication deployment. This frontend update does not invent a new
database or replace your server's authentication implementation.

## Check with your actual backend

Create an authorized test account, verify the acknowledgement, then sign in.
Also verify duplicate accounts, invalid input, an unavailable server, and a
signup request cancelled while navigating to Login. Check that directly opening
`#actor` while signed out still shows Login and exposes no account data.
