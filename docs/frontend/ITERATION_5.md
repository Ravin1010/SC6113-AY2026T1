# Iteration 5 — Mobile-friendly frontend integration

Base: `67df196859bb0e2f392aa24167e7283bf38589df` (accepted Iteration 4).
Branch: `feature/iteration-5-frontend-dashboard`.

## Baseline and reuse

The baseline used independent classroom HTML pages, a narrow centered CSS container,
and inline Web3.js 1.5.2 scripts on funding/transfer pages. Those scripts called the
two historical record-only contracts, accepted caller-supplied participant values,
and displayed their last stored record. Their addresses and inline execution have
been removed completely from active templates/static files. No evolved deployment
address, ABI, balance, remittance or transaction hash is supplied by this frontend.

Retain all six original routes and classroom name-log operations. Restyle the pages
through a shared Jinja base and responsive CSS. `/main` is the central dashboard;
`/depositMoney` and `/transferMoney` are supporting forms. `/` primarily links to the
dashboard, with optional classroom name entry in a secondary disclosure. `/viewUser`
still exposes classroom records and deletion; `/deleteUser` still confirms deletion.
No Flask, API, database, dependency or Solidity change was required.

## UI structure

- `base.html`: document/viewport, skip link, shared header, navigation, login panel,
  status messages and test-asset/fiat-settlement boundary.
- `main.html`: session-aware account, deployment, funding, remittance, cached activity
  and Admin sections. Protected dashboard content is hidden until session verification.
- `forms.html`: shared funding/remittance/Admin input macros. Every blockchain action
  is rendered with native `disabled`, regardless of session or backend response.
- `api.js`: same-origin JSON requests, 12-second network timeout, structured errors
  and concise deployment-state messages.
- `auth.js`: injected wallet access, message signing, session reads/logout, account
  consistency and wallet-network display.
- `forms.js`: preview-only address/positive amount/uint256 ID checks; never sends a
  transaction or posts an action form.
- `app.js`: session/dashboard rendering, history, navigation and wallet change events.

No frontend framework, CDN dependency or build pipeline is introduced. The classroom
Web3 CDN is unnecessary for login and has been removed; native wallet APIs suffice.

## Wallet authentication

User click -> `eth_requestAccounts` -> POST `/api/auth/nonce` -> `personal_sign` ->
POST `/api/auth/verify` -> backend-validated session -> account/history reads.
`personal_sign` receives a hex encoding of the exact server-issued UTF-8 message,
followed by the selected wallet address. Signatures are transient local variables;
no signature/session credential is persisted in localStorage or sessionStorage.
Private keys are never requested. The accepted Flask cookie/session architecture
remains unchanged; a wallet connection is not treated as authentication.

Check selected account before and after verification. Account-change events clear
the current UI and revoke the known old session; pending login generations cannot
render obsolete wallet data. Authenticated and connected wallet identities are
shown separately, with a warning on mismatch. The wallet chain is read for display;
login does not require a blockchain transaction or silently switch networks.

Restore the session after navigation/reload; refresh on tab return/focus. Logout uses
the session CSRF token and only reports success after the backend confirms it.
Session expiry returns to login and clears displayed history. Handle absent provider,
connection/signature rejection, wallet mismatch, expired/replayed challenge, backend
errors and network failures. For mobile injected-wallet access, the login panel
instructs users to open the site in MetaMask's in-app browser; ordinary mobile Safari/
Chrome without an injected provider cannot sign in. WalletConnect is not added.

## Undeployed blockchain boundary

| Backend code | Display |
|---|---|
| `BLOCKCHAIN_NOT_CONFIGURED` | Deployment not configured; available after verified Sepolia deployment |
| `BLOCKCHAIN_DEPLOYMENT_UNVERIFIED` | Verification pending; actions unavailable |
| `BLOCKCHAIN_READER_UNAVAILABLE` | Live reads not available; actions unavailable |

The deployment detail disclosure preserves the error code and missing/invalid
configuration field names. Roles, balances and remittance statuses are explicitly
unavailable. No Sender/Recipient/Admin permission is inferred from login or SQLite.

Deposit, withdraw, create, claim, cancel, authorize Sender, authorize Recipient,
revoke, pause and unpause are all disabled. No wallet transaction method or backend
blockchain-write request exists in the frontend. This remains true even if a future
API unexpectedly reports configured deployment/roles. Enabling writes is later work.

Input checking is a preview only: valid nonzero address format, distinct recipient
when the session wallet is known, positive test ETH with at most 18 decimals and
positive uint256 ID. It does not prove checksum, authorization, available funds or
remittance eligibility. Contract/backend validation remains authoritative.

## Activity provenance

Authenticated dashboard calls GET `/api/transactions?limit=10&offset=…`.
Only returned cache records are shown. Require the accepted provenance fields:
`source=sqlite_index`, `authoritative=false`, `live_blockchain_checked=false`.
History uses cards and DOM textContent; returned values cannot inject HTML.
Show cached receipt/block/deployment metadata, never pretend it is live financial
state. Empty cache says “No indexed transactions available yet,” explicitly noting
that this does not establish empty blockchain history. Pagination handles cache-only
pages; errors clear stale records and show an unavailable state. No indexing or
cache writes are implemented. Test fixtures exist only in temporary test storage.

## Responsive/accessibility approach

Mobile-first single-column cards, full-width action rows, 16px form text and at least
44px primary navigation/control targets. Long wallet addresses/hashes wrap. At 768px,
forms/cards can use two columns; at 1100px navigation becomes horizontal. Below that,
a Menu button opens stacked navigation with `aria-expanded`/`aria-controls`, closes
after selection and supports Escape/keyboard focus. There are no hover-only controls,
animations or fixed-height content containers. Disabled states, labels, focus rings,
live status regions and a skip link remain visible/accessible.

## Focused checks and reproduction

Backend regression:

```sh
python -m unittest discover -s tests -v
```

Browser test tooling is development-only. Install Playwright 1.62.1 separately if not
already available; it is not added as a production dependency or frontend build step:

```sh
npm install --no-save --package-lock=false playwright@1.62.1
npx playwright install chromium
PYTHON=.venv/bin/python node --test tests/frontend.cjs
```

A preinstalled browser can be used with `CHROMIUM_EXECUTABLE_PATH=/path/to/chromium`.
Optional `UI_SCREENSHOT_DIR` saves temporary screenshots into an existing directory.
The helper starts a local test-only Flask server with a temporary SQLite file and
generates ephemeral Ethereum wallets/signatures. No production/runtime database,
RPC, MetaMask extension or deployed contract is used. Deployment errors and populated
cache rendering use clearly controlled browser-response fixtures; real nonce/signature
verification, sessions, logout, expiry and empty-cache reads use accepted Flask APIs.

Result: **20/20 browser/integration tests**, **29/29 backend regression tests**.
Chromium 153.0.8010.0 via Playwright 1.62.1. Browser download from the normal Playwright
CDN was unavailable here; a temporary standalone Chromium package provided the test
executable, without adding it to project dependencies. Responsive checks cover `/`,
`/main`, `/depositMoney`, `/transferMoney`, `/viewUser` at 360/768/1280px, including
long identifiers, menu touch/keyboard interactions and input fitting. Dashboard
screenshots were visually inspected. No horizontal document overflow was found;
all blockchain controls stayed disabled and no transaction RPC method was requested.
Classroom log deletion confirmation was also checked. No browser exceptions occurred.

## Scope and later work

No Solidity, Flask/API/schema, runtime user.db, Render or Turso changes; no deployments,
main merge, formal report/slides/Drive edits or Iteration 6 work. Later verified
integration must supply actual role/balance/remittance reads, indexing and wallet-signed
transactions. Physical-device MetaMask and live Sepolia E2E checks remain later;
responsive viewport tests are not a claim of hardware-wallet/mobile E2E coverage.
Production auth origin/shared secrets and durable persistence remain accepted later
configuration work from Iteration 4.

References used for provider behavior:

- [MetaMask provider API](https://docs.metamask.io/metamask-connect/evm/reference/provider-api/)
- [MetaMask JSON-RPC API](https://docs.metamask.io/metamask-connect/evm/reference/json-rpc-api/)
