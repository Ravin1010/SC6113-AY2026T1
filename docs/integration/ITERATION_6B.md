# Iteration 6B — production persistence, hosted verification and mobile UX: final freeze

Iterations 1–6A remain approved/frozen. This document consolidates Iteration 6B
only; it does not start Iteration 7. Frozen implementation head:
`f32ab933f5aa4cb51237a6468ad9a317c2ee2f79`.
Iteration 6A base: `ab7ef5d8b674ae2b89cc7796300e792b71030d8a`.
Branch: `feature/iteration-6b-production-deployment`; no merge to `main`.
The final consolidation commit changes documentation only.

## Evidence and authority boundaries

| Kind | Meaning |
|---|---|
| Authoritative blockchain state | Verified Sepolia contracts determine authorized roles, pause, balances, reservations, remittance parties/amount/status and transaction outcomes. |
| Turso application-support state | User Logs, nonce/session support, wallet metadata, indexed transaction/event evidence and indexing progress. Activity is non-authoritative history, not financial truth. |
| Browser snapshot | Temporary presentation/performance cache of earlier verified reads. It cannot authorize an action or establish current financial truth. |
| Owner-observed manual evidence | Hosted MetaMask actions, observed dashboard/API results, redeploy persistence and physical-phone checks supplied by the owner. These are not represented as actions performed by Work. |
| Automated evidence | Isolated Python/browser/EVM regressions and independently obtained read-only service/chain checks. Browser wallet submissions and local EVM transactions are test mocks/local operations, not Sepolia writes. |

## Production architecture and configuration

Public URL: https://sc6113-ay2026t1.onrender.com

| Item | Frozen value |
|---|---|
| Render service | `srv-dal7read0e5s738rldh0` / `SC6113-AY2026T1` |
| Render branch | `feature/iteration-6b-production-deployment` |
| Hosting | Existing free Singapore Python service, one instance |
| Build / start | `pip install -r requirements.txt` / `gunicorn app:app` |
| Production database | One free Turso database, `sc6113-remittance` |
| Network / chain | Sepolia / `11155111` |
| Deployment ID | `sc6113-sepolia-11884239` |
| Admin | `0x4A779fA7d5eA106f1aDFB8369e65fCAA465ca7Fd` |
| RoleRegistry | `0x8E7A8Abf90cD4363F82489D14485Df7ACcaE4678` |
| deposit_money | `0x630863E58375Db128EFEfA51Ee369141cCbb839A` |
| paynow | `0xA2Ee37DD717a8758Eb864788456d047b296C00E8` |
| Manifest | `deployment/sepolia.json` |

The existing three-contract architecture, permanent wiring, ABI/build evidence
and Sepolia deployments are unchanged. Historical classroom addresses are not
used as the evolved deployment. Solidity sources match frozen Iteration 3 commit
`313a82a8514624efd9351f3d45180447ae6b966d` byte-for-byte.

Environment variable names/requirements only; no secret values are recorded:

| Variable | Requirement |
|---|---|
| `APP_ENV` | `production` |
| `FLASK_SECRET_KEY` | Strong stable secret, entered privately in Render |
| `AUTH_ORIGIN` | `https://sc6113-ay2026t1.onrender.com` |
| `TURSO_DATABASE_URL` | Remote classic libSQL primary; no local-file fallback in production |
| `TURSO_AUTH_TOKEN` | Database credential, entered privately in Render |
| `BLOCKCHAIN_RPC_URL` | Existing Sepolia HTTPS RPC; credential stays private |
| `BLOCKCHAIN_CHAIN_ID` | `11155111` |
| `ROLE_REGISTRY_ADDRESS` | Frozen RoleRegistry above |
| `FUNDING_CONTRACT_ADDRESS` | Frozen deposit_money above |
| `REMITTANCE_CONTRACT_ADDRESS` | Frozen paynow above |
| `BLOCKCHAIN_DEPLOYMENT_ID` | `sc6113-sepolia-11884239` |
| `BLOCKCHAIN_MANIFEST_PATH` | `deployment/sepolia.json` |
| `DATABASE_PATH` | Optional local development/test SQLite path |

Production session cookies remain Secure/HttpOnly/SameSite=Lax. HTTPS-origin,
single-use nonce/signature verification and session validation fail closed.
Flask has no wallet keys. No Turso token, RPC credential, Flask secret, nonce,
signature or CSRF/authentication token is committed in this evidence document.
`.env.example` contains variable names with empty values.

## Turso integration and durable User Log evidence

The minimal adapter uses official `libsql==0.1.11` against the classic libSQL
remote primary. `backend/turso.py` adapts rows/errors to the existing Flask
DB-API usage; no ORM, local replica/synchronization or architecture rewrite.
Ordinary local development/testing continues to use stdlib SQLite. Production
starts from the accepted clean additive schema; historical local test/session
records were not migrated. The existing schema, constraints, foreign keys,
upserts, nonce-consumption transactions and atomic indexing behavior are retained.
No schema change is part of the final consolidation.

References inspected during 6B implementation (2026-10-10):
- https://docs.turso.tech/sdk/python/reference
- https://docs.turso.tech/sdk/python/quickstart
- https://docs.turso.tech/cli/db/create
- https://turso.tech/pricing

The driver requires the classic libSQL engine, not the alternative Turso engine.
One free database was used; no paid infrastructure was introduced. Provider
quotas and limited free backup retention are operational limits.

The visible **Name** / **Save Name & Continue** form trims/validates names,
stores a server UTC timestamp and continues to `/main`. `user(name,timestamp)`
remains the classroom table. `/viewUser` shows Name/Timestamp columns;
**Delete All User Logs** clears only `user`, not authentication or index tables.
This is not registration or authentication and does not assign wallet roles.

Owner-verified hosted persistence sequence:
1. Names entered through the visible production form.
2. Timestamped records saved and displayed in User Log.
3. Render redeployed on the same production branch.
4. The same records remained after redeploy, demonstrating durable remote storage
   rather than reliance on Render's ephemeral local filesystem.
5. Delete All User Logs cleared the names; the page showed **No names logged.**
6. Wallet authentication/session and transaction/event indexing remained usable
   afterward, consistent with deletion being restricted to the `user` table.

This is the completed **insert → view → survive redeploy → delete all** evidence.
Automated schema/delete-isolation/atomicity tests supplement it; local libSQL
checks alone are not presented as proof of remote Turso persistence.

## Render deployment and rollback evidence

Read-only Render inspection during final consolidation confirmed implementation
head `f32ab933f5aa4cb51237a6468ad9a317c2ee2f79` was **Live**, deployment
`dep-db58k07avr4c73esj0b0`, finished `2026-10-10T18:56:01.70302Z`.
Service inspection confirmed the 6B feature branch, free plan, Singapore region,
unchanged Python build/start commands and commit-triggered auto-deploy.
The final documentation push may create another deploy of identical runtime
code; its status is reported in the final response. No Render settings are changed.

Prior non-secret rollback configuration is retained in
`docs/deployment/render-rollback.json`: previous `main` commit
`92707ce35aa22246d6cfd5592e85b52f33ddb7bc`, previous live deploy
`dep-db335vg473hc7388jfb0`, same build/start commands. Environment backups belong
privately to the owner. Any rollback is a separately authorized operational
step; no rollback or environment change is performed in this consolidation.

## Hosted MetaMask authentication and role authorization

Owner-verified hosted authentication on Render displayed Admin wallet
`0x4A779fA7d5eA106f1aDFB8369e65fCAA465ca7Fd`, Sepolia, **Admin / Auditor**.
Wallet switching and Sender/Recipient re-authentication worked in the hosted
lifecycle. Authentication signs a nonce message; connection alone is not login.
Private keys remain in MetaMask. Role permissions are verified on-chain.

| Role | Wallet | Hosted authorization transaction | Observation |
|---|---|---|---|
| Sender | `0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a` | `0x0d1225ee36f8682d44a2ab952851b6223505e272f86c38fe9221e92f58fc28a9` | Confirmed with six confirmations |
| Recipient | `0x890F63435Cf6F4D526F7062A282A94c74A50cFa3` | `0x27a9cede4d5f9a66440e19614f234b32728992ca4a41061d07289576d323320a` | Confirmed with six confirmations |

## Hosted deposit → create #3 → claim lifecycle

These are the existing owner-signed hosted transactions. This consolidation
submits no additional Sepolia writes.

| Action | Exact transaction hash | Block | Verified deployment events |
|---|---|---|---|
| Deposit `0.001 test ETH` | `0xfdb959d34b7f4ba6e82d0030f067fb9f5e36c3c7c18ced763c8a3441b02e2d28` | `11886306` | `FundsDeposited` |
| Create remittance #3, `0.001 test ETH` | `0x2f2d2ba058d5ca56ad4d18fc1fdc2a2d2bb90fd2ced22dbd189b267a6bbc69ba` | `11886325` | `FundsReserved`, `RemittanceCreated`, both `remittanceId = 3` |
| Recipient claims #3 | `0x23fd98f2e04e8f7b47eae0117a25935c6b90b618a560f4de81de57614b02a73c` | `11886364` | `ReservedFundsReleased`, `RemittanceClaimed`, both `remittanceId = 3` |

Owner-verified hosted receipts for all three returned `status: CONFIRMED`,
`canonical: true`, `activity_indexed: true`. Amount is
`1000000000000000 wei`; parties are the Sender/Recipient above. The creation
hash was recovered from hosted receipt logs rather than invented.

Observed after creation: Sender available `0.001 test ETH`, reserved
`0.001 test ETH`, #3 `PENDING`. The available balance includes the wallet's
existing funding state; this is not a claim that the single listed deposit alone
produced both balances.

Authoritative final #3 read: `id: 3`, `status: COMPLETED`,
`reservation_active: false`, amount `0.001 test ETH`,
`source: verified_contract`, `authoritative: true`.
The final dashboard showed #3 `COMPLETED`, #2 `CANCELLED`, #1 `COMPLETED`.
Independent read-only checks from this consolidation are recorded separately below.

## Direct authoritative remittance discovery

`GET /api/remittances` reads verified `remittanceCount`, scans contract records
newest-first and reads remittance/reservation state directly. Ordinary wallets
see sender/recipient participation; Admin may see all. Pagination occurs after
filtering. Responses use `source: verified_contract`, `authoritative: true`,
`discovery: direct_contract_scan`. A missing/partial Turso event index cannot
block financial discovery. The owner production-validated #1, #2 and #3.
Direct contract/RPC failures still fail closed; no fabricated financial records.

## Historical index and verified receipt fast path

The non-authoritative Turso Activity index remains bounded/resumable: six-second
request budget capped at eight, chunks capped at 25 blocks, safe atomic progress,
pass-local receipt/transaction/block RPC deduplication, short timeout/no retry
indexing transport, canonical-block/reorg fences and reconciliation/reset.
Incomplete chunks never advance checkpoints. History can report partial
`caught_up: false` or a structured unavailable condition without blocking direct
financial reads. Full historical catch-up is not a freeze prerequisite.

After successful server verification of a canonical receipt with the required
confirmations, the receipt endpoint atomically/idempotently upserts the transaction
and its decoded verified-contract events. It shares canonical row/payload mapping
with historical indexing. It does not accept browser-supplied event data and
never advances historical `indexing_state`. Wallet/participant checks precede
insertion; event participants preserve wrapper/batch visibility. Authorization,
block/hash/log validation and atomic rollback remain enforced.

Owner production verification confirmed the receipt fast path for the deposit,
creation and claim above. Activity subsequently displayed those transactions and
events. Older events appeared gradually through ordinary backfill, showing that
the two paths coexist. Duplicate receipt verification remains idempotent.
Activity indicates incomplete historical catch-up separately from recent verified
receipts. Neither path makes Turso the authority for balances or remittance status.

## Cross-page snapshot caching and safe verification retry

Non-secret `sessionStorage` snapshots are scoped by authenticated wallet,
Sepolia chain, deployment and public session presentation epoch. No authentication
tokens, nonces, signatures, CSRF secrets or provider credentials are cached.
Page navigation reuses the snapshot; dashboard list/history are fetched when
needed, and funding-first loads omit unrelated sections. Concurrent identical
reads share promises. Focus/visibility checks session validity without full
financial reloads. Explicit **Refresh account & activity** checks external
changes; wallet/network/session/deployment changes invalidate context.

Confirmed state-changing actions invalidate the snapshot once and perform one
shared authoritative load plus necessary affected section/ID reads. Claim/cancel
must verify terminal remittance state. Ordinary clicks/navigation/tab changes do
not trigger that load. Rejected/failed submissions do not invalidate the cache
as if a successful financial change occurred.

A valid submitted hash is preserved with its explorer link and non-secret pending
context across navigation. Submission remains locked while its outcome is
unresolved. Temporary verification failures show a neutral submitted/pending
message and **Check transaction**: verification only, never automatic re-signing
or resubmission. Input preview cannot erase the notice. A canonical failed/reverted
receipt with six confirmations unlocks; a successful receipt must also complete
its authoritative post-state refresh before normal action eligibility returns.
Receipt/post-state outages and verification-only recovery are automated browser
regressions. The owner observed temporary hosted RPC failures after create/claim;
later authoritative state proved completion, and accepted final retry behavior
is retained. No additional live write was performed merely to retest an outage.

Measured automated cache behavior: initial dashboard requires one account,
one balance, one list and one history read. Navigation across Funding/Remittance/
User Log/back adds zero repeats of those snapshot reads. Explicit Refresh adds
one of each. Account/network/session/deployment changes still refresh as required.

## Physical mobile MetaMask verification

**Owner-verified manual check: PASS.** Production Render site usable from a
physical phone; MetaMask mobile workflow and wallet authentication work; the
responsive interface is usable. Device, OS, browser and model details were not
supplied and are not invented. Browser regression emulation at 360/768/1280 px
supplements this evidence and does not replace the physical-phone check.
No extra mobile blockchain write was required.

## Final automated regressions

| Suite | Final result |
|---|---|
| Solidity compilation | solc `0.8.34+commit.80d5c536`, three contracts, zero warnings; Shanghai, optimizer 200 runs |
| Contract sanity | 10 groups passed; 50 expected rejection checks passed |
| Python/backend/database | 126 tests passed, isolated SQLite/libSQL databases |
| Browser/frontend | 52 tests passed, isolated Flask sessions and controlled wallet mocks |
| SQLite local-chain HTTP integration | 14 assertions passed; 12 canonical events, repeat indexing unchanged |
| libSQL local-chain HTTP integration | 14 assertions passed; 12 canonical events, repeat indexing unchanged |
| Dependency check | `python -m pip check`: no broken requirements |
| Whitespace/scope | `git diff --check` passes; final change is this documentation only |

Coverage includes wallet nonce/signature/session validation, schema/User Log
isolation, receipt atomicity/idempotence/scoping, unchanged historical checkpoints,
slow/partial catch-up, direct contract discovery, receipt/post-state outage locks,
verification-only retry, final remittance state, failure unlock, cache/navigation
and mobile layout. Local EVM checks verify genuine ABI/RPC receipt decoding and
fast-path insertion before backfill with both database drivers; no Sepolia writes.
Ganache's native µWS/Node ABI mismatch falls back successfully to JavaScript;
it is a test-tool performance observation, not an application failure.

Frozen source, manifest and schema comparisons pass. Operational credential
pattern scan has no findings; `.env.example` is blank. Runtime `user.db` SHA-256
remains `108de2caedd2c73374229f955de1e183387590b1031d05b242b03d386dbfe7cb`.
No runtime code, schema, secrets, RPC settings, contract addresses or Solidity
changes were necessary for this final consolidation.

Commands (browser dependencies belong to the test environment, not production):

```sh
python -m unittest discover -s tests -p 'test_*.py'
npm run compile:contracts
npm run sanity:contracts
PYTHON=python node tests/local-chain.cjs
LOCAL_DB_DRIVER=libsql PYTHON=python node tests/local-chain.cjs
PYTHON=python CHROMIUM_EXECUTABLE_PATH=/path/to/chromium node --test tests/frontend.cjs
python -m pip check
git diff --check
```

## Independent final read-only verification

Checked at `2026-10-10T19:23:08Z` using HTTP GETs and a separate credential-free
public Sepolia RPC connection. Render's configured RPC/secrets were not read or
changed. No wallet transaction, login signature or production database write was
performed by these independent checks.

- Public landing, Dashboard, Funding, Remittance and User Log routes returned
  **HTTP 200**. The User Log read is an availability check; the earlier delete
  empty-state proof remains the owner's manual observation.
- Unauthenticated `/api/auth/session`, `/api/remittances` and
  `/api/transactions` returned **HTTP 401**, preserving protected-session access.
- The production service/branch and Live implementation head were independently
  confirmed through Render's read-only service/deployment metadata.
- The accepted `SepoliaReader` independently verified source/runtime/deployment
  correspondence, Admin and permanent wiring, chain `11155111` and deployment
  `sc6113-sepolia-11884239`. Snapshot block **11886605**, hash `0xbed7c75789f89ba8bf4943ad82280fd18bf805e6fe976928f1f6a1b5a94758d0`;
  verified `remittanceCount = 3`.
- Direct verified #3 read returned `COMPLETED`, `reservation_active: false`,
  `1000000000000000 wei`, matching Sender/Recipient and authoritative provenance.
- Deposit/create/claim receipts were independently read and their deployment
  events decoded: canonical, successful, blocks **11886306 / 11886325 / 11886364**,
  respectively **300 / 281 / 242 confirmations** at the snapshot.
  Deposit decoded `FundsDeposited`; creation decoded `FundsReserved` and
  `RemittanceCreated`; claim decoded `ReservedFundsReleased` and
  `RemittanceClaimed`. The claim's outer destination is a wallet wrapper rather
  than paynow; verified deployment events establish the accepted association.
- This environment has no owner-authenticated production session or Turso
  credential. Current hosted Activity/Turso visibility and
  `activity_indexed: true` remain the owner's supplied manual evidence; the
  independent chain receipt reads do not claim to re-query Turso or bypass login.
  Direct-discovery implementation/source and regression checks supplement the
  owner's authenticated production #1/#2/#3 list observation.

## Operational limitations

- Public Sepolia RPC may fail intermittently; reads fail closed and submitted
  transactions retain a verification-only recovery path.
- Historical event catch-up may initially be incomplete. Recent verified receipts
  appear independently; absence from the index does not establish chain absence.
- Render Free may cold-start after inactivity; Turso persistence survives redeploy.
- Application evidence waits for six confirmations; this is the application's
  confirmation policy, not an absolute finality guarantee.
- Activity/Turso remains non-authoritative evidence/history. Browser snapshots
  require explicit Refresh for changes made by other wallets.
- Direct remittance scanning suits the low-volume coursework MVP; no high-scale
  architecture or production financial suitability is claimed.
- One free database/provider quotas and limited backup retention remain operational
  constraints. No paid service was introduced.
- Cross-border is the user/problem context. Sepolia test ETH does not demonstrate
  real fiat settlement, FX/banking integration or production international payments.

## Acceptance criteria and freeze

| Criterion | Evidence / result |
|---|---|
| Durable hosted database, local SQLite preserved | Owner insert/view/redeploy-survival/delete evidence; automated driver/database regressions — PASS |
| Existing User Log remains minimal and independent | Visible Name/timestamp flow; deletion restricted to `user` — PASS |
| Existing Render service reused, secure configuration | Live feature branch, unchanged build/start, no exposed credentials — PASS |
| Hosted wallet authentication and Sepolia lifecycle | Owner Admin/Sender/Recipient flow and exact authorization/deposit/create/claim receipts — PASS |
| Financial/index authority separation | Direct #3 completed/inactive reservation; partial index independent — PASS |
| Receipt fast path and safe retry | Owner receipt/activity results and automated failure/retry/idempotence regressions — PASS |
| Caching and mobile usability | Automated dedup/navigation/refresh/responsive tests; owner physical MetaMask check — PASS |
| Frozen scope preserved | No extra Sepolia writes, Solidity/schema/secret changes, main merge, report/slides/Drive edits or Iteration 7 — PASS |

Historical catch-up need not be complete. The operational observations above are
accepted limitations, not unresolved architecture blockers. Earlier checkpoint
pending items are superseded by this consolidated evidence. No further live
transactions are required to freeze Iteration 6B.

**ITERATION 6B: APPROVED / FROZEN**
