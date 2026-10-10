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

No Turso account/database has been created or token requested in chat.
No Render settings have been changed; no 6B deployment has happened yet.
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
