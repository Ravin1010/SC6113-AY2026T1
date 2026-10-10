# Iteration 4 — Backend / REST API / Database

Base: accepted Iteration 3 commit `313a82a8514624efd9351f3d45180447ae6b966d`.
Branch: `feature/iteration-4-backend-api-db`. No merge, deployment or frontend integration.

## Starting point and preservation

The original Flask routes are `/`, `/main`, `/depositMoney`, `/transferMoney`,
`/viewUser` (GET/POST) and `/deleteUser` (POST). `/main` records a supplied name;
view/delete act on the classroom `user(name text, timestamp timestamp)` table.
The baseline used a fresh `sqlite3.connect('user.db')` per operation with a relative,
hardcoded path. Python dependencies were Flask and gunicorn.

`create_app()` adds configuration and testability; `app` remains available for
`gunicorn app:app`. Legacy paths, endpoint names, templates and log operations are
preserved. The default database is the same repository `user.db`, now located
relative to `app.py` rather than the shell working directory. `DATABASE_PATH` can
override it. Connections are request-local, use parameterized SQL, enable foreign
keys and close at teardown. No ORM or migration framework is added.

Importing the app does not open or modify the database. Initialization is additive
and idempotent on first database use, or explicitly with `flask --app app init-db`.
The committed classroom database is unchanged; tests use temporary databases.

## Authentication and sessions

1. POST a wallet to `/api/auth/nonce`. A cryptographically random 32-byte nonce is
   stored with wallet, the hash of a browser-attempt token, exact signed message,
   issue/expiry times and consumption time. Default expiry is five minutes.
2. The response supplies the exact message to sign with MetaMask `personal_sign`.
   This is EIP-191 signed-message authentication, not a blockchain transaction or
   a claim of full EIP-4361/SIWE conformance.
3. POST wallet, nonce and 65-byte signature to `/api/auth/verify`. Optional `message`
   must equal the stored message. `eth-account==0.13.7` performs recovery using
   `encode_defunct`; no cryptographic recovery is implemented manually.
4. Verify wallet syntax/checksum, nonce ownership, originating browser attempt,
   expiry, single-use state and recovered signer. Conditional nonce consumption,
   wallet metadata and server-session insertion occur in one SQLite transaction.
   Concurrent attempts can produce only one successful login.
5. Rotate the Flask session and issue a random opaque session token. Its hash,
   wallet, expiry and revocation are server-side in `auth_sessions`. Flask's signed
   cookie carries the token; it is not encrypted and carries no private key.
   All protected requests validate this database record. Default lifetime is one
   hour; logout revokes it, so replaying a pre-logout cookie fails.

Exact message structure (values supplied by server):

```text
SC6113 Cross-Border Remittance DApp wallet login
Application origin: <AUTH_ORIGIN>
Wallet: <checksummed address>
Nonce: <random nonce>
Issued at: <UTC ISO timestamp>
Expires at: <UTC ISO timestamp>
This signature authenticates a session only; it authorizes no blockchain transaction.
```

Only the latest requested nonce in a browser is eligible for verification. Expired
or failed challenges never establish a session. Failed signatures do not consume
an otherwise valid nonce. Ten outstanding unexpired challenges per wallet limit
trivial repeated requests; general deployment rate limiting and record retention
remain later hardening work.

Cookies are HttpOnly and SameSite=Lax. Production enables Secure cookies and requires
`APP_ENV=production`, an externally supplied high-entropy `FLASK_SECRET_KEY`, and
explicit canonical HTTPS `AUTH_ORIGIN` (scheme + host + optional port, no trailing
slash/path). Development defaults to localhost and an ephemeral random secret;
set a shared secret for multiple workers or sessions will not survive process
changes. Never commit secrets. No private keys are accepted or stored.

API POSTs require JSON, reject mismatched Origin when present and have no permissive
CORS. Logout additionally requires `X-CSRF-Token` from login/session response. Login
is bound to the browser challenge cookie. API bodies are limited to 16 KiB.
Legacy classroom form routes retain their original access behavior; they do not
grant API authentication or blockchain roles.

## API endpoints

All replies are JSON; errors have `error.code`, `error.message` and optional details.
Protected endpoints return 401 `AUTH_REQUIRED` without a valid server-validated session.
Responses use `Cache-Control: no-store`.

| Method / route | Authentication | Responsibility / current response |
|---|---|---|
| POST `/api/auth/nonce` | Public, browser-bound challenge | `{wallet}` -> 201 nonce, exact message, issue/expiry |
| POST `/api/auth/verify` | Challenge cookie + wallet signature | `{wallet,nonce,signature,message?}` -> 200 wallet session + CSRF token |
| GET `/api/auth/session` | Session | 200 authenticated wallet + CSRF token |
| POST `/api/auth/logout` | Session + CSRF header | `{}` -> 200 authenticated=false; revoke session |
| GET `/api/users/me` | Session | 200 wallet/application metadata; roles explicitly unavailable |
| GET `/api/users/me/balances` | Session | 503 blockchain boundary; no invented balances |
| GET `/api/remittances` | Session | Validate pagination; 503 blockchain boundary |
| GET `/api/remittances/<id>` | Session | Validate positive uint256 ID; 503 blockchain boundary |
| GET `/api/transactions` | Session | 200 wallet-scoped cached index only, with provenance flags |
| GET `/api/transactions/<hash>/receipt` | Session | Validate 32-byte hash; 503 blockchain boundary |
| GET `/api/transactions/audit` | Session; future on-chain Admin check | 503; no locally inferred Admin role |

List routes support `limit` (1–100, default 50) and `offset` (0–1,000,000, default 0).
Unexpected/repeated query fields are rejected. Authentication inputs reject missing,
unexpected and malformed JSON fields. Important errors: 400 input/signature errors,
401 signer/attempt mismatch, 403 origin/CSRF rejection, 409 nonce replay or concurrent
consumption, 410 expiry, 413 excessive body, 415 non-JSON, 429 outstanding challenge
limit and 503 storage/blockchain unavailable. There are no remittance or role write
APIs and no backend-signed blockchain transactions.

`/api/transactions` reports `source=sqlite_index`, `authoritative=false`,
`live_blockchain_checked=false`, `indexing_available=false` and
`scope=authenticated_wallet`. Without a deployment identifier it returns no indexed
items. With an identifier, it restricts records to Sepolia, that deployment and the
logged-in wallet as sender or recipient. Empty cached items are not confirmed empty
blockchain history. No runtime indexer or browser cache-insert endpoint exists yet.

## Additive SQLite schema and authority

| Table | Purpose and constraints |
|---|---|
| `user` (preserved) | Existing name/timestamp columns and records; never dropped or rebuilt |
| `auth_nonces` | Nonce primary key; wallet/expiry index; expiry must exceed creation |
| `app_wallets` | Canonical lowercase wallet primary key; created/last-login times; no roles |
| `auth_sessions` | Hashed token primary key; wallet foreign key; expiry/revocation |
| `indexed_transactions` | Composite key chain/deployment/hash; nullable observed receipt/block fields; wallet index |
| `indexed_events` | Composite key chain/deployment/hash/log index; foreign key to transaction; block/event/payload and optional remittance ID |
| `indexing_state` | Composite key chain/deployment/contract; last indexed block/hash/time |

Block/log positions have nonnegative constraints; receipt status, when present, is
0 or 1. Remittance ID is TEXT to preserve uint256 values outside SQLite integer
range. Only a later verified blockchain indexer may populate the three index tables.
No standalone remittance cache is needed now; indexed events supply its future
starting point. No sample receipts, balances or remittances are seeded.

SQLite owns application-support records and authentication sessions only. Blockchain
remains authoritative for roles, pause state, available/reserved funds, participants,
amounts and remittance status. Cached receipts/events must be reconciled against
verified blockchain data and handled for reorgs in later integration.

## Undeployed blockchain configuration boundary

Future environment hooks:

- `BLOCKCHAIN_RPC_URL`
- `BLOCKCHAIN_CHAIN_ID` (Sepolia `11155111`; only nonempty default)
- `ROLE_REGISTRY_ADDRESS`
- `FUNDING_CONTRACT_ADDRESS`
- `REMITTANCE_CONTRACT_ADDRESS`
- `BLOCKCHAIN_DEPLOYMENT_ID` (unique identifier for the verified contract set)

Addresses default to empty. Validate complete configuration, Sepolia chain,
HTTP(S) RPC URL and nonzero distinct Ethereum addresses. Both historical classroom
addresses are explicitly rejected, never substituted. Missing/invalid configuration
returns HTTP 503:

```json
{"error":{"code":"BLOCKCHAIN_NOT_CONFIGURED","message":"Verified evolved Sepolia deployment configuration is incomplete or invalid.","details":{"configured":false,"missing":["..."],"invalid":[],"deployment_verified":false,"reader_available":false}}}
```

Even complete syntactically valid configuration returns
`BLOCKCHAIN_DEPLOYMENT_UNVERIFIED` until independently verified. Verification is
false by default and cannot be asserted through an API or environment flag.
If marked verified programmatically in future integration, this iteration still
returns `BLOCKCHAIN_READER_UNAVAILABLE`: no live reader has been implemented.
No RPC calls are made here. Iteration 6 must supply verified deployments and actual
read integration. Flask never takes custody of private keys; all ten financial/
role transactions remain MetaMask-signed user/Admin actions.

## Future durable persistence selection

Official documentation reviewed 2026-10-10. **Select Turso Cloud free hosted libSQL
(SQLite-compatible) remote-primary persistence for later deployed use.** Keep local
standard-library SQLite for development/tests and Render for application hosting.
The current Render free service's local filesystem must not be treated as durable.
The application is NOT integrated with Turso in this iteration.

| Option | Free allowance and fit | Assessment |
|---|---|---|
| Turso Cloud | $0/no credit card; 100 databases, 5 GB storage, 500M rows read/month, 10M written/month, 3 GB sync/month; one-day point-in-time recovery. SQLite fork/compatible Python remote client. | Selected: direct remote SQLite-oriented access offers the simpler path from this Flask application. |
| Cloudflare D1 | SQLite SQL semantics; 10 free databases, 500 MB each, 5 GB total; 5M reads/day, 100k writes/day, seven-day Time Travel. HTTP API access. | Credible alternative; adapting HTTP responses/transaction semantics for this Render Python application adds work (architecture assessment). |

Turso documents durable remote commits independent of compute/local disk lifetime.
Its current Python documentation distinguishes `libsql` for remote libSQL from
`turso_serverless` for its newer engine. Use the driver matching the provisioned
engine later; do not mistake embedded/local sync persistence for a durable Render
filesystem. libSQL serializes writes; test concurrency and retries for this small
coursework workload. No SDK is installed now. Compatibility is a documented
candidate, not a tested drop-in connection change: verify schema, foreign keys,
row factory, execute-script initialization, transactions, conditional update
rowcounts and simultaneous nonce consumption before replacing connections.

Remain on the free plan, do not enable paid upgrades/overages, and monitor usage;
quotas/recovery windows are finite and must be rechecked before provisioning.
D1 queries fail when daily free read/write quotas are exhausted until reset.
Expected small coursework usage fits these published allowances; this is an
estimate rather than measured production usage. Later work includes provision,
credentials outside git, data migration, compatibility/atomicity tests and
restart/redeploy persistence checks. No account, database or credentials were
created; no provider integration, data migration or Render change occurred.

Official sources:

- [Turso pricing](https://turso.tech/pricing)
- [Turso durability](https://docs.turso.tech/cloud/durability)
- [Turso SDK selection / SQLite compatibility](https://docs.turso.tech/sdk/introduction)
- [Turso Python reference](https://docs.turso.tech/sdk/python/reference)
- [Cloudflare D1 overview](https://developers.cloudflare.com/d1/)
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/)
- [D1 limits](https://developers.cloudflare.com/d1/platform/limits/)

## Focused tests and local commands

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

Tests use Python `unittest`, Flask's test client, generated Ethereum wallets and
isolated temporary databases. No MetaMask, RPC, deployed contract, runtime user.db
or remote service is needed. Coverage includes signatures, wallet/browser binding,
expiry, sequential/concurrent replay, logout/revoked cookies, invalid input,
unauthenticated requests, preserved schema/log behavior, idempotent initialization,
reopened storage, uniqueness/foreign keys, cache scoping and fail-closed deployment
configuration. This is backend verification, not full blockchain/E2E/gas testing.

Run locally with `python app.py` after installing requirements; database defaults
to the classroom file. Prefer `DATABASE_PATH` pointing to a disposable/local copy
while experimenting. The frontend has not been connected to these new APIs.

## Remaining work

Later phases must integrate frontend wallet login/API calls, implement verified
blockchain reads and indexing/reorg reconciliation, check on-chain Admin access
before live audit access, integrate/test free remote persistence, configure shared
production secrets/HTTPS, and set deployment retention/rate limits. Existing
classroom log viewing/deletion remain deliberately unchanged and should be assessed
when the evolved production UI/access rules are integrated. No Iteration 5 work
has been started here.
