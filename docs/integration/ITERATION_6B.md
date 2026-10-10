# Iteration 6B — production integration (checkpoint; not yet complete)

Base: `ab7ef5d8b674ae2b89cc7796300e792b71030d8a`.
Branch: `feature/iteration-6b-production-deployment`.
Public service: https://sc6113-ay2026t1.onrender.com.

## Minimal database integration

Turso classic **libSQL-engine** database with official `libsql==0.1.11` Python
DB-API driver, directly connecting to the remote primary. No embedded replica,
local database synchronization, ORM, or backend rewrite. `backend/turso.py`
only adapts result rows and SQL errors to the existing application interface.
Native driver transactions retain commit/rollback and affected-row checks;
nonce consumption and indexing continue to use transaction blocks. SQLite SQL,
foreign keys, constraints, upserts and the accepted schema remain unchanged.

Absent Turso configuration in development/testing uses ordinary stdlib SQLite.
Production requires a remote `.turso.io` URL and token; it never silently falls
back to a local file. Additive initialization creates a clean remote schema;
**no local data is copied**. Turso is application-support storage for User Logs,
auth nonces, wallet metadata, server session records, indexed transactions/events,
and indexing progress. It is never the authority for financial state.

Official references inspected 2026-10-10:
- https://docs.turso.tech/sdk/python/reference
- https://docs.turso.tech/sdk/python/quickstart
- https://docs.turso.tech/cli/db/create
- https://turso.tech/pricing

The driver must match the database engine: `libsql` requires a classic libSQL
DB, not the new Turso-engine `--tursodb` option. Alternatives were rejected here:
`pyturso` synchronization introduces a local file and explicit sync;
`turso_serverless` targets the other engine. Current Free plan advertises 5 GB,
500 million monthly rows read, 10 million rows written, 100 databases and
one-day restore retention. Use **one free DB**, no paid upgrades. Free quotas and
short backup retention remain operational limitations. Real remote compatibility
must be confirmed at the hosted checkpoint; local native-driver tests are not
represented as remote-production proof.

## User Log

Visible Name / Save Name & Continue form, trimmed 1–120 characters, server UTC
timestamp, redirect to `/main`. `user(name,timestamp)` remains unchanged.
`/viewUser` renders Name/Timestamp columns; `/deleteUser` deletes **user only**.
This feature is independent of wallet login and roles. No passwords or profiles.

## Presentation caching

`sessionStorage` has a single explicit-allowlist snapshot scoped by authenticated
wallet, actual wallet chain, deployment ID supplied in HTML, and public session
presentation epoch (not an authentication token). It includes roles/pause/balances and page-specific read results, never
nonces, signatures, CSRF/auth tokens or credentials. Sessions are revalidated
with the backend on page load; cached UI is not authentication or authorization.
Unsigned preparation still verifies current authoritative contract preconditions.

First authenticated financial page reads verified account/funding state once.
Navigation reuses that state; dashboard-only history/list data are fetched only
when first needed and then cached. User Log pages do not trigger financial reads.
Identical concurrent GETs and eligibility reads share promises. Focus/visibility
only check session validity, never reload blockchain state for the same session.

A canonical successful receipt with at least six confirmations clears the
snapshot and performs **one shared fresh state load**, then refreshes needed
section/ID data against that snapshot. Claim/cancel show terminal states.
Rejected/failed transactions retain the snapshot. Manual Refresh, account,
network, session/wallet and deployment changes invalidate it. Explicit Refresh
remains necessary for external changes made by other wallets. Cached values are
presentation snapshots of earlier verified reads, never financial authority.
Accepted 6A participant-event association for MetaMask wrappers/batches remains
unchanged. The temporary loading flash is outside this work.

## Production configuration

Enter secrets directly in Render Environment, never in chat or the repository:

| Variable | Value / requirement |
|---|---|
| APP_ENV | production |
| FLASK_SECRET_KEY | Newly generated strong stable secret |
| AUTH_ORIGIN | https://sc6113-ay2026t1.onrender.com |
| TURSO_DATABASE_URL | The new free classic libSQL DB URL |
| TURSO_AUTH_TOKEN | DB-scoped token, stored only in Environment |
| BLOCKCHAIN_RPC_URL | Working Sepolia HTTPS RPC; credentials only in Environment |
| BLOCKCHAIN_CHAIN_ID | 11155111 |
| ROLE_REGISTRY_ADDRESS | 0x8E7A8Abf90cD4363F82489D14485Df7ACcaE4678 |
| FUNDING_CONTRACT_ADDRESS | 0x630863E58375Db128EFEfA51Ee369141cCbb839A |
| REMITTANCE_CONTRACT_ADDRESS | 0xA2Ee37DD717a8758Eb864788456d047b296C00E8 |
| BLOCKCHAIN_DEPLOYMENT_ID | sc6113-sepolia-11884239 |
| BLOCKCHAIN_MANIFEST_PATH | deployment/sepolia.json |

Production cookies remain Secure/HttpOnly/SameSite=Lax; HTTPS canonical origin
is required; wallet login remains single-use/expiring and fail-closed. Flask
never owns wallet keys. `.env.example` documents variable names only.

## Render rollback

Read-only service inspection confirmed existing free Singapore Python service,
`main`, build `pip install -r requirements.txt`, start `gunicorn app:app`, automatic
commit deploys. Previous live deploy `dep-db335vg473hc7388jfb0` used main commit
`92707ce35aa22246d6cfd5592e85b52f33ddb7bc`.
Non-secret rollback configuration: `docs/deployment/render-rollback.json`.
Owner must privately back up current Environment values before replacing them;
the connector does not expose environment backups or a branch-setting action.
Reuse this service, switch its branch to the 6B feature branch, retain build/start
commands. Restore main and previous environment values to roll back.

A temporary checkpoint commit is necessary to supply Render with buildable
GitHub source before hosted/manual verification; it is not the final approved
6B commit. Final commit follows evidence and regression completion.

## Verification commands

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py'
npm ci
npm run compile:contracts
npm run sanity:contracts
PYTHON=python node tests/local-chain.cjs
LOCAL_DB_DRIVER=libsql PYTHON=python node tests/local-chain.cjs
PYTHON=python CHROMIUM_EXECUTABLE_PATH=/path/to/chromium node --test tests/frontend.cjs
python -m pip check
git diff --check
```

Browser checks require Playwright and Chromium in the verification environment,
not in production dependencies. Test databases/wallets are isolated and no test
records are copied to runtime `user.db` or production.

## Hosted evidence — pending required checkpoints

At the original source checkpoint, Turso and Render setup were still pending.
Subsequent owner-reported hosted checks are recorded in the correction section below;
no credentials have been requested in chat.
Local regressions are recorded at the checkpoint, not claimed as hosted proof.

Still required, in order:
1. Free Turso classic libSQL DB and credentials entered directly in Render.
2. Previous Environment values privately preserved, feature branch deployed.
3. Hosted API/auth/remote compatibility and unchanged Sepolia reads verified.
4. Name insert/view, remote row confirmation, restart/redeploy survival,
   Delete All User Logs, and preservation of auth/indexing tables.
5. User-signed hosted authorization of Sender/Recipient, small deposit, one
   create and Recipient claim. Record receipts/IDs; do not repeat the other five
   transaction types or any contract deployment. Existing wallets reused.
6. Physical-phone MetaMask-browser checks, no duplicate writes needed.
7. Final regressions, scope/secret check, final commit/push without main merge.

Iteration 6A deployment and completed smoke-test evidence remain preserved in
`deployment/sepolia.json`, `deployment/live-smoke-evidence.json` and the 6A doc.
No new hosted lifecycle transaction or phone result is invented here.

## Local checkpoint regression results

- Python: **95 passed** (63 accepted tests plus 29 inherited tests exercised
  through the real libsql adapter and three additional persistence/User Log
  test methods). All use isolated databases; no remote proof is claimed.
- Browser: **48 passed** using Chromium and controlled wallet mocks; actual
  server nonce/signature/session verification remains in the browser flow.
- Solidity compile: solc **0.8.34**, all three compile, zero compiler warnings.
- Contract sanity: **10 groups**, **50 expected rejections**, all pass.
- Local-chain HTTP integration: both sqlite3 and libsql adapters each passed
  **8 assertions**, indexed **12 canonical events**, repeat indexing unchanged.
- `pip check` and `git diff --check` pass.
- Ganache reports a native µWS/Node ABI mismatch and successfully uses its
  JavaScript fallback; this is test-tool performance only.
- Phone emulation: 360, 768 and 1280 px checks pass; physical phone pending.
- Measured cache reads: initial dashboard = one account, one balance, one list,
  one history request; navigation through Funding/Remittance/User Log/back adds
  **zero** of those requests. Explicit Refresh adds exactly one of each.
  Funding-first load omits list/history until dashboard first needs them.
- Snapshot invalidation/session/deployment/network/account tests pass. Claim and
  cancel each refresh one account and one balance plus the selected terminal ID.
- Frozen contracts, ABI/build/deployment evidence, schema, and runtime user.db
  are unchanged. User.db SHA-256 remains
  `108de2caedd2c73374229f955de1e183387590b1031d05b242b03d386dbfe7cb`.
- Changed-file secret-pattern scan passes; `.env.example` values are empty.

These are pre-hosting checkpoint results. Hosted persistence/restart, hosted
MetaMask lifecycle and physical-device evidence are still required before the
final 6B commit/verdict. No final approval is implied by this checkpoint.

## Hosted index catch-up correction

Base checkpoint: `449d708d03b75bf2717eb7d4ac8053473df8235c`; same 6B branch.
Owner reports successful hosted Turso User Log insert/view, persistence across
Render redeploy, Delete All User Logs, and MetaMask Admin authentication. These
are owner-reported results, not new wallet transactions performed by Work.
The initial clean production index then timed out in synchronous receipt reads
on `/api/remittances`, producing HTTP 500 and a Gunicorn worker timeout.

The correction keeps the confirmed-log index and direct contract reads, with:
- A six-second indexing budget (hard configuration cap eight seconds), checked
  before and after RPC calls, and chunks capped at 25 blocks.
- A dedicated indexing-only HTTP provider: no retries/backoff, connect timeout
  at most 0.5 seconds and read timeout at most one second, reduced to fit the
  remaining budget. The authoritative reader transport is unchanged.
- Pass-local receipt/transaction caches: each unique transaction is fetched at
  most once. Ordinary block lookups are shared by height. Deliberate fresh
  end-of-chunk and verification-snapshot reads remain as reorg fences.
- Atomic writes of validated chunk events/transactions and their checkpoint;
  completed chunks survive budget exhaustion. Incomplete chunks never advance
  progress. A later request continues at checkpoint + 1.
- Normal budget exhaustion returns `caught_up: false`. RPC failures/timeouts
  return sanitized `BLOCKCHAIN_READER_UNAVAILABLE` / HTTP 503. If existing
  checkpoints could not be verified within the budget, return 503 rather than
  expose unchecked indexed evidence. Orphaned cache is still purged and replayed.
- Partial discovery is explicitly flagged. Financial remittance records still
  come from authoritative contract reads; no index completeness is assumed.

No Gunicorn timeout increase, background worker, queue, schema change, new
credentials, Solidity/deployment changes, or frontend production changes.
Cross-page caching and explicit Refresh behavior remain intact. Existing safe
chunks may remain committed when a subsequent chunk fails validation; the next
pass verifies all checkpoints and purges/replays on reorg. The adjusted rollback
test asserts that the inconsistent contract chunk has no checkpoint/events,
while earlier independently validated chunks retain safe progress.

Focused regressions cover clean index, partial progress/continuation, eventual
completion/idempotence, duplicate logs sharing RPC calls, slow receipts, normal
partial HTTP 200, structured 503, direct reads independent of catch-up, and a
real delayed HTTP receipt response that returns 503 in under one second with
exactly one receipt request. A browser test wait was stabilized for an already
pending session-only focus check; it still asserts exactly one state reload.

Correction regression results: **104 Python tests**, **48 browser tests**,
local-chain integration with sqlite3 and libsql (**8 assertions and 12 canonical
events per driver**, repeat indexing unchanged), and `git diff --check`.
Hosted lifecycle transactions remain paused; no MetaMask transaction, schema
change, secret change, smart-contract redeployment, main merge, or Iteration 7.
This remains a checkpoint correction, not final Iteration 6B approval.

## Second hosted checkpoint correction: authoritative remittance discovery

Base: `b5f3332bb933f637cdbbc1d047a68dff6bb741df`, on the same 6B branch.
The owner reported hosted account, balance and history HTTP 200 responses but
remittance-list HTTP 503 while the clean/partial Turso index caught up.

`GET /api/remittances` now discovers directly from the verified reader's
`remittanceCount`, scanning IDs newest-first through `reader.remittance(id)`.
The verified immutable Admin address permits all records; ordinary wallets see
only records naming them as sender or recipient, independently of current role
revocation. Offset/limit apply after filtering, and scanning stops when the page
is filled. Each financial record and reservation comes from the verified,
block-pinned contract reader with its existing snapshot/reorg checks. Responses
use `source: verified_contract`, `authoritative: true` and
`discovery: direct_contract_scan`. An empty index is not consulted, populated,
or required. A direct contract/RPC failure still fails closed with structured
503; index failure alone cannot block this endpoint.

The frontend labels direct contract discovery and its authoritative empty state.
It no longer describes remittance discovery as partial indexed history. Existing
browser snapshots, cache invalidation and deduplication are unchanged.
`/api/transactions`, the bounded resumable indexer, its receipt/block validation,
atomic checkpoints and reorg semantics are unchanged. History remains
non-authoritative and best-effort, returning partial progress or `live_error`.
Earlier correction notes about index-dependent remittance discovery describe
the previous checkpoint and are superseded by this section.

Verification: 116 Python tests, including 12 new direct-discovery regressions
(empty index, failing index, participant/Admin filtering, ordering, filtered
pagination, direct financial reads, zero count, structured reader failure and
unchanged history indexing). Browser regressions: 48 full-suite checks plus one new focused check (49 passed),
cover existing navigation/cache,
authentication and transaction refresh behavior plus direct discovery wording.
Local-chain checks run with both sqlite3 and libsql: 10 assertions and 12
canonical events per driver; completed/cancelled remittances are listed before
index initialization, and repeat indexing remains idempotent.

Direct scanning is intentionally suitable for the current small coursework
remittance count; it is not a high-volume search architecture. Hosted
post-deploy authenticated recheck remains an owner checkpoint. No additional
MetaMask writes are required or performed for this correction. No Solidity,
Turso schema, secret, contract deployment, Render configuration, main merge,
or Iteration 7 change is included.
