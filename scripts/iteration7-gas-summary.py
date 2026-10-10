"""Render measured local CSV and separately checked historical receipt observations."""
import csv
import json
from pathlib import Path
root = Path(__file__).resolve().parent.parent
rows = list(csv.DictReader((root / 'results/iteration7_gas.csv').open()))
live = json.loads((root / 'results/iteration7_sepolia_gas.json').read_text())
lines = ['# Iteration 7 gas evaluation', '',
    'Local measurements: Solidity 0.8.34, optimizer enabled/200 runs, Shanghai EVM, Ganache 7.9.2, deterministic wallets, chain ID 31337. Frozen source is unchanged. Each row is one successful direct transaction in the specified state; deployment, wiring and internal calls are excluded.', '',
    'Two independent fresh in-memory runs produced byte-identical local CSV and evaluation JSON. This demonstrates reproducibility for these scenarios, not a statistical sample of production gas.', '',
    '| Action | Contract | Gas used | ETH transfer | Scenario |', '|---|---|---:|---|---|']
for r in rows:
    lines.append(f"| {r['action']} | {r['contract']} | {int(r['gas_used']):,} | {'Yes' if r['eth_value_transfer']=='true' else 'No'} | {r['scenario']} |")
lines += ['', 'Creation reserves funds already held in funding: it sends no new ETH. Claim and withdraw send ETH out; deposit sends ETH in. Cancel unlocks accounting only.', '',
    '## Interpretation', '',
    '- **Highest:** transfer/create (285,988): first remittance ID increments the counter and initializes parties/amount/status and a separate reservation, changes available/reserved owner and aggregate totals, performs cross-contract checks and emits two events.',
    '- **Lowest:** unpause (22,751): clears the shared flag with a log. Clearing an occupied slot differs from pause (44,637), which sets it; refunds and initial slot values affect observed gas.',
    '- New Sender/Recipient grants (~46k) write independent permission mappings and emit RoleAuthorized. Revocation (24,514) clears an existing permission.',
    '- First deposit (78,301) changes owner/aggregate availability. Withdrawal (54,459) debits two balances and makes an ETH call; measured withdrawal leaves a nonzero balance.',
    '- Claim (114,416) and cancel (115,218) both transition lifecycle and reservation state and emit two events. Claim performs a payout; cancellation restores available accounting. Their ordering is scenario-specific: state slots/refunds matter, so ETH transfer alone does not predict which costs more.', '',
    '## Existing Sepolia receipts — supplementary, not directly comparable', '',
    f"Read-only capture: {live['captured_at_utc']}; head {live['snapshot_head']}. Chain ID 11155111, six or more confirmations and canonical block hashes checked. These are existing transactions, not new writes.", '',
    'Whole outer-transaction gas is reported below. Wallet wrappers/batches can include signature verification, wallet execution and other overhead; direct deposits also have different prior storage conditions. No call trace was collected to isolate overhead. Do not attribute the entire live/local difference to the Solidity functions.', '',
    '| Action | Evidence | Outer gas used | Existing transaction hash |', '|---|---|---:|---|']
for r in live['records']:
    lines.append(f"| {r['action']} | {r.get('evidence','Read unavailable')} | {format(r['gas_used'], ',') if 'gas_used' in r else 'Unavailable'} | `{r['transaction_hash']}` |")
lines += ['', '## Optimization assessment (no Solidity change)', '',
    'Existing choices: compiler optimizer 200; immutable registry/funding/Admin references; compact enum/boolean state; direct keyed lookups; no on-chain enumeration loop; bounded work per financial transaction; fixed trusted remittance wiring; separate events for later indexing. Read-only getters are not counted as transactions.', '',
    'The funding contract intentionally stores per-owner and aggregate accounting, reservation participants and amount, in addition to remittance records. These redundant checks/state improve traceability and invariants at a storage cost. Events also duplicate some identity information for index consumers; removing them solely for gas would weaken frozen evidence responsibilities.', '',
    'KIV only: benchmark packed storage alternatives, whether both aggregate totals are necessary, custom errors instead of revert strings, and alternative guard implementations under a separately selected EVM. These may affect safety, deployed bytecode or integration and do not justify reopening this deployment. The current boolean guards are straightforward and have callback rejection/rollback tests.', '',
    'No gas-related correctness/DoS defect was found in the fixed-work financial actions reviewed. Off-chain direct remittance discovery is linear and accepted only for the low-volume MVP.', '',
    'Gas units are not ETH costs: fees depend on gas price and network conditions. No fiat conversion, real settlement claim, optimum claim or production benchmark is made.', '',
    '## Reproduce', '', '```sh', 'node scripts/iteration7-contract-evaluation.cjs',
    'python scripts/iteration7-read-gas.py https://ethereum-sepolia-rpc.publicnode.com',
    'python scripts/iteration7-gas-summary.py', '```', '',
    'The optional public endpoint above is a read-only evaluation transport, not a change to Render RPC configuration. Endpoint credentials are never written to results. CSV contains local measurements only; supplemental live observations are in iteration7_sepolia_gas.json.']
(root / 'results/iteration7_gas.md').write_text('\n'.join(lines)+'\n')
