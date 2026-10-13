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
