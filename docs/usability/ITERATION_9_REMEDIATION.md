# Post-Iteration-9 usability remediation — local verification

## Scope and frozen baseline

Exact accepted Iteration 9 head: `1cd5df1064b80785d0c6cf57b2bdf1c83b393aaa`.
Branch: `feature/iteration-9-usability-remediation`.
Iterations 1–9 and the original usability evidence remain frozen. This record is
separate from `ITERATION_9.md` and its participant CSV; neither is rewritten.
Only bounded application fixes, tests, a local wallet-characterization utility and
this record change. No live deployment, Sepolia write, infrastructure/database change,
main merge or Iteration 10 work is performed.

## Diagnosis and implementation decisions

| Finding | Repository diagnosis | Bounded implementation |
|---|---|---|
| U9-01: waiting/loading | Frontend gated confirmation at six; app default also made the history/receipt fast path wait six. RPC latency is a separate mechanism. | Change application default and frontend threshold to one. Receipt API reports the required count and keeps zero-confirmation/noncanonical results pending. History uses the same default; bounded backfill/reorg checks stay intact. |
| U9-02: Smart Account | Existing receipt association already accepts server-decoded deployment events for wrapper/relayer participants. The study supplies no reproducible wallet version/delegation trace. A separate CALL wrapper changes msg.sender, but EIP-7702 need not change the address. | No speculative support. Add visible ordinary-account guidance and retain wrapper receipt association. Do not relax actor, wallet, event or deployment checks. |
| U9-03: account/session mismatch | Existing accountsChanged handler invalidated every event, including same-account notifications; disconnect was absent. Restore could encounter a mismatched connected wallet. | Ignore a same-account event; logout through the existing CSRF-protected API on differing/empty account or disconnect; clear current UI/cache and disable actions. Also detect mismatch during state loading. Require re-authentication. |
| U9-04: created ID | Generic confirmation/hash output did not highlight the remittance ID. | Require exactly one matching decoded paynow RemittanceCreated event; match recorded sender/recipient/amount, validate its ID and directly read that remittance. Display a strong “Remittance created — ID #…” heading distinct from transaction hash. Never derive from count. |
| U9-05: stale state | Own successful transaction refresh cleared the entire snapshot, re-reading unrelated identity, balance/list data. Lookup/history caches have distinct responsibilities. | Financial actions refresh balances; create/claim/cancel invalidate remittance lists, and claim/cancel their ID detail. Role changes refresh identity/role state and invalidate the target role lookup; pause refreshes shared pause state. Refresh Activity separately as non-authoritative history. Preserve unrelated cached reads. |

Fresh signature authentication already explicitly cleared the presentation cache;
that behavior is retained and tested. Ordinary navigation/focus reuses snapshots;
explicit Refresh and network/session/deployment changes still invalidate context.
No blanket polling, SPA conversion, provider failover or broad redesign is added.

## Confirmation and verification integrity

`BLOCKCHAIN_CONFIRMATIONS` application default changes 6 → 1; frontend also uses
one. This is the expressly approved application-policy change, not a Render environment
change. No RPC URL, address, manifest or secret value changes.

Zero confirmations cannot finish the UI flow. One canonical block is enough only
when existing deployment, receipt association and authoritative post-state checks
succeed. A noncanonical receipt remains pending even with a larger count. Definitive
canonical failure unlocks appropriately. Pending hashes remain saved and actions
locked through verification/post-state failures. Check transaction retries verification
only; no automatic signing/resubmission is introduced. Ambiguous/missing creation
events keep the operation unresolved rather than guessing an ID.

One confirmation gives less protection against a short chain reorganization than
six. This is accepted for bounded Sepolia coursework use, not production financial
finality. Reorg reconciliation remains; history/cache is not financial authority.
Existing 6A/6B/7 historical evidence and scripts recording six-confirmation observations
are left unchanged, since those observations are historical, not the current UI policy.

## Smart Account characterization and decision

`node scripts/remediation-wallet-characterization.cjs` compiles an ephemeral generic
wrapper alongside the unchanged three contracts and executes only on in-memory
Ganache. It checks:

1. An authorized ordinary wallet creates successfully.
2. The same wallet routing through an unapproved separate CALL-wrapper rejects.
3. Rejection creates no extra remittance.
4. Available accounting remains unchanged by rejection.

This demonstrates an actor-address constraint, **not** the P02/P04 root cause or a
reproduction of same-address EIP-7702. No MetaMask extension/delegation implementation
is deployed. Existing Python regressions still accept valid verified wrapper/batched
receipts and reject unrelated participants. Correct receipt association does not prove
transaction execution compatibility.

Official MetaMask sources consulted 13 October 2026:

- [What is a smart account](https://support.metamask.io/configure/accounts/what-is-a-smart-account/): MetaMask documents account upgrades retaining the existing address and programmable/batched behavior.
- [EIP-7702 quickstart](https://docs.metamask.io/smart-accounts-kit/get-started/smart-account-quickstart/eip7702/): describes upgrading an EOA to programmable functionality.

Thus Smart Account support is not inherently impossible. However, exact failure
reproduction and a demonstrated bounded fix are unavailable; the user's support
conditions are not all met. Supported mode remains a standard MetaMask account on
Sepolia. Guidance explains that Smart Account/delegation mode may need disabling if
submission is incompatible, and that a submitted hash must be checked before trying
another transaction. No wallet API/SDK architecture or permission bypass is added.

## Account, session and pending-transaction safety

A differing/empty account or disconnect clears authenticated display immediately,
invalidates snapshots and calls existing logout. A non-secret sessionStorage
`sc6113-reauth-required` flag prevents navigation from restoring an obsolete cookie
session if logout temporarily fails; only successful signature authentication clears
it. Actual server revocation requires the logout API to be reachable. Login's existing
pre/post-signing account checks handle changes during unauthenticated login; first
connection events do not cancel otherwise valid authentication.

Saved unresolved hashes remain scoped by original wallet/network/deployment. UI
receipt responses and post-state work are guarded against session changes. They are
not reassociated with a new wallet, nor are chain/history records deleted. Returning
to the original wallet and re-authenticating can restore its pending verification.

## Targeted refresh/cache behavior

The presentation cache retains its wallet/chain/deployment/session scope and explicit
non-secret allowlist. Concurrent identical section reads share one in-flight promise.
Invalidation epochs prevent stale in-flight results repopulating invalidated caches.

| Confirmed action | Current direct state read | Invalidated section evidence |
|---|---|---|
| deposit / withdraw | Own available/reserved balances | Activity; preserve unrelated remittance/role reads |
| create | Own balances; verified event-derived new ID detail | Remittance list + Activity |
| claim / cancel | Own balances + affected remittance detail/status | Remittance list, affected ID + Activity |
| authorize Sender/Recipient / revoke | Own roles and verified deployment/pause view | Target wallet role lookup + Activity; no balance/list reload |
| pause / unpause | Verified roles/deployment pause view | Activity; financial balances/list unchanged |

Controls remain disabled while authoritative state refreshes; progress describes the
refresh. Successful completion is not restored until required financial post-state
succeeds. Activity failure can be reported independently and does not make history
financial authority. External counterparty changes still require explicit Refresh.

## External/tooling observations

P05's operational RPC issue was corrected outside this pass. No provider/configuration
value is touched or old-provider dependency introduced. P03's MetaMask deceptive-site
warning is not reproduced. Static inspection finds no credential/seed collection,
dynamic code evaluation or new permission request to explain that warning. This does
not establish why the external security system warned. No warning is bypassed or
suppressed; it remains an unresolved tooling/reputation observation.

Navigation structure, visible status/history provenance and mobile layout are preserved.

## Files and tests

| File | Purpose |
|---|---|
| `app.py` | Approved one-confirmation application default |
| `backend/api.py` | Explicit required-count/pending receipt response |
| `static/js/app.js` | Session invalidation, restore guard, targeted refresh |
| `static/js/cache.js` | Selective invalidation, preserve unrelated reads, in-flight deduplication |
| `static/js/live.js` | One-confirmation flow, session race guard, verified creation ID |
| `templates/base.html` | Ordinary-account guidance; navigation unchanged |
| `tests/frontend.cjs` | Nine new remediation cases; existing fixtures updated to one confirmation and targeted reads |
| `tests/test_live_api.py` | Three new receipt-policy/logout cases |
| `tests/test_receipt_index.py` | One-confirmation fast-path/checkpoint test, also inherited by libSQL; zero-confirmation fixture updated |
| `tests/test_blockchain.py` | Confirmation-head and reorg fixtures aligned with one-confirmation policy |
| `scripts/remediation-wallet-characterization.cjs` | Four local generic-wrapper checks |
| `docs/usability/ITERATION_9_REMEDIATION.md` | Separate diagnosis, evidence and owner-review record |

New browser coverage: zero→one completion, event-derived ID/hash distinction, same
account/disconnect, fresh differently signed authentication, original-wallet pending
hash preservation, cache dedup/selective invalidation, visible guidance, missing event
fail-closed lock, and failed logout/navigation re-authentication. Existing tests cover
all ten actions, pause/role checks, network/session changes, selective navigation,
receipt/post-state outages and verification-only retries. Browser wallets and RPC are
controlled mocks, not real MetaMask or Sepolia transactions.

## Local acceptance results

| Check | Result |
|---|---|
| Solidity 0.8.34 compile | Three production contracts; zero compiler warnings |
| Contract sanity | 10 groups; 50 expected rejections PASS |
| Iteration 7 role characterization | 8 assertions PASS; accepted I7-01 preserved |
| Comprehensive local contract evaluation | 71 scenarios, 61 expected rejections, 952 assertions, 48 seeded model transitions PASS |
| Generic-wrapper characterization | 4 checks PASS; scope limitation above |
| Complete Python suite | 164 tests PASS, including SQLite/libSQL auth/index/storage and new one-confirmation cases |
| Complete browser suite | 64 tests PASS; 360/768/1280px responsive coverage retained |
| SQLite local-chain HTTP integration | 14 assertions, 12 canonical events; repeated index unchanged PASS |
| libSQL local-chain HTTP integration | 14 assertions, 12 canonical events; repeated index unchanged PASS |
| Dependencies / syntax / whitespace | pip check; JS parse checks; git diff --check PASS |
| Frozen scope | Contracts, manifest, schema, runtime database, environment/dependency manifests and original I9 evidence byte-identical |

Ganache reports a native µWS binary mismatch with Node 24 and uses its JS fallback;
checks pass. Initial browser-harness mistakes were corrected (unsupported Playwright
method, dashboard-only locator on a supporting page); final results above refer to
the completed acceptance run. The browser download initially failed; an isolated
temporary Chromium 153 executable was restored from a packaged binary. No application
dependency or build pipeline was added for this test environment.

Reproduce using existing dependencies and an available Chromium executable:

```sh
npm run compile:contracts
npm run sanity:contracts
node scripts/iteration7-role-boundary.cjs
node scripts/iteration7-contract-evaluation.cjs
node scripts/remediation-wallet-characterization.cjs
python -m unittest discover -s tests -p 'test_*.py' -q
NODE_PATH="$CODEX_PRIMARY_RUNTIME_NODE_MODULES" PYTHON=python CHROMIUM_EXECUTABLE_PATH=/path/to/chromium node --test tests/frontend.cjs
PYTHON=python node tests/local-chain.cjs
LOCAL_DB_DRIVER=libsql PYTHON=python node tests/local-chain.cjs
python -m pip check
git diff --check
```

## Hosted-verification plan — deferred, not executed

After owner review and separate deployment authorization:

1. Check hosted version, deployment identity and ordinary-account guidance without
   changing contract/config/schema values.
2. Owner authenticates; check fresh wallet/roles/balances, then same-account and
   different-account/disconnect behavior. A changed account must re-authenticate.
3. Owner signs only an agreed small test lifecycle; inspect canonical confirmation
   #1 success, affected balances/status and event-derived created ID/hash presentation.
4. Verify Activity evidence/provenance, page navigation snapshot reuse and explicit
   Refresh for counterparty changes. Do not claim instantaneous confirmation or RPC.
5. If verification temporarily fails, preserve hash/lock and use Check transaction
   only. Check original-wallet pending context after switching back. No blind resubmit.

No such hosted transaction/deployment is performed now. Real MetaMask mode behavior,
external warnings and public-RPC timing remain limitations requiring owner observation.

## Acceptance status

**LOCAL VERIFICATION PASSED — READY FOR OWNER REVIEW BEFORE HOSTED SMOKE DEPLOYMENT.**
This is not hosted approval, a new usability study, a Solidity/security audit or a
production-financial suitability claim. No main merge, Render deployment, Sepolia
write, Turso operation or Iteration 10 work is performed.

## Hosted checkpoint — deployment and unauthenticated page verified

Owner manually deployed exact commit `324a0f913b432ae0b0746f5ade5128860fbf303b`.
Render deploy `dep-db719sm7bikc7393i9u0` is **live**, finished
13 October 2026 at 11:25:37 UTC (19:25:37 Asia/Kuala_Lumpur).
Startup logs show Gunicorn listening on port 10000 and a worker booted; no error/
critical entries were returned for the checked 11:24:34–11:29:03 UTC window.

Independent HTTP checks: `/main` and all three changed JS assets return 200.
Hosted `app.js`, `live.js`, `cache.js` match the approved commit byte-for-byte.
HTML contains visible ordinary-account guidance and configured deployment ID
`sc6113-sepolia-11884239`. Unauthenticated `/api/auth/session` returns 401
`AUTH_REQUIRED`, as expected. This configured ID is not itself a fresh chain proof.

Hosted request logs also show owner-browser authentication, `/api/users/me`,
`/api/users/me/balances`, `/api/remittances` and `/api/transactions` returning 200.
Those status codes establish successful requests, not independent inspection of the
owner's wallet/role/balance payload. Wallet preflight is the next manual checkpoint.
No wallet transaction was submitted by Work; ordinary and Smart Account create
results, first-success confirmation count and account-switch evidence remain pending.

Render retains the 6B linked branch/build/start settings; its exact-commit dashboard
operation changed auto-deploy from on to off as documented at the deployment
checkpoint. No environment values were edited by Work. Future deployment must be
explicit; do not treat a documentation push as deploying this branch automatically.
**Hosted remediation acceptance remains pending.**

## Subsequent hosted observations — owner-supplied evidence

The owner subsequently tested the exact deployed `324a0f913b432ae0b0746f5ade5128860fbf303b`
commit. This supersedes the pending wallet checkpoint above; it does not replace the
frozen participant study or imply that Work independently inspected every payload.

| Test | Owner-observed result |
|---|---|
| Ordinary authentication | `0x890F...cFa3`, Sender/Recipient; initially available 0.001 test ETH, reserved zero |
| Ordinary create | #10, 0.0005 test ETH; successful `Confirmed (1 confirmation)` and prominent `Remittance created — ID #10`; available/reserved each 0.0005 test ETH; #10 PENDING |
| Account switch | Switching to `0x3e09...0442a` immediately cleared old identity; sign-in-again notice, new authentication required, then matching connected/authenticated wallet and fresh Sender/Recipient roles |
| Smart Account create | MetaMask Smart Account/delegation enabled on Sepolia; `0x3e09...0442a` to `0x890F...cFa3`, 0.00001 test ETH, #11; `Confirmed (1 confirmation)`, prominent ID #11 and successful authoritative post-state |

Ordinary creation transaction:
`0x7adf8388b63663ba140c07ae2116c15634b18ac9be8cf629ff77e521ff90c8c3`.
Smart Account creation transaction:
`0x7daf5245f10607524477fc0aa85d0457382b4ae1c4a03c922d7f5d616f9ec4b6`.
No new transaction was submitted during this performance correction.

U9-01, U9-03 and U9-04 passed hosted observation. U9-02 **functional compatibility
passed for this specific tested MetaMask/Sepolia configuration only**. This is not
generic Smart Account support. Wallet warnings included “Unknown”, “Added protection”,
“Malicious site” and “High-risk request”; several acknowledgements caused substantial
wallet-side friction. Their cause is not established as a repository-controlled DApp
defect. Do not bypass or suppress security warnings. The guidance now describes this
limited success, prefers ordinary accounts, disclaims broader compatibility and
instructs verification before retrying when a hash exists.

U9-05 state correctness passed; hosted performance remained unacceptable. Owner-supplied
Render log completion times (SGT): auth verification 19:49:31; `/api/users/me`
19:49:42; balances 19:49:52; remittances 19:50:13; activity 19:50:29.
The elapsed span is approximately 57–58 seconds, with approximate incremental waits
of 10, 10, 21 and 16 seconds as reported. These are successive completion times,
not isolated endpoint duration measurements. The owner subjectively reported 1–2
minutes and 15–20 seconds before the MetaMask create-confirmation UI. The latter
suggests preparation latency, not blockchain confirmation latency; hosted endpoint
profiling has not independently established its exact duration.

## Performance correction — diagnosis and boundary

Inspection confirms `get_reader()` previously reused only Flask request-local `g`.
Every fresh HTTP request repeated source/build checks, deployment transactions and
receipts, constructor/deployer evidence, historical block anchors, runtime code and
wiring checks before endpoint-specific reads. The frontend loads account, balances,
remittances and activity sequentially. Remittance discovery also repeated the same
pinned-block hash check for every record. This explains redundant work; public-RPC
latency and bounded history catch-up can contribute separately. Reader construction
does not invoke a compiler. Local fingerprinting still occurs on each request and
was small relative to the injected RPC waits in the controlled profile.

### Verified static evidence versus fresh state

The cache stores **verified static evidence, never a SepoliaReader or financial
snapshot**. It is process-local, at most four contexts, with a non-sliding 60-second
expiry and single-flight verification. Its private SHA-256 identity includes all
blockchain configuration fields, RPC endpoint identity, manifest path/content, build
content/compiler settings, source content and source/build mapping. Raw RPC credentials
are not serialized, sent to the browser or logged by the profiler. Restart, expiry,
input change or explicit test cache reset requires complete original verification.

Cold verification retains source/compiler/runtime/creation-input/deployer/constructor/
receipt/canonical-block/wiring proofs. Only successfully **wired** deployments are
cached. Unwired funding is deliberately never cached. Frozen exact runtime implements
immutable Admin/registry/funding references and a permanently locked one-time trusted
remittance reference; it has no proxy upgrade route. Those verified references may
therefore be reused while their canonical evidence remains valid.

Every warm reader remains independent and fetches:

- fresh latest block number and its hash, chain ID;
- exact current runtime bytes for all three contracts, **including immutable spans**;
- canonical hashes for deployment blocks and the block anchoring verified wiring;
- fresh pause and remittance count;
- endpoint-specific roles, balances, reservations and remittances at the pinned block.

Current receipt data, confirmations, canonicality, decoded events and post-state are
not cached globally. A reorg, code mismatch, bad chain or failed revalidation fails
closed; static verification failures evict the entry without stale fallback. Normal
structured unavailable errors remain intact. Dynamic preparation still validates
wallet/roles/recipient/pause/available funds, unsigned transaction contents and gas.

For direct remittance list discovery, all reads remain pinned to one block. A final
snapshot check occurs before any batch results are returned, rather than after every
record. A changed canonical hash rejects the complete response. Participation filtering,
newest-first ordering, pagination and financial authority remain unchanged. No browser
refresh/polling behavior was added; navigation caching, account/session invalidation,
one-confirmation policy, event-derived ID and verification-only retries are preserved.

### Reproducible local performance characterization

`scripts/profile-verified-reads.py` compares accepted checkpoint source with the new
reader using an isolated synthetic RPC, 11 remittances, an empty-event index and 5 ms
delay per counted RPC operation. It executes reader plus endpoint operations, not a
real hosted HTTP/auth/Turso workload. The account request is cold and the others warm.

| Operation | Before RPC calls | After RPC calls | Before/after complete static proofs |
|---|---:|---:|---:|
| Account | 26 | 26 | 1 / 1 |
| Balances | 26 | 16 | 1 / 0 |
| Remittances | 56 | 36 | 1 / 0 |
| Activity, empty-event catch-up | 33 | 23 | 1 / 0 |
| Prepare create | 31 | 21 | 1 / 0 |
| Total sequence | 172 | 122 | 5 / 1 |

Measured controlled sequence time was 890.48 ms before and 632.67 ms after (~29%
reduction); preparation was 161.65 ms versus 108.95 ms (~33%). These synthetic local
times **do not establish hosted speed improvement**. Machine-readable call breakdowns
and readable results are in `results/iteration9_read_performance.csv` and `.md`.
Warm preparation avoids redundant deployment transactions/receipts and immutable
getter proofs while retaining fresh dynamic authorization, gas estimation and checks.

### Final local regression evidence

| Check | Final result |
|---|---|
| Solidity 0.8.34 compile | 3 contracts, 0 warnings |
| Contract sanity | 10 groups, 50 expected rejections PASS |
| I7 role boundary | 8 assertions PASS; accepted Low I7-01 unchanged |
| Comprehensive contract evaluation | 71 scenarios, 61 expected rejections, 952 assertions, 48 model transitions PASS |
| Generic-wrapper characterization | 4 checks PASS |
| Python | 179 tests PASS, including 15 static-context/fresh-state regression tests |
| Browser | 64 tests PASS, including existing 360/768/1280 px, account-switch, confirmation, verified-ID and retry checks |
| SQLite local-chain HTTP | 14 assertions, 12 canonical indexed events; repeat unchanged PASS |
| libSQL local-chain HTTP | 14 assertions, 12 canonical indexed events; repeat unchanged PASS |
| Dependencies/static/scope | pip check, JS syntax and git diff --check PASS; frozen sources/schema/config/manifests/I9 evidence unchanged |

The new tests exercise static single-flight reuse, distinct request readers, wallet
separation, fresh head/roles/balance/pause/count, input invalidation, exact immutable-byte
runtime mismatch, wrong chain, deployment/snapshot reorg rejection, TTL failure with
no stale fallback, uncached unwired state, fresh receipts/confirmations, all dynamic
prepare conditions and cache reset. Existing RPC failure, one-confirmation, pending-lock,
account switch and verified-ID regressions remain passing. Ganache's native µWS binary
is unavailable under this Node runtime; its documented JS fallback passed all checks.

Additional reproducibility commands (alongside the complete suite above):

```sh
python -m unittest discover -s tests -p 'test_*.py' -q
python scripts/profile-verified-reads.py --rpc-delay-ms 5
```

### Remaining limitations and next hosted checkpoint

Conservative warm verification still needs RPC for runtime and canonical anchors;
cold verification recurs after expiry/restart and separately per worker. A slow provider
can still be slow. Direct scanning is low-volume O(n); historical catch-up remains
independent and time-budgeted. Dashboard reads remain sequential. No absolute latency
promise, generic Smart Account guarantee, production financial finality claim or new
physical-phone result is made.

After owner review and separate deployment authorization, deploy the reviewed exact
commit without changing environment values. Use hosted read-only timing to compare
cold/warm account, balances, remittances, Activity and unsigned preparation. Check fresh
state, navigation reuse, explicit Refresh, unavailable/reorg failure behavior and
guidance. Reuse existing hosted writes; no new write is needed merely to time reads.
If a later transaction test is desired it requires a separate owner-signed checkpoint.

**PERFORMANCE CORRECTION LOCALLY VERIFIED — HOSTED RE-VERIFICATION REQUIRED**
No Render deployment, Sepolia write, Solidity/deployment/config/schema change, main
merge or Iteration 10 work occurred during this correction. Hosted performance and
the overall remediation freeze remain pending.

## Second performance correction — owner-observed hosted checkpoint

The owner deployed first correction `bd571500c73690bd2a58a991d49fded4bb025ac9`,
Render deployment `dep-db726959fdbs73epce10`, reported **LIVE** without config/env/address
or contract changes. This is owner-supplied hosted evidence, not a new Work deployment.
On 13 October 2026 (SGT), successful auth completed 20:29:40.400; account completed
20:29:49.957; balances 20:29:55.931; remittances 20:30:13.639; Activity 20:30:26.147.
The resulting 45.747-second span improved approximately 20% over the previous
57–58-second observation but remained unacceptable. These are successive completion
times, not instrumentation isolating every request's execution duration.

Transfer page session was observed at 20:32:07.420; recipient roles completed at
20:32:23.419 (~16 seconds). Preparation completed 20:32:34.669 (~11.25 seconds after
the role response); perceived Create-to-wallet-UI wait was ~15 seconds. The owner
**rejected** the MetaMask request. No Sepolia transaction resulted. The role request
was outside the 60-second cache window, while preparation was warm. Extending TTL alone
therefore cannot address the remaining warm bottleneck. U9-01/03/04 and U9-05 correctness
remain hosted PASS; specific Smart Account success and warning friction remain as
recorded above. U9-05 performance still requires hosted re-verification.

### Remaining warm-path profile

Before this second correction, a warm constructor performed a head read, initial hash,
chain ID, three runtime-code reads, four historical/verification-anchor reads, pause,
count and final snapshot hash. Endpoint checks then added their own pinned state and
final hash. No full static proof reran, but substantial partial static proof did.

The controlled 11-remittance fixture separates the operations below. Columns A–E are
logical RPC messages, not HTTP batch round trips. Chain ID is retained as a current
network-identity safeguard; it is not part of the reused historical proof.

| Warm endpoint | A: static runtime/anchors before → after | B: current head/chain/hash before → after | C: pause/count | D: endpoint reads | E: history |
|---|---:|---:|---:|---|---|
| Account | 7 → 0 | 5 → 5 | 2 | 2 wallet-role calls | 0 |
| Balances | 7 → 0 | 5 → 5 | 2 | 2 balance calls | 0 |
| Recipient roles | 7 → 0 | 5 → 5 | 2 | 2 role calls | 0 |
| Remittances | 7 → 0 | 5 → 5 | 2 | 22 transaction/reservation calls | 0 |
| Activity | 7 → 0 | 4 → 4 | 2 | 0 | 10 messages: 3 log requests, 7 deliberate reconciliation/block checks |
| Prepare create | 7 → 0 | 6 → 5 | 2 | 2 owner roles, recipient role, available funds, simulation, gas estimate | 0 |

An index with actual logs additionally reads deduplicated transaction receipts,
transactions and log blocks. Those evidence/reorg checks are intentionally unchanged.
Provider/Web3 middleware can add other messages outside this controlled reader fixture.

### Second-pass implementation and trust boundary

The existing **60-second, non-sliding, content/config-keyed static context** now reuses
runtime, historical receipts/transactions/anchors and proven immutable wiring without
re-fetching them on each warm request. TTL was not increased. Full original proof
runs on expiry, restart/clear or identity/content change, fails closed on error, and
also compares previously verified exact runtime bytes during same-identity expiry
revalidation. A wired context is required; unwired relationships remain uncached.

Fresh per-request readers still obtain head/hash, chain ID, pause/count, wallet roles,
financial state, receipt canonicality/confirmations and transaction post-state. Fresh
chain ID remains a low-cost check against a changed/wrong-network RPC. No wallet or
financial state is placed in the process-wide cache. Dynamic getter reuse is scoped
strictly to one reader's pinned block and exact contract/function/argument tuple.

**Explicit bounded trade-off:** a change/reorg affecting old deployment evidence is
not re-queried on every warm endpoint. It is detected on bounded full revalidation;
current snapshot/receipt reorg checks remain fresh. This assumes the frozen exact
non-upgradeable runtime and stable configured Sepolia RPC within the cache interval.
It is a coursework performance policy, not an instantaneous historical-reorg detector,
a stronger RPC trust model or production financial assurance. Warm dynamic failures
still return unavailable state rather than stale financial results.

Independent contract reads use the installed Web3 **7.14.0** batch API. Its HTTP batch
transport is narrowly subclassed to require exact request/response ID correspondence,
unique IDs, expected count and successful JSON-RPC results before ABI decoding.
Reordered valid responses are mapped deterministically. Missing/duplicate/unknown IDs,
RPC errors, timeout or malformed ABI reject the batch without populating partial getter
cache. No browser-supplied financial data is used. Every eth_call has the same explicit
block number; a final current-block hash fence must pass before results escape.

Remittances prefetch at most **10 IDs / 20 eth_calls** per transport batch, newest-first,
then preserve participant/Admin filtering and pagination. A last batch may read a few
extra records before the requested page is filled; the bound remains ten. Single-item
transaction/reservation pairs, role pairs and balance pairs also batch. Available funds
and recipient authorization are batched during create preparation; owner role checks,
pause, exact unsigned from/to/data/value, simulation and gas estimation remain required.
Preparation uses one final pinned-snapshot fence rather than an extra intermediate fence.
No state from a previous HTTP request is reused for preparation.

Activity remains separately indexed, bounded, resumable and non-authoritative. Its
receipt/event verification, chunk reconciliation fences and checkpoint semantics were
not modified. No aggregate dashboard endpoint or concurrent-request frontend was added:
batching materially reduces the existing paths without new API/UI coupling. The current
sequential routes and cross-page presentation-cache semantics remain intact. Check
Inputs still waits for authoritative recipient permissions and cannot enable unsafe
submission merely on syntax validation.

### Controlled before/after results against bd57150

Artifacts: `results/iteration9_warm_performance.csv` and `.md`; reproduce with
`python scripts/profile-warm-reads.py --rpc-delay-ms 5`.
The offline fixture uses 11 records and an empty-event backfill. Transport grouping
and a 5 ms round-trip delay are **emulated**, with actual Web3 ABI/strict batch behavior
and real local-EVM HTTP integration tested separately. Counts exclude hosted HTTP/auth,
Turso transport, provider computation and middleware-specific additional calls. Cold
means full proof; warm excludes one priming proof. No public RPC or write is used.

| Endpoint | Cold messages / trips before → after | Warm messages before → after | Warm trips before → after | Warm ms before → after |
|---|---|---:|---:|---:|
| Account | 26/26 → 26/25 | 16 → 9 | 16 → 7 | 83.01 → 37.19 |
| Balances | 26/26 → 26/25 | 16 → 9 | 16 → 7 | 84.23 → 39.75 |
| Recipient roles | 26/26 → 26/25 | 16 → 9 | 16 → 7 | 83.56 → 37.37 |
| Remittances | 46/46 → 46/26 | 36 → 29 | 36 → 8 | 186.99 → 42.54 |
| Activity | 33/33 → 33/33 | 23 → 16 | 23 → 15 | 122.90 → 80.44 |
| Prepare create | 31/31 → 30/28 | 21 → 13 | 21 → 10 | 110.23 → 53.53 |

Complete sequential dashboard fixture (cold account, warm balances/remittances/Activity):
**99 → 80 logical messages; 99 → 55 transport round trips; 528.05 → 299.39 ms** (~43%
controlled latency reduction). Both versions execute one complete static proof in this
sequence; standalone warm operations execute zero and standalone cold operations one.
Warm runtime-code reads fell 3 → 0; old deployment/verification-anchor reads 4 → 0.
Warm roles improved ~55%, remittances ~77% and preparation ~51% in this transport-delay
fixture. These values do **not** predict hosted times. Cold Check Inputs can still pay
full verification after expiry; historical index processing and actual RPC latency remain.

### Second-pass regression and scope

| Check | Result |
|---|---|
| Solidity 0.8.34 | 3 frozen contracts compile; zero warnings |
| Contract sanity | 10 groups / 50 expected rejections PASS |
| I7 characterization | 8 assertions PASS; accepted Low role limitation unchanged |
| Comprehensive contract/security evaluation | 71 scenarios, 61 expected rejections, 952 assertions, 48 model transitions PASS |
| Generic-wrapper characterization | 4 checks PASS |
| Python/backend | 192 tests PASS |
| Browser/frontend | 64 tests PASS; one-confirmation/account-switch/verified-ID/retry/navigation/responsive behavior retained |
| SQLite and libSQL local-chain HTTP | Each 14 assertions / 12 canonical indexed events; repeat unchanged PASS |
| Dependency, syntax, whitespace, frozen scope | PASS; no requirements/schema/source/config/manifest/I9 evidence change |

New regressions cover zero warm runtime/anchor calls, successful TTL full proof, actual
Web3 batch ordering/pinning/getter deduplication, missing/duplicate/unknown IDs, errored
or malformed results, timeout, bounded 20-call remittance batch, wallet-role isolation
and structured batch-failure 503 on SQLite/libSQL API paths. Prior tests retain fresh
roles/pause/balances/count/remittances, failed TTL revalidation, identity/build/source
changes, cache reset/single-flight, snapshot reorg rejection, fresh receipt confirmations,
dynamic prepare authorization and one-confirmation/retry/ID rules. The two previous
per-request historical/runtime revalidation tests now check expiry revalidation, matching
the intentionally changed bounded static trust policy. No deployment verification was
removed from cold proof. Ganache uses its JS fallback for the unavailable native µWS
binary in this Node runtime; all checks pass.

Changed implementation files are `backend/blockchain.py`, `backend/api.py` and
`backend/preparation.py`; other changes are tests, profiling results/utility and this
remediation record. Frozen participant evidence, Solidity, contract addresses, deployment
manifest, schema, runtime DB, dependencies, environment/config and secrets are unchanged.
No Render deployment, Sepolia transaction, main merge or Iteration 10 work occurred.

### Next hosted read-only re-verification

After owner review and separately authorized exact-commit deployment, confirm LIVE,
startup and verified deployment without configuration changes. Time cold and warm
account/balance/recipient/remittance/activity reads and unsigned preparation separately;
the owner can reject the wallet prompt with no transaction. Verify the configured RPC
accepts standard JSON-RPC batches: unsupported/rejected batches fail safely, and no
hosted compatibility claim is made before this check. Check full verification after
expiry, fresh roles/balances/pause, snapshot consistency and ordinary navigation reuse.
Do not require new Sepolia writes just to measure performance. Do not bypass Smart
Account warnings. The bounded static interval, per-worker cold costs, sync request
ordering, low-volume O(n) scanning and public-RPC failures remain limitations.

**SECOND PERFORMANCE CORRECTION LOCALLY VERIFIED — HOSTED RE-VERIFICATION REQUIRED**
Overall remediation is not frozen yet.
