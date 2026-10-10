# Iteration 6A — verified Sepolia integration

Base: `6dca6f3424d2c6ef929c186204df799904d96fbf` (Iteration 5).
Branch: `feature/iteration-6a-sepolia-integration`.
Frozen contracts remain byte-for-byte unchanged from Iteration 3
`313a82a8514624efd9351f3d45180447ae6b966d`.

Status: **Completed live smoke test accepted; final integration verification passed**.
Actual public addresses/hashes/blocks/source status are in `deployment/sepolia.json`.
`deployment/post-wiring-verification.json` records successful strict verification
and a read-only second-wiring revert. Completed smoke evidence is preserved in
`deployment/live-smoke-evidence.json`; the user authorized final commit/push after
accepting the corrected integration package on 10 October 2026.
Never use historical classroom addresses.

## Verified deployment observations

Sourcify exact-match and Blockscout verified source were independently retrieved
for all three contracts. Published source contents equal accepted files byte-for-byte;
compiler 0.8.34, optimizer enabled/200, Shanghai match. Actual Remix virtual source
paths are `contracts/contracts/...`, rather than `contracts/...`. This changes only
metadata. `scripts/reproduce-remix-build.cjs` reproduces the deployed path mapping
from unchanged sources/settings; `deployment/remix-build.json` and
`deployment/remix-compiler-input.json` permit strict full comparison, retaining
metadata and masking only compiler-declared immutable spans. The manifest explicitly
selects this supported source-path mapping. No arbitrary artifact path or
verification-override flag is accepted. ABIs and Solidity architecture are unchanged.

Wiring transaction 0xa2b051bc68857ee471c8bf22d127907e903d69e79b70c40ec3426201b98a54c4
at block 11884306 uses wallet batching. Its top-level destination is not funding;
verification therefore requires the canonical receipt, Admin initiator, zero value,
correct deployment block, and exactly one decoded RemittanceContractConfigured event
emitted by verified deposit_money with correct Admin/paynow values. Final getter
and read-only repeat-call revert complete the proof. Receipt API supports verified
contract events inside wallet batches while retaining wallet/Admin scope checks.

The completed smoke test is documented below.
`docs/integration/MANUAL_SEPOLIA_SMOKE_TEST.md` retains the reproduction guide.
The earlier automated read checks are historical pre-smoke evidence; they do not
claim actual wallet authentication or financial transaction submission.

## Original Checkpoint 1 deployment instructions (completed)


Import these exact files into the Remix workspace root, preserving paths:

- `contracts/RoleRegistry.sol`
- `contracts/deposit_money.sol`
- `contracts/transfer_money.sol`

Use Solidity **0.8.34+commit.80d5c536**, optimizer **enabled**, **200** runs,
EVM **Shanghai**. Keep default compiler metadata settings; do not flatten files,
rename paths, change sources, enable viaIR or substitute another compiler.
`deployment/compiler-input.json` is the exact standard JSON compilation input.
`deployment/accepted-build.json` includes compiler, settings, source hashes,
creation/runtime bytecode and compiler-declared immutable references.
`static/abi/*.json` contains exactly the accepted three ABIs.
Rebuild with `npm ci` then `node scripts/prepare-deployment.cjs`.

In Remix Deploy & Run select the injected MetaMask provider and explicitly confirm
**Sepolia, chain 11155111 (0xaa36a7)** and your chosen public Admin address.
Keep deployment Value **0 wei**. Sign each deployment manually in MetaMask:

| Order | Selected contract | Constructor arguments |
|---|---|---|
| 1 | `RoleRegistry` | None; deployer becomes immutable sole Admin |
| 2 | `deposit_money` | Actual RoleRegistry address |
| 3 | `paynow` from `transfer_money.sol` | Actual RoleRegistry address, actual deposit_money address |

Use the same Admin account for all three deployments. Record each contract's
public address, deployment transaction hash and explorer link. Never share keys
or seed phrases. Wait for successful receipts, preferably six confirmations.

**DO NOT CALL `setRemittanceContract` YET.** Return the seven public values
(Admin address, three contract addresses and three deployment transaction hashes)
and source-verification status/links. Independent checks precede permanent wiring.

### Publish/verify source

Use Remix's **Contract Verification** plugin: choose Sepolia, the compiled
contract and its deployed address; enter the exact constructor arguments. Try
Sourcify or an available Sepolia explorer service. If Etherscan requires an API
key, enter it privately in Remix's settings; do not put it in the repository or
send it to Work. Preserve verification receipts and public source links.

Alternatively upload `deployment/compiler-input.json` as Solidity standard JSON
input in Sepolia explorer verification, selecting the same compiler. Fully
qualified names are `contracts/RoleRegistry.sol:RoleRegistry`,
`contracts/deposit_money.sol:deposit_money` and
`contracts/transfer_money.sol:paynow`. Constructor argument bytes must correspond
to the actual public addresses (one address for deposit_money; two for paynow).
Report verification failures rather than changing sources/settings to force a match.

Official references checked for this preparation:
https://remix-ide.readthedocs.io/en/latest/contract_verification.html
https://docs.etherscan.io/api-reference/endpoint/verifysourcecode

## Evidence/configuration after the user returns actual data

The public manifest was filled only after the user supplied actual deployment data. Its eventual JSON shape:
`chainId` integer; `deploymentId` unique string; `admin` actual public address;
`contracts` object keyed by RoleRegistry/deposit_money/paynow, each with actual
`address`, `transactionHash`, and integer `blockNumber`. Optional explorer/source
links are evidence notes, never substitutes for programmatic verification.

Set the six public network/address/deployment environment fields documented in
`.env.example`, and `BLOCKCHAIN_MANIFEST_PATH` to that actual evidence file.
RPC URLs can contain provider tokens: do not commit or print such tokens.
Use a new deployment identifier for a different contract set; indexes are scoped
by chain and deployment. SQLite remains local application-support storage.

### Verification policy and Checkpoint 2

`backend/blockchain.py` verifies every request at a fixed block snapshot:
Sepolia chain, source hashes/compiler/settings, nonempty exact runtime code after
masking only solc's declared immutable ranges, exact creation transaction input
plus ABI-encoded constructor arguments, deployer, successful canonical receipt,
actual deployment block, immutable Admin and all registry/funding references.
Unmasked runtime bytes including metadata must match. Immutable values are also
verified through constructors/getters. No environment verification flag bypasses
these checks. A change/reorg/RPC failure disables actions.

Before wiring run `python scripts/verify-deployment.py --phase pre-wiring`.
It additionally requires trusted remittance unset, unpaused registry and count 0.
If any critical check fails, stop. Only after independent pre-wiring verification
and the user's Checkpoint 2 should the user manually sign the single Remix call
`deposit_money.setRemittanceContract(actualPaynowAddress)`. Return its public hash.
No frontend action or backend endpoint performs this setup.

After the user returns that hash, run
`python scripts/verify-deployment.py --phase post-wiring --wiring-tx ACTUAL_HASH`.
It verifies the transaction and permanent reference, and simulates repeated wiring
using read-only `eth_call`, expecting `Already configured`. Never send a second
wiring transaction. No live verification is claimed before these steps occur.

## Non-custodial backend and frontend

Web3.py **7.14.0** supplies maintained ABI encoding, reads, receipt access, event
parsing, simulation and gas estimation. Flask owns no wallet/signing keys.
Existing nonce/message/session/CSRF authentication remains unchanged.

| API | Responsibility |
|---|---|
| GET `/api/users/me` | Application metadata plus independently verified roles/Admin/pause; structured unavailable roles otherwise |
| GET `/api/users/me/balances` | Live available/reserved amounts in decimal wei strings and formatted test ETH |
| GET `/api/users/roles/<address>` | Validated address, live ordinary-role checks; no UI self-assignment |
| GET `/api/remittances` | Wallet IDs discovered through confirmed events; each record reread from contract |
| GET `/api/remittances/<id>` | Live record for participant or on-chain Admin; preserves exit rights after revocation |
| GET `/api/transactions` | Wallet-scoped non-authoritative event/receipt index with indexing/live-check provenance |
| GET `/api/transactions/audit` | On-chain Admin-only indexed activity |
| GET `/api/transactions/<hash>/receipt` | Actual RPC receipt/canonicality/confirmation data for this deployment and initiating/event-associated wallet/Admin |
| POST `/api/transactions/prepare` | Session + CSRF; validates one of ten actions; simulates/estimates and returns an **unsigned** transaction only |

The unsigned preparation whitelist is exactly authorizeSender, authorizeRecipient,
revokeRole, pause, unpause, deposit, withdraw, transfer, claim, cancel. One-time
wiring/internal funding operations are excluded. Authoritative contracts still
validate every transaction. All UI writes require verified permanent wiring,
authenticated/connected wallet match, Sepolia and eligibility. Exit rights use
recorded ownership/participant identity rather than retained roles. Full pause
blocks all five financial actions, leaving eligible Admin role controls/unpause.

The browser uses `eth_sendTransaction` **only after an explicit user button click**
and a fresh session/chain/account/verified-address check. MetaMask presents the
transaction for user review and signing. Deposit uses native ETH `value`; other
actions use zero value. Calldata comes from maintained Web3 ABI encoding. Gas has
a 20% estimate margin; this is transaction preparation, not gas benchmarking.
The UI displays submitted hashes as pending until actual canonical receipts have
six confirmations; failures/rejections are explicit. A pending hash is not success.
Unsupported network switching is never automatic; the user can request Sepolia.

## Event indexing/reconciliation

All 13 frozen event types are decoded from verified contract ABIs. Each contract
starts at its actual deployment block. On-demand reads process at most 5,000 blocks
per contract per request, in 500-block chunks. A six-confirmation policy excludes
recent unconfirmed events. Lists explicitly report discovery/catch-up limitations;
ID lookup and balances always use current verified contract state.

The index stores chain/deployment scope, actual tx/hash/block/log identifiers,
participant addresses, decoded event arguments and actual transaction initiator.
Composite keys and upserts make reruns idempotent. Stored checkpoint block hashes
are compared with RPC canonical hashes; an orphaned checkpoint clears only that
deployment's cache and replays from deployment. Each event/receipt and chunk hash
is checked, including a final verification-snapshot check. Inconsistent updates
roll back atomically. This simple coursework policy is not a production indexer.
Historical cached data remains clearly labelled when live reads are unavailable;
SQLite never determines balances or remittance status.

## Focused verification commands

Install Python requirements in an isolated environment. Existing Node dependencies
remain unchanged; Playwright is needed only to execute browser tests.

```
npm run compile:contracts
npm run sanity:contracts
python -m unittest discover -s tests -p 'test_*.py' -v
PYTHON=python node tests/local-chain.cjs
PYTHON=python CHROMIUM_EXECUTABLE_PATH=/path/to/chromium node --test tests/frontend.cjs
```

Offline reader/indexer/API tests use clearly identified public fixture addresses;
browser tests mock wallet submission without sending any transactions. The local
HTTP integration uses an ephemeral Ganache EVM and its local test accounts, never
Sepolia/user wallets. Existing 360/768/1280px checks remain; live hash/status cards
also exercise 360px layout. Existing manual live evidence is now preserved below.

## Completed evidence and exclusions

The user completed and accepted manual smoke testing. Existing signed transactions
were independently recovered through verified contract events and canonical receipts,
without sending any further transactions. The full evidence file includes hashes,
outer sender/target, block hashes, log IDs, event arguments, confirmations, terminal
state and index correspondence. UI observations are user-reported; the read-only
evidence script proves blockchain outcomes, not an automated MetaMask/browser run.

Iteration 6B remains Turso integration/Render hosting and applicable deployment
work. No provider was provisioned/integrated, no Render setting/deployment changed,
no main merge occurred, and formal report/slides/Drive were not edited. Comprehensive
security/gas analysis and physical-phone evaluation remain later phases.

## Automated verification results

- solc 0.8.34+commit.80d5c536: all three contracts compile; zero Solidity warnings.
- Existing contract sanity suite: 10 groups and 50 expected rejection checks pass.
- Python authentication/database/reader/indexer/live-API suite: 63/63 pass.
- Chromium browser suite: 40/40 pass, including all ten wallet-write paths
  with explicit mocks and mobile/tablet/desktop layout checks.
- Ephemeral local HTTP integration: 8 assertions pass; 12 canonical events
  indexed; repeat indexing creates no duplicates. No Sepolia transactions.
- Dependency check and git whitespace check pass. Ganache uses its supported
  JavaScript fallback because the optional native uWS binary is unavailable.
- Solidity source diff against accepted Iteration 3 is empty; runtime user.db
  SHA256 remains 108de2caedd2c73374229f955de1e183387590b1031d05b242b03d386dbfe7cb.
- Live deployment/source/wiring and completed financial smoke receipts were
  independently verified; all ten action types are covered by canonical events.
- Finalization is authorized on the Iteration 6A feature branch only; main remains
  the accepted classroom baseline. No new financial transactions were sent.

## Post-wiring live read validation

`deployment/live-read-validation.json` records 9 passed live API/preparation checks
using isolated server-session fixtures, no actual MetaMask login, no keys, and zero
blockchain writes. Roles/Admin, balances, remittance list, transaction history,
canonical wiring receipt, audit and address role reads match verified contract/RPC
state. One actual wiring event was indexed; repeat indexing produced no duplicates.
Unsigned authorization simulation/calldata preparation succeeded without broadcasting.
An earlier run passed six routes and stopped at a transient reader-unavailable
response; the rerun completed with no transient failures. Provider availability is
therefore an operational limitation; failures remain explicit and fail closed.

Latest regression counts: 63 Python tests, 40 browser tests, 10 Solidity sanity
groups (50 expected rejections) and 8 local HTTP assertions all passed. Solidity
compilation/reproduction has no warnings. User.db and frozen sources are unchanged.
The separate manual smoke-test guide remains a reproduction reference; its
checkpoint is completed and accepted. Existing user-signed financial lifecycle
evidence is recorded below. No Iteration 6B or Render/Turso/main/report/slides/Drive
work occurred. No extra live transactions are required for the accepted corrections.

## Narrow post-smoke corrections

Receipt access accepts the signing wallet or a participant identified in ABI-decoded
logs emitted by the verified deployment contracts. This supports MetaMask wrapper/
batched transactions even when the outer transaction sender is a relayer. Arbitrary
wrapper transactions and logs from other deployments do not establish association.

Frontend session and verified deployment context remain in memory until wallet,
network/session changes or explicit refresh. Focus and browser-history restoration
check the session only. Ordinary clicks and section links do not reload chain state.
Full page navigation initializes only data needed by that page. Concurrent identical
GETs share an in-flight request; role/ID eligibility lookups additionally share a
30-second in-memory cache, cleared on context changes or affected transactions.
Transaction preparation always rechecks current contract state on the server.

After confirmed deposit/withdraw, refresh wallet funding state. After create/claim/
cancel, refresh funding state and displayed remittance records, including the selected
ID; terminal claim/cancel buttons become disabled. Role changes invalidate the target
role lookup and refresh own identity only when affected. Pause/unpause refresh shared
pause state. Indexed history refreshes after confirmed actions when displayed. Failed
or rejected actions do not force a complete reload. No loading-flash work or separate
completion-flow redesign is included.

## Completed live smoke evidence

Read-only recovery snapshot: Sepolia block **11885470**,
block hash `0x2b743771bfd9f194325995576257b54ec473b70e786571667072140a2040f583`. All receipts succeeded, remain
canonical and have at least six confirmations. Source/immutable references were
verified before collecting events. The recovery/indexing run sent **zero**
blockchain transactions and used an isolated temporary database.

| Wallet | Address | Final permissions |
|---|---|---|
| Admin / Auditor | `0x4A779fA7d5eA106f1aDFB8369e65fCAA465ca7Fd` | Sole Admin; no ordinary roles |
| Sender | `0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a` | Sender permission revoked |
| Recipient | `0x890F63435Cf6F4D526F7062A282A94c74A50cFa3` | Sender and Recipient independently authorized |

The Recipient also received Sender authorization before Recipient authorization.
This is preserved as observed evidence; dual permissions are explicitly allowed.
Actual deposits were **0.001 + 0.002 test ETH**, rather than one 0.003 deposit.
Both remittances were **0.001 test ETH**. No evidence has been rewritten to fit the
illustrative guide sequence.

| Block | Action | Actual transaction hash |
|---|---|---|
| 11884306 | One-time wiring (excluded from count) | `0xa2b051bc68857ee471c8bf22d127907e903d69e79b70c40ec3426201b98a54c4` |
| 11884606 | authorizeSender | `0x435c01292070c2c4973fb6f04d38fd592e0a89c8ba532a418f90d8f67efee599` |
| 11884646 | authorizeSender | `0xe8d18bc3971b16c1d98dc31a9ae7ba8a58eec1868e2fd36222c57d801caee1f6` |
| 11884670 | authorizeRecipient | `0xe90e29d163dda3503e1cdefdf3331e2f49d074e5e68756f489519ea2c4821564` |
| 11884741 | deposit | `0xc7e5eafd2f395a59805f992f7a55dc3c2231d79193cd2f0e16b9e48d0f6c2858` |
| 11884851 | transfer | `0x3ae3b35001cdf73c9a3540a9af0087300afb23600901eaa93f148c716b652ff6` |
| 11884976 | claim | `0xbca164391f46a2955e91465f1663964245743d6572425ab520d80c992aaa13e5` |
| 11885039 | deposit | `0xa7dffefd79d3ea3af0361583e7da7eae4120dfd56fb2c78316d5c6c6d6ea690f` |
| 11885065 | transfer | `0xf85c90d72c58c164ade7b264a29b6880b1c7be97099f47849f57c4143dec5db1` |
| 11885102 | revokeRole | `0xe9a297cd30bca10c31a68b88ecca477319bce908d4545d93b64d5f4d158dac83` |
| 11885128 | cancel | `0xf4b5220faab62424594ad36bdfc9092e7341149a66d663d4db0abb062ffaa580` |
| 11885160 | withdraw | `0xbe8040bc5c08dd3a8be9548a7ebd3b5ea285ddba1fdcbc1e1ddf646ebeeffcd2` |
| 11885184 | pause | `0x424e7ea47c58a084d0bec781824d350bc1a816579301ab088927f9adc7aac766` |
| 11885253 | unpause | `0x1fb6c70f0e4f0952700bd2f6397b0ef1c3df604ee3019e2a1b30a6312192be99` |

**Results:** 13 user/Admin transactions cover exactly ten distinct action types;
one additional wiring transaction is excluded. Remittance **#1 = COMPLETED**,
**#2 = CANCELLED**; both reservations are inactive. Cancellation and withdrawal
occurred after Sender-role revocation, proving retained exit rights. Final Sender
available balance is **0.001 test ETH**, reserved **0**; the system is **unpaused**.
Financial identity/status/balance state remains contract-authoritative.

The index contains **14 transactions and 18 events**, including wiring; a repeated
index run leaves both counts unchanged. All batch/wrapper receipts are tied to
events emitted by the verified deployment contracts. Original deployment and
pre-smoke read evidence are retained unchanged as historical snapshots.

`scripts/read-smoke-evidence.py` reproduces this read-only collection when
`BLOCKCHAIN_RPC_URL` is set. It must never sign or broadcast. Full canonical receipt
and event details are in `deployment/live-smoke-evidence.json`.
