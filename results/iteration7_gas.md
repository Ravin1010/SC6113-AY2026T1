# Iteration 7 gas evaluation

Local measurements: Solidity 0.8.34, optimizer enabled/200 runs, Shanghai EVM, Ganache 7.9.2, deterministic wallets, chain ID 31337. Frozen source is unchanged. Each row is one successful direct transaction in the specified state; deployment, wiring and internal calls are excluded.

Two independent fresh in-memory runs produced byte-identical local CSV and evaluation JSON. This demonstrates reproducibility for these scenarios, not a statistical sample of production gas.

| Action | Contract | Gas used | ETH transfer | Scenario |
|---|---|---:|---|---|
| authorizeSender | RoleRegistry | 46,207 | No | First grant to ordinary Sender |
| authorizeRecipient | RoleRegistry | 46,217 | No | First grant to ordinary Recipient |
| revokeRole | RoleRegistry | 24,514 | No | Revoke Sender wallet Recipient permission; Sender remains |
| pause | RoleRegistry | 44,637 | No | False to true |
| unpause | RoleRegistry | 22,751 | No | True to false |
| deposit | deposit_money | 78,301 | Yes | First deposit, 0.005 ETH, zero prior balance |
| withdraw | deposit_money | 54,459 | Yes | Partial withdrawal 0.001 ETH; remaining availability |
| transfer | paynow | 285,988 | No | First remittance ID, 0.001 ETH, new reservation storage |
| claim | paynow | 114,416 | Yes | Claim 0.001 ETH after Recipient revocation |
| cancel | paynow | 115,218 | No | Cancel pending 0.001 ETH after Sender revocation; available nonzero |

Creation reserves funds already held in funding: it sends no new ETH. Claim and withdraw send ETH out; deposit sends ETH in. Cancel unlocks accounting only.

## Interpretation

- **Highest:** transfer/create (285,988): first remittance ID increments the counter and initializes parties/amount/status and a separate reservation, changes available/reserved owner and aggregate totals, performs cross-contract checks and emits two events.
- **Lowest:** unpause (22,751): clears the shared flag with a log. Clearing an occupied slot differs from pause (44,637), which sets it; refunds and initial slot values affect observed gas.
- New Sender/Recipient grants (~46k) write independent permission mappings and emit RoleAuthorized. Revocation (24,514) clears an existing permission.
- First deposit (78,301) changes owner/aggregate availability. Withdrawal (54,459) debits two balances and makes an ETH call; measured withdrawal leaves a nonzero balance.
- Claim (114,416) and cancel (115,218) both transition lifecycle and reservation state and emit two events. Claim performs a payout; cancellation restores available accounting. Their ordering is scenario-specific: state slots/refunds matter, so ETH transfer alone does not predict which costs more.

## Existing Sepolia receipts — supplementary, not directly comparable

Read-only capture: 2026-10-10T19:53:00.076424+00:00; head 11886748. Chain ID 11155111, six or more confirmations and canonical block hashes checked. These are existing transactions, not new writes.

Whole outer-transaction gas is reported below. Wallet wrappers/batches can include signature verification, wallet execution and other overhead; direct deposits also have different prior storage conditions. No call trace was collected to isolate overhead. Do not attribute the entire live/local difference to the Solidity functions.

| Action | Evidence | Outer gas used | Existing transaction hash |
|---|---|---:|---|
| authorizeSender | Iteration 6A historical smoke | 307,581 | `0x435c01292070c2c4973fb6f04d38fd592e0a89c8ba532a418f90d8f67efee599` |
| authorizeSender | Iteration 6A historical smoke | 307,581 | `0xe8d18bc3971b16c1d98dc31a9ae7ba8a58eec1868e2fd36222c57d801caee1f6` |
| authorizeRecipient | Iteration 6A historical smoke | 307,603 | `0xe90e29d163dda3503e1cdefdf3331e2f49d074e5e68756f489519ea2c4821564` |
| deposit | Iteration 6A historical smoke | 254,416 | `0xc7e5eafd2f395a59805f992f7a55dc3c2231d79193cd2f0e16b9e48d0f6c2858` |
| transfer | Iteration 6A historical smoke | 1,331,593 | `0x3ae3b35001cdf73c9a3540a9af0087300afb23600901eaa93f148c716b652ff6` |
| claim | Iteration 6A historical smoke | 354,689 | `0xbca164391f46a2955e91465f1663964245743d6572425ab520d80c992aaa13e5` |
| deposit | Iteration 6A historical smoke | 254,416 | `0xa7dffefd79d3ea3af0361583e7da7eae4120dfd56fb2c78316d5c6c6d6ea690f` |
| transfer | Iteration 6A historical smoke | 1,256,905 | `0xf85c90d72c58c164ade7b264a29b6880b1c7be97099f47849f57c4143dec5db1` |
| revokeRole | Iteration 6A historical smoke | 198,280 | `0xe9a297cd30bca10c31a68b88ecca477319bce908d4545d93b64d5f4d158dac83` |
| cancel | Iteration 6A historical smoke | 367,648 | `0xf4b5220faab62424594ad36bdfc9092e7341149a66d663d4db0abb062ffaa580` |
| withdraw | Iteration 6A historical smoke | 238,794 | `0xbe8040bc5c08dd3a8be9548a7ebd3b5ea285ddba1fdcbc1e1ddf646ebeeffcd2` |
| pause | Iteration 6A historical smoke | 305,981 | `0x424e7ea47c58a084d0bec781824d350bc1a816579301ab088927f9adc7aac766` |
| unpause | Iteration 6A historical smoke | 196,483 | `0x1fb6c70f0e4f0952700bd2f6397b0ef1c3df604ee3019e2a1b30a6312192be99` |
| deposit | Iteration 6B hosted | 58,576 | `0xfdb959d34b7f4ba6e82d0030f067fb9f5e36c3c7c18ced763c8a3441b02e2d28` |
| transfer | Iteration 6B hosted | 1,256,905 | `0x2f2d2ba058d5ca56ad4d18fc1fdc2a2d2bb90fd2ced22dbd189b267a6bbc69ba` |
| claim | Iteration 6B hosted | 354,701 | `0x23fd98f2e04e8f7b47eae0117a25935c6b90b618a560f4de81de57614b02a73c` |

## Optimization assessment (no Solidity change)

Existing choices: compiler optimizer 200; immutable registry/funding/Admin references; compact enum/boolean state; direct keyed lookups; no on-chain enumeration loop; bounded work per financial transaction; fixed trusted remittance wiring; separate events for later indexing. Read-only getters are not counted as transactions.

The funding contract intentionally stores per-owner and aggregate accounting, reservation participants and amount, in addition to remittance records. These redundant checks/state improve traceability and invariants at a storage cost. Events also duplicate some identity information for index consumers; removing them solely for gas would weaken frozen evidence responsibilities.

KIV only: benchmark packed storage alternatives, whether both aggregate totals are necessary, custom errors instead of revert strings, and alternative guard implementations under a separately selected EVM. These may affect safety, deployed bytecode or integration and do not justify reopening this deployment. The current boolean guards are straightforward and have callback rejection/rollback tests.

No gas-related correctness/DoS defect was found in the fixed-work financial actions reviewed. Off-chain direct remittance discovery is linear and accepted only for the low-volume MVP.

Gas units are not ETH costs: fees depend on gas price and network conditions. No fiat conversion, real settlement claim, optimum claim or production benchmark is made.

## Reproduce

```sh
node scripts/iteration7-contract-evaluation.cjs
python scripts/iteration7-read-gas.py https://ethereum-sepolia-rpc.publicnode.com
python scripts/iteration7-gas-summary.py
```

The optional public endpoint above is a read-only evaluation transport, not a change to Render RPC configuration. Endpoint credentials are never written to results. CSV contains local measurements only; supplemental live observations are in iteration7_sepolia_gas.json.
