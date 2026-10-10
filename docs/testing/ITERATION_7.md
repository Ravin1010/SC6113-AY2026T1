# Iteration 7 — Comprehensive testing, security review and gas evaluation

## 1. Frozen baseline and scope

Project: **Cross-Border Remittance DApp with Recipient Claim and Status Tracking**.
Accepted production baseline: `8c99477be903ed3885249ad91be17b103f5ab4bc`.
Evaluation checkpoint resumed: `fda2702cc06e79ba26528658eda961b610e853a1`.
Branch: `feature/iteration-7-testing-security-gas`. Iterations 1–6B remain frozen.
Only evaluation tests/utilities/results/documentation change. No production runtime,
Solidity, schema, manifest, deployment, credentials or infrastructure change.
Sepolia chain ID 11155111; deployment ID `sc6113-sepolia-11884239`.
Frozen public addresses and deployment details remain in `deployment/sepolia.json`.

## 2. Methodology and evidence boundaries

- **Deterministic automation:** isolated Ganache/temporary SQLite and real libSQL driver files, controlled wallet/RPC/browser fixtures. Local EVM deployments/writes are test execution only, not public deployment.
- **Historical live evidence:** existing 6A ten-action smoke receipts and 6B hosted lifecycle. No new Sepolia write.
- **Fresh read-only evidence:** existing receipts re-read for gas, status/canonical block/event validation and confirmations. No production session or Turso credential is used. This does not independently repeat hosted UI operations.
- **Owner-observed evidence:** production persistence across redeploy, wallet switching/authentication and physical-phone MetaMask usability from accepted 6B documentation. No device/browser/model details are invented.

Blockchain is financial authority. Turso/indexed Activity is non-authoritative history;
browser snapshots are temporary presentation caches. Passing tests do not constitute
formal verification, a professional audit, representative migrant-user evaluation,
production suitability or proof against every attack.

## 3. I7-01 discovery, review and adopted resolution

The original requested criterion said “Admin cannot self-assign ordinary roles.”
The checkpoint reproduction showed both authorizeSender(Admin) and
authorizeRecipient(Admin) succeed: the immutable deployer is the authorized caller;
neither function excludes it as the target. Unauthorized callers still reject.

The owner reviewed this result and adopted **Option A**:

> Only the immutable Admin may grant and revoke ordinary Sender and Recipient permissions. Sender and Recipient permissions do not grant, modify, transfer, or replace Admin authority. The deployed MVP technically permits the Admin address itself to also hold Sender and/or Recipient permissions. This is accepted as a Low-severity role-separation limitation and is not used as the normal operational configuration.

The discovery is preserved, including `original_self_assignment_prohibition: FAIL`
in the updated role-boundary result. The corrected authorization/immutable-Admin
criterion is **PASS**, and I7-01 is **Low / Accepted limitation**. No privilege
escalation is demonstrated; no frozen Solidity/deployment correction is required.
Eight characterization assertions reproduce the actual behavior and retained checks.
This conscious policy acceptance supersedes the blocked checkpoint verdict.

## 4. Ten-transaction verification matrix

`E7` = `scripts/iteration7-contract-evaluation.cjs`; `S3` =
`scripts/sanity-contracts.cjs`; `B` = `tests/test_blockchain.py` and live API fixtures;
`UI` = `tests/frontend.cjs` mocked ten-action preparation/submission checks.
Each row has E7 positive/events/rejection evidence, S3 lifecycle/safety evidence,
B unsigned preparation/authorization and UI integration evidence. Receipt hashes
below are existing, freshly read-only checked 6A transactions; additional 6B samples
are retained in the gas JSON. Internal coordination/wiring/getters are excluded.

| Action / contract | Required role and preconditions | Success / events | Important rejection cases | Automated evidence | Existing Sepolia receipt | Local gas | Status |
|---|---|---|---|---|---|---:|---|
| `authorizeSender` / RoleRegistry | Admin: Nonzero target; Sender absent | Sender permission set; RoleAuthorized(Sender) | Non-Admin, zero target, duplicate grant | E7 + S3 + B + UI | `0x435c01292070c2c4973fb6f04d38fd592e0a89c8ba532a418f90d8f67efee599` | 46,207 | Accepted Low I7-01 |
| `authorizeRecipient` / RoleRegistry | Admin: Nonzero target; Recipient absent | Recipient permission set; RoleAuthorized(Recipient) | Non-Admin, zero target, duplicate grant | E7 + S3 + B + UI | `0xe90e29d163dda3503e1cdefdf3331e2f49d074e5e68756f489519ea2c4821564` | 46,217 | Accepted Low I7-01 |
| `revokeRole` / RoleRegistry | Admin: Nonzero target; selected ordinary role present | Only selected permission cleared; RoleRevoked | Non-Admin, zero, missing role, invalid Admin enum | E7 + S3 + B + UI | `0xe9a297cd30bca10c31a68b88ecca477319bce908d4545d93b64d5f4d158dac83` | 24,514 | PASS |
| `pause` / RoleRegistry | Admin: Currently unpaused | Shared flag true; five financial actions blocked; SystemPaused | Non-Admin; already paused | E7 + S3 + B + UI | `0x424e7ea47c58a084d0bec781824d350bc1a816579301ab088927f9adc7aac766` | 44,637 | PASS |
| `unpause` / RoleRegistry | Admin: Currently paused | Shared flag false; actions resume; SystemUnpaused | Non-Admin; already unpaused | E7 + S3 + B + UI | `0x1fb6c70f0e4f0952700bd2f6397b0ef1c3df604ee3019e2a1b30a6312192be99` | 22,751 | PASS |
| `deposit` / deposit_money | Authorized Sender: Unpaused; msg.value > 0 | Caller and total available increase by msg.value; FundsDeposited | Zero, unauthorized/revoked Sender, paused, plain ETH send | E7 + S3 + B + UI | `0xc7e5eafd2f395a59805f992f7a55dc3c2231d79193cd2f0e16b9e48d0f6c2858` | 78,301 | PASS |
| `withdraw` / deposit_money | Balance owner: Unpaused; positive amount ≤ own available | Available debited; owner paid; failure rolls back; FundsWithdrawn | Zero, insufficient/unowned balance, reserved funds, paused, rejecting/reentrant receiver | E7 + S3 + B + UI | `0xbe8040bc5c08dd3a8be9548a7ebd3b5ea285ddba1fdcbc1e1ddf646ebeeffcd2` | 54,459 | PASS |
| `transfer` / paynow | Authorized Sender: Unpaused; wired; distinct nonzero authorized Recipient; amount > 0 ≤ available | New ID/PENDING; exact funds reserved atomically; FundsReserved + RemittanceCreated | Unauthorized/revoked Sender, zero/self/unapproved Recipient, zero/excess amount, paused, unwired | E7 + S3 + B + UI | `0x3ae3b35001cdf73c9a3540a9af0087300afb23600901eaa93f148c716b652ff6` | 285,988 | PASS |
| `claim` / paynow | Recorded Recipient: Unpaused; ID exists and PENDING; caller matches | COMPLETED; exact payout; inactive reservation atomically; ReservedFundsReleased + RemittanceClaimed | Wrong claimant, double/unknown/after-cancel, paused, rejecting/reentrant receiver | E7 + S3 + B + UI | `0xbca164391f46a2955e91465f1663964245743d6572425ab520d80c992aaa13e5` | 114,416 | PASS |
| `cancel` / paynow | Recorded Sender: Unpaused; ID exists and PENDING; caller matches | CANCELLED; reservation returned to availability; ReservedFundsUnlocked + RemittanceCancelled | Other authorized Sender, Recipient, double/unknown/after-completion, paused | E7 + S3 + B + UI | `0xf4b5220faab62424594ad36bdfc9092e7341149a66d663d4db0abb062ffaa580` | 115,218 | PASS |

Claim/cancel/withdraw do **not** require a still-current ordinary role: existing
ownership/participant rights survive revocation, subject to shared full pause.
Role administration remains available during pause. A wallet can hold independent
Sender and Recipient permissions; an individual remittance still uses distinct wallets.
All ten types have successful deterministic and existing live evidence; the two role
grants carry the consciously accepted I7-01 limitation rather than an invented rejection.

## 5. Functional, negative and accounting tests

E7 adds targeted cases for unauthorized role administration, zero/duplicate grants,
invalid revocation enum, role independence, immutable Admin/no transfer setter,
permanent wiring, trusted-only reservations, amount/recipient/balance/identity bounds,
plain ETH rejection, pause coverage and role administration during pause, exact
stored parties/status/amount and creation event payloads, claim payout net of gas,
terminal-state/double-use rejection and post-revocation exit rights.

The original sanity suite additionally uses a rejecting/reentrant receiver compiled
only in memory. Claim rejection rolls back remittance status/reservation; withdrawal
rejection rolls back accounting. Recipient and funding callbacks cannot reenter.
Neither receiver fixture is a fourth application contract.

E7's seeded model interleaves 48 deposits, withdrawals, creation, claims and
cancellation across two Senders/two Recipients, checking each owner's available and
reserved totals, all tracked remittance statuses/active flags, aggregate totals and
actual custody balance after every operation. Equality applies to these scenarios
without forced ETH; generally liabilities must be **≤** contract ETH balance.
This is a bounded reproducible model test, not a huge fuzz campaign.

E7 final result: **71 scenario checks, 61 expected rejections, 952 explicit assertions, 48 model transitions**. Exact cases and environment are in `results/iteration7_contract_evaluation.json`.

## 6. Manual Solidity security review

Review covered all three frozen sources and their call relationships:

| Area | Evidence and conclusion |
|---|---|
| Admin / ordinary roles | onlyAdmin guards five administration actions. Admin is immutable; enum contains ordinary roles only. Grants are independent. I7-01 accepted, no ordinary-to-Admin escalation path. |
| Wiring | Admin-only one-time setter requires code/nonzero address and matching registry/funding getters; address cannot be cleared/replaced after setup. Getter matching is not a general proof that an arbitrary candidate is trustworthy, so deployment verification remains essential; frozen deployed paynow is already verified. |
| Authorization ordering | Pause/guard precede financial effects; Sender/Recipient checks precede new reservation. Claim/cancel use recorded participants intentionally, not current roles. All funding coordination checks trusted caller. |
| CEI / external calls | Withdrawal and release debit accounting/active flag before ETH call. Claim marks COMPLETED before funding release. Revert rolls back both contracts if payout fails. Cancel uses fixed sender and unlocks internally. No caller-selected withdrawal/payout redirect. |
| Reentrancy | Local guards cover all funding accounting mutations and remittance actions; callbacks reject. Role getters are read-only calls. Recipient rejection affects its claim and leaves sender cancellation possible while pending/unpaused. |
| Accounting | Positive amounts, sufficient available balance and unique reservation ID checks; lock moves available to reserved; release decrements reserved; unlock restores original owner. Solidity 0.8 checked arithmetic protects overflow/underflow. |
| Lifecycle / replay | Only PENDING can reach COMPLETED or CANCELLED. Existing IDs cannot be reserved again; terminal/double claim/cancel reject; no expiry, partial claims or reopening. |
| Events | Successful effects emit useful parties, IDs, amounts and statuses; revert removes provisional logs. Creation event args/sequence checked directly and later server ABI decoding/indexing tested. |
| Unexpected ETH | No payable receive/fallback: ordinary ETH sends reject. Forced ETH can still create uncredited surplus. It cannot create spendable user credit; no sweep action exists. |
| DoS / computation | Financial actions have fixed work rather than scanning all remittances. A rejecting recipient can block its payout, not redirect funds; atomic rollback plus pending cancellation protect accounting. Full pause and single Admin key create the known liveness dependency below. |

### Findings and accepted limitations

No **Critical or High** finding was identified in this bounded manual review and
these tests. This is not a claim that none can exist or a formal audit.

| ID / severity / status | Component / evidence | Preconditions / actual impact | Mitigation / boundary |
|---|---|---|---|
| I7-01 / Low / Accepted limitation | RoleRegistry permits Admin target in both grants; local reproduction | Legitimate Admin already controls sole authority; can combine ordinary permissions with Admin. No unprivileged escalation or demonstrated loss. | Option A accepted; normal operational Admin kept separate. Immutable authority and non-Admin rejection remain. |
| I7-02 / Medium / Known accepted liveness limitation | Immutable sole Admin plus full financial pause, documented since Iteration 3 | Admin pauses and cannot/will not unpause, including key loss: exits remain blocked indefinitely. No confiscation/accounting mutation, but access can remain suspended. | Coursework trust/single-Admin design; owner key responsibility. No recovery/governance feature introduced. |
| I7-03 / Low / Accepted classroom data-integrity limitation | `/deleteUser` is public POST, no wallet role/auth requirement; deletes only user | Any site visitor can clear shared name logs or add names. Logs are not an authenticated identity/audit authority. | Explicit minimal public User Log scope, parameterized SQL/escaping and delete-isolation tests. Do not put sensitive records here; no financial authority affected. |
| I7-04 / Informational / Accepted custody limitation | No unsolicited-ETH credit or surplus sweep | Forced ETH may remain uncredited/unrecoverable; liabilities are not increased, no other-user withdrawal path. | Use deposit(); reconcile liabilities ≤ custody; no arbitrary Admin fund sweep. |
| I7-05 / Informational / Accepted scale/availability limitation | Direct scan + public RPC + shared snapshot | Large count/high request traffic or stale presentation may delay views; external wallet changes need Refresh. Cached views are not transaction authorization. | Low-volume coursework; authoritative preparation/simulation rechecks chain, targeted confirmation refresh, explicit fail-closed errors and Refresh. |

I7-02/03/04/05 describe already frozen behavior and operational boundaries, not new
correctness defects requiring production correction. No material new defect was
found that invalidates the frozen financial/authentication behavior.

## 7. Backend, authentication and API robustness

`tests/test_backend.py` runs against SQLite and (through `LibsqlBackendTests`) the
real libSQL driver. Tests verify random distinct 64-hex challenges (not a statistical
entropy proof), domain/wallet/time message fields, exact EIP-191 verification,
browser-bound attempt, expiration, replay/wrong signer/altered message, conditional
single-use update including concurrent consumption, hashed server-session validation,
logout/revocation/expiry/tampered cookie and protected JSON APIs.

Origin checks, JSON/body bounds, CSRF logout and unsigned-transaction preparation,
wallet checksum/zero-address validation, malformed argument/action rejection,
production HTTPS/secret/secure-cookie configuration and absence of private-key
custody are reviewed/tested. User Log is deliberately independent and public, not
protected by wallet authentication. JSON APIs do not implement financial signing.

Deployment validation verifies chain/address/manifest, constructor inputs, source/
runtime metadata with immutable spans, canonical deployment receipts and wiring.
Historical classroom addresses cannot silently substitute. Wrong context/roles,
paused state, terminal participants and read/simulation failures fail closed.
Missing configuration and reader failures return structured unavailability, not
fabricated balances/roles/remittances. `/api/users/me` may return identity with an
explicit roles-unavailable object; Activity may return cached evidence and live_error.

Browser tests verify submitted hash retention/locked writes through receipt and
post-state outages, Check transaction retry without re-sign/resubmit, failed canonical
receipt unlock, and successful authoritative post-state before restoring normal
controls. These use controlled mocks; live owner-signed evidence is separate.

## 8. Database and activity index robustness

New `tests/test_iteration7_storage.py` runs the complete receipt fast-path (10),
bounded historical catch-up (9) and direct remittance discovery (12) tests through
real libSQL file connections, adding 31 tests. Two further tests check all six
support tables survive User Log deletion and names are parameterized/HTML-escaped,
each with both SQLite and libSQL. Existing auth suite is already driver-parametrized.

Verified scenarios: idempotent initialization/upserts, persistence on reopen,
transaction rollback, atomic multiple-event receipt failure, duplicate receipt/backfill
coexistence, canonical fields, participant/batched association, unrelated wallet
rejection and isolated receipt insertion leaving historical checkpoints unchanged.
SQLite/libSQL local-chain HTTP integration also decodes/indexes real local EVM events.
These are local driver compatibility proofs, not a repeat of remote-network durability;
the latter remains owner-verified 6B redeploy evidence.

Historical indexing is time/chunk bounded, RPC-deduplicated and reorg fenced. Only
completed validated chunks persist and advance checkpoints; incomplete chunks do
not. Progress for other completed chunks is allowed. Slow/failed RPC, malformed
logs/receipts and reorg reconciliation are exercised; historical catch-up can return
caught_up:false or structured live_error normally. Newly verified receipts use the
independent atomic fast-path; they do not claim historical completeness.

Direct remittance listing does not call index_events: verified count/records are
scanned newest-first, filtered by Sender/Recipient (Admin all), then paginated.
Empty/broken index therefore cannot replace or block financial contract truth.

## 9. Frontend, caching and mobile regression

The full browser suite covers wallet-signature API session/login/logout, rejected
connection/signatures, absent MetaMask, expiry/context changes, unavailable deployment
states, read-only history provenance/escaping, ten mocked actions, terminal post-state,
failed/rejected transactions and verification-only retry locks.
Snapshot reuse across server-rendered routes, deduplicated identical reads, ordinary
click/focus/navigation without full reload, explicit Refresh and account/chain/session/
deployment invalidation remain accepted and tested.

Three existing viewport tests exercise pages/navigation/forms at 360/768/1280 px.
Three added viewport tests populate verified-role financial pages and long Activity
hashes with incomplete-history provenance, check no page overflow, ordinary-role
Admin disablement and usable deposit input/control, without any wallet write.
Phone usability remains accepted **owner-observed 6B physical MetaMask evidence**.
Browser emulation is not claimed as a new physical test or full wallet-platform coverage.

## 10. Gas methodology and results

`node scripts/iteration7-contract-evaluation.cjs` executes exactly ten representative
successful direct transactions on a fresh deterministic chain and writes
`results/iteration7_gas.csv`. Scenarios/environment/ETH-transfer flags and transaction
hashes accompany gas used. Two fresh runs were byte-identical for the CSV and full
scenario JSON. These are reproducible samples, not population statistics.

| Action | Local gas used |
|---|---:|
| authorizeSender | 46,207 |
| authorizeRecipient | 46,217 |
| revokeRole | 24,514 |
| pause | 44,637 |
| unpause | 22,751 |
| deposit | 78,301 |
| withdraw | 54,459 |
| transfer | 285,988 |
| claim | 114,416 |
| cancel | 115,218 |

Lowest observed scenario: **unpause, 22,751**. Highest: **first transfer/create,
285,988**. Claim **114,416** and cancel **115,218** have distinct payout/accounting
work and refund effects; do not generalize their relative order across all states.

Supplemental read-only capture (2026-10-10T19:53:00.076424+00:00, head 11886748)
validated **16/16 existing Sepolia receipts**, covering all ten action types plus
additional 6A/6B samples, with canonical blocks/events and at least six confirmations.
`results/iteration7_sepolia_gas.json` stores actual receipt gas. No live value is
manufactured and no new receipt is generated by a write. Whole wrapper/batch gas
is explicitly not function-isolated; use local gas for controlled comparisons.
Detailed scenarios, every live hash/value and analysis are in `results/iteration7_gas.md`.

## 11. Gas optimization assessment

The implementation uses optimizer 200, immutable role/funding/Admin references,
keyed balances/reservations, small enums/flags and fixed-work financial actions.
Creation is expensive because it initializes multiple mappings/records and updates
owner/aggregate accounting across two contracts with two logs. Clearing permissions/
pause differs from initializing zero slots; payout does not alone determine gas.

Aggregate accounting, reservation identity, remittance storage and rich events have
intentional traceability/invariant costs. Boolean reentrancy guards are simple and
verified. Future/KIV packing/custom errors/guard alternatives or removing redundant
totals require benchmarking and safety review, not changes to the frozen deployment.
No claim of optimal gas or gas-related correctness defect is made. Gas units are not
fee/time guarantees; no fiat-rate or production financial suitability claim.

## 12. Assignment-area evidence mapping

This uses the frozen requirements retained in repository/integration materials;
it does not claim an independent re-read or change to the assignment brief.

| Assignment area | Iteration 7 evidence | Boundary |
|---|---|---|
| ≥3 interacting contracts / roles / security | Three-contract compile, ten-action matrix, trusted coordination, role/negative/adversarial review | Not a formal audit; accepted single Admin/I7-01 limits |
| ≥10 blockchain transaction types / MetaMask / traceability | ABI-count sanity, real historic receipts/events, wrapper association, UI mock preparation/signing boundary | No new live writes; deployment/setup/internal/read calls excluded |
| Testing/evaluation | 159 Python + 55 browser tests; 71 E7 cases; 48 model transitions; both local-chain DB paths | Focused deterministic samples, not exhaustive or representative usability research |
| Gas estimation/analysis | Ten controlled gas rows, existing 16-receipt supplement, unsigned preparation estimation tests | Wrapper overhead separated; no optimality/real-money claims |
| Backend REST / persistence / history | Auth/API validation, both drivers, atomic/index/checkpoint/direct-read tests, retained hosted durability | DB/index never financial authority; remote durability evidence from 6B |
| Responsive dashboard / mobile | 360/768/1280 browser tests and prior owner phone evidence | No new physical-device test/model details |
| Public cloud deployment | Accepted Render Live/Turso/hosted Sepolia lifecycle in 6B | No Iteration 7 Render config/deploy or authenticated production re-test |
| Report/diagrams/demo/manual/contributions | This reusable evidence artifact | Formal report/slides/submission materials untouched; completion assessed later |

## 13. Final regression results

| Suite/check | Final result |
|---|---|
| Solidity 0.8.34 compile | Three contracts, zero warnings, Shanghai optimizer 200 |
| Contract sanity | 10 groups / 50 expected rejections PASS |
| Role-boundary characterization | 8 assertions PASS under reviewed criterion; original prohibition retained as FAIL history |
| E7 functional/security/model/gas | 71 cases / 61 expected rejections / 952 assertions / 48 model transitions PASS; 10 gas rows; two byte-identical runs |
| Python/backend/db | 159 tests PASS (33 added) |
| Browser/frontend | 55 tests PASS (3 added), including 360/768/1280 px |
| SQLite local-chain HTTP | 14 assertions PASS; 12 canonical events, repeat indexing unchanged |
| libSQL local-chain HTTP | 14 assertions PASS; 12 canonical events, repeat indexing unchanged |
| Python dependency check | No broken requirements |
| git diff --check | PASS |

Ganache's native uWS binary does not match the current Node ABI; its JavaScript
fallback succeeds. This is an environment/tool warning, not a Solidity warning.
Controlled failure tests intentionally log a database exception while returning
sanitized 503 and asserting rollback; those logs do not indicate a failed suite.

## 14. Reproducibility

Use Python dependencies from requirements.txt, locked Node dependencies and the
existing Playwright/Chromium test setup. Set PYTHON to the test environment interpreter.
All DB tests use temporary files; do not point tests at production credentials.

```sh
npm run compile:contracts
npm run sanity:contracts
node scripts/iteration7-role-boundary.cjs
node scripts/iteration7-contract-evaluation.cjs
python -m unittest discover -s tests -p 'test_*.py' -q
NODE_PATH="$CODEX_PRIMARY_RUNTIME_NODE_MODULES" PYTHON=python CHROMIUM_EXECUTABLE_PATH=/tmp/sc6113-chromium node --test tests/frontend.cjs
PYTHON=python node tests/local-chain.cjs
LOCAL_DB_DRIVER=libsql PYTHON=python node tests/local-chain.cjs
python scripts/iteration7-read-gas.py https://ethereum-sepolia-rpc.publicnode.com
python scripts/iteration7-gas-summary.py
python -m pip check
git diff --check
```

The optional public read-only evaluation endpoint is not the Render RPC configuration.
No credentials are recorded. Historical endpoint availability may affect the optional
supplement; stored checked receipts retain their capture-time provenance.

## 15. Accepted limitations and final acceptance

Accepted boundaries: I7-01 ordinary/Admin overlap, single-Admin pause liveness,
public shared User Log, uncredited forced ETH, public-RPC interruptions, partial
historical catch-up, six-confirmation evidence policy, Render Free cold starts,
external-change/manual-refresh presentation caching and low-volume direct scanning.
No production financial suitability, representative user survey or scalability claim.

| Criterion | Status |
|---|---|
| Reviewed I7-01 policy recorded; history retained; Solidity untouched | PASS / accepted Low limitation |
| Ten distinct actions with positive/negative/event/live/gas evidence | PASS |
| Functional/accounting/callback/terminal/revocation/pause evaluation | PASS within tested scope |
| Manual security assessment, no identified Critical/High issue | PASS within review scope; not formal assurance |
| Backend/db/index/frontend regression | PASS |
| Complete ten-action reproducible gas evaluation | PASS |
| Evidence provenance and operational limitations explicit | PASS |
| No Sepolia writes/redeploy, schema/config/secret/address changes, main merge or Iteration 8 | PASS |

**ITERATION 7: APPROVED / FROZEN**
