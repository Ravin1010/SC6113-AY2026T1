# Iteration 7 — evaluation checkpoint: review required

## Scope and baseline

Base: `8c99477be903ed3885249ad91be17b103f5ab4bc` (accepted Iteration 6B freeze).
Branch: `feature/iteration-7-testing-security-gas`.
This checkpoint adds only a local characterization utility, its result, and this document.
No production source, Solidity, schema, addresses, configuration or historical evidence is changed.

**Iteration 7 is blocked on an acceptance-policy mismatch.** It is not a completed comprehensive security review or gas evaluation. The user's change policy requires documenting genuine defects/contradictions and stopping before changing frozen Solidity or architecture. Existing passing regressions do not resolve the new criterion below.

## Finding I7-01: Admin can authorize itself as Sender and Recipient

| Field | Finding |
|---|---|
| Severity | Low: role-separation policy mismatch |
| Component | `contracts/RoleRegistry.sol`, `authorizeSender` and `authorizeRecipient` |
| Required Iteration 7 criterion | “Admin cannot self-assign ordinary roles.” |
| Actual checks | Caller must equal immutable Admin; target must be nonzero and not already authorized. Neither function excludes `wallet == admin`. |
| Preconditions | Caller already controls the sole legitimate Admin wallet. An unprivileged caller cannot perform this action. |
| Evidence | `scripts/iteration7-role-boundary.cjs` successfully grants both ordinary permissions to the local deployer; both receipts succeed and getters return true. |
| Impact | Admin can also participate in ordinary Sender/Recipient activity. This does not create a second Admin, change Admin identity, bypass balance ownership, or establish a theft exploit. |
| Mitigations already present | `onlyAdmin`, immutable Admin identity, ordinary-role-only revocation enum; unauthorized authorization rejects. |
| Acceptance status | FAIL for the explicitly requested self-assignment prohibition. Not silently treated as an accepted limitation. |

The earlier implementation document (`docs/contracts/ITERATION_3.md`) describes immutable Admin authority and ordinary-role revocation, but does not specify a target-address exclusion. Iteration 6A's observed Admin having no ordinary roles describes that snapshot; it does not prove that self-assignment is impossible. These statements must not be conflated.

### Reproduction and interpretation

Run `node scripts/iteration7-role-boundary.cjs` from the repository root.
The utility compiles the exact frozen source with Solidity 0.8.34, optimizer 200,
Shanghai target and uses deterministic in-memory Ganache chain ID 31337.
It uses no external RPC or live signing keys. Eight characterization assertions
pass, establishing that the new acceptance criterion **fails**. Its zero exit status
means the reproduction behaved as asserted, not that the prohibition passed.
Machine-readable output: `results/iteration7_role_boundary.json`.

### Correction recommendation requiring review

Decide which policy is intended before resuming the comprehensive evaluation:

1. If Admin may hold ordinary permissions, explicitly amend the Iteration 7 criterion to require that only Admin can grant ordinary roles and ordinary roles cannot grant/change Admin authority. Keep the frozen deployment unchanged.
2. If strict Admin/ordinary-role separation is mandatory, both authorization functions need a target-not-Admin check. That changes frozen Solidity and would require a separately approved correction/deployment plan; it cannot be applied to the already deployed immutable contracts in this iteration.

No correction to production Solidity or architecture has been made. The finding is not labelled Critical/High, and no complete security verdict is claimed.

## Baseline transaction coverage retained, not newly expanded

The existing `scripts/sanity-contracts.cjs` tests all ten ABI actions and 50 expected
rejections, including pause, revocation exit rights, atomic payout rollback,
reentrancy callbacks, accounting and terminal states. Existing live evidence is
preserved in `deployment/live-smoke-evidence.json` and
`docs/integration/ITERATION_6A.md`; hosted evidence remains in
`docs/integration/ITERATION_6B.md`. None was regenerated using new Sepolia writes.

| Action | Initiator | Principal outcome/events | Existing baseline coverage | Iteration 7 assessment |
|---|---|---|---|---|
| authorizeSender | Admin | Sender permission; RoleAuthorized | Local sanity + historical 6A/6B | PARTIAL: I7-01 criterion fails |
| authorizeRecipient | Admin | Recipient permission; RoleAuthorized | Local sanity + historical 6A/6B | PARTIAL: I7-01 criterion fails |
| revokeRole | Admin | Selected ordinary role removed; RoleRevoked | Local sanity + historical 6A | Baseline PASS; expanded review deferred |
| pause | Admin | Full financial pause; SystemPaused | Local sanity + historical 6A | Baseline PASS; expanded review deferred |
| unpause | Admin | Financial actions resume; SystemUnpaused | Local sanity + historical 6A | Baseline PASS; expanded review deferred |
| deposit | Authorized Sender | Available credited from msg.value; FundsDeposited | Local sanity + historical 6A/6B | Baseline PASS; expanded review deferred |
| withdraw | Balance owner | Available debited, owner paid; FundsWithdrawn | Local sanity + historical 6A | Baseline PASS; expanded review deferred |
| transfer | Authorized Sender | PENDING remittance, exact reservation; FundsReserved + RemittanceCreated | Local sanity + historical 6A/6B | Baseline PASS; expanded review deferred |
| claim | Recorded Recipient | COMPLETED, payout; ReservedFundsReleased + RemittanceClaimed | Local sanity + historical 6A/6B | Baseline PASS; expanded review deferred |
| cancel | Recorded Sender | CANCELLED, available restored; ReservedFundsUnlocked + RemittanceCancelled | Local sanity + historical 6A | Baseline PASS; expanded review deferred |

This is a checkpoint summary, not the final requested precondition/negative/gas matrix.
Deployment/wiring, reads and internal calls are excluded from the ten-action count.
Gas measurement, optimization assessment, full security findings and rubric mapping
remain uncompleted at the required review stop; no gas numbers are invented.

## Regression evidence

The complete existing regression suite was rerun without production modifications.
Tests use isolated local databases, controlled mocks and local EVM instances.
They do not mutate production Turso or submit Sepolia transactions.

| Check | Result |
|---|---|
| Solidity 0.8.34 compile | 3 application contracts; zero warnings |
| Contract sanity | 10 groups; 50 expected rejection checks PASS |
| New Admin-policy characterization | 8 assertions PASS; required self-assignment prohibition FAIL |
| Python | 126 tests PASS |
| Browser/frontend | 52 tests PASS; includes 360/768/1280 px responsive cases |
| SQLite local-chain HTTP integration | 14 assertions PASS; 12 canonical events, repeat indexing unchanged |
| libSQL local-chain HTTP integration | 14 assertions PASS; 12 canonical events, repeat indexing unchanged |
| Python dependency check | No broken requirements |
| git diff --check | PASS |

Ganache reports that its native uWS binary does not match the installed Node ABI;
it successfully uses the JavaScript fallback. This is a test-tool warning.

### Existing robustness evidence

Python tests cover browser-bound unpredictable expiring single-use nonces, EIP-191
signature recovery, wrong signer/message, concurrent nonce consumption, sessions,
logout/CSRF, malformed inputs, production fail-closed configuration, deployment
verification, reorgs, budgeted indexing, atomic/idempotent receipt insertion,
participant scoping and direct authoritative remittance discovery.
SQLite/libSQL tests cover initialization, transactions/rollback, upserts, reopen
persistence and User Log deletion isolation. Browser tests cover cache reuse and
context invalidation, pending transaction locks, verification-only retry without
resubmission, definitive failed receipts and authoritative post-state refresh.
These baseline passes are not a claim of exhaustive security assurance.

Physical phone/MetaMask usability remains **owner-observed Iteration 6B evidence**;
no physical-device test or additional mobile blockchain write occurred here.
No new production/chain verification is claimed in this checkpoint.
Blockchain remains financial authority; Turso history and browser snapshots remain
non-authoritative. Existing public-RPC interruptions, incomplete backfill, six
confirmations, Render cold starts and low-volume direct scanning limitations remain.

## Reproducibility

Use the existing Python environment installed from `requirements.txt` and Node
dependencies from the lockfile. Browser tests require the existing Playwright and
Chromium test setup described in the frontend/integration documentation.

```sh
npm run compile:contracts
npm run sanity:contracts
node scripts/iteration7-role-boundary.cjs
python -m unittest discover -s tests -p 'test_*.py' -q
NODE_PATH="$CODEX_PRIMARY_RUNTIME_NODE_MODULES" PYTHON=python CHROMIUM_EXECUTABLE_PATH=/tmp/sc6113-chromium node --test tests/frontend.cjs
PYTHON=python node tests/local-chain.cjs
LOCAL_DB_DRIVER=libsql PYTHON=python node tests/local-chain.cjs
python -m pip check
git diff --check
```

## Acceptance and scope

- Accepted 6B commit is the exact branch base: PASS.
- Production runtime, frozen Solidity, schema and manifest unchanged: PASS.
- No new Sepolia writes/deployment, Render configuration/secret change, main merge,
  formal report/slides/Drive work or Iteration 8: PASS.
- Admin self-assignment prohibition: FAIL; review required.
- Full Iteration 7 expanded matrix, gas artifacts and comprehensive assessment:
  NOT COMPLETED, stopped at the policy contradiction.

**ITERATION 7: BLOCKED**
