# Cross-Border Remittance DApp with Recipient Claim and Status Tracking

## Overview

SC6113 coursework MVP using **Sepolia test ETH only**. A Sender deposits funds, creates a remittance that reserves them, and a designated Recipient claims it or the Sender cancels it while pending. It demonstrates programmable lifecycle rules and verifiable status/history, not real international fiat settlement, FX conversion or production financial suitability.

## Key Features

- Sender, Recipient and immutable Admin roles.
- MetaMask wallet-signature authentication and user-controlled transaction signing; Flask owns no wallet keys.
- Deposit/withdraw; create/claim/cancel remittances; role administration and pause/unpause.
- Direct authoritative remittance state, transaction/event Activity, and responsive dashboard.
- Remittance Status Overview: PENDING / COMPLETED / CANCELLED bars and counts for the currently loaded page (up to 20), presentation only, with no extra API/RPC request. This is not historical analytics.
- Minimal Name/Timestamp User Log, independent of wallet authentication and roles.

The exact ten blockchain transaction types are `authorizeSender`, `authorizeRecipient`, `revokeRole`, `pause`, `unpause`, `deposit`, `withdraw`, `transfer` (create remittance), `claim` and `cancel`. Deployment and one-time wiring are excluded.

**Balance terminology:** Available deposited funds are the wallet owner's unreserved DApp deposits. Claim pays directly to the recipient's wallet; it does not increase the recipient's deposited balance. Cancel returns reserved funds to the sender's deposited balance.

## Architecture / Components

| Component | Responsibility |
|---|---|
| `contracts/RoleRegistry.sol` | Immutable Admin; Sender/Recipient permissions; global pause |
| `contracts/deposit_money.sol` | Available/reserved accounting, deposits/withdrawals, trusted remittance reservations and payouts |
| `contracts/transfer_money.sol` (`paynow`) | PENDING → COMPLETED or CANCELLED lifecycle, participant checks |
| Flask REST backend (`app.py`, `backend/`) | Wallet authentication/session, verified chain reads, unsigned preparation and receipt verification |
| SQLite locally / Turso in production | User Log, nonce/session support and non-authoritative transaction/event index |
| `templates/`, `static/` | Server-rendered HTML, CSS and vanilla JavaScript; MetaMask and scoped presentation caching |
| Sepolia / Render | Financial test-chain state / hosted Python application |

Blockchain contract reads are financial authority. Turso/SQLite and browser snapshots are application support/history/presentation only. Claim/Cancel rights for existing remittances survive ordinary-role revocation under the frozen design; pause blocks financial writes.

## Blockchain Deployment

Network: **Ethereum Sepolia**, chain ID **11155111**. Deployment ID: `sc6113-sepolia-11884239`.

| Contract / authority | Verified address |
|---|---|
| RoleRegistry | `0x8E7A8Abf90cD4363F82489D14485Df7ACcaE4678` |
| deposit_money | `0x630863E58375Db128EFEfA51Ee369141cCbb839A` |
| paynow | `0xA2Ee37DD717a8758Eb864788456d047b296C00E8` |
| Immutable Admin | `0x4A779fA7d5eA106f1aDFB8369e65fCAA465ca7Fd` |

See [frozen deployment manifest](deployment/sepolia.json) and [Sepolia evidence](docs/integration/ITERATION_6A.md). Test assets only; do not deploy replacements or use historical classroom addresses.

## Public Deployment

- Application: <https://sc6113-ay2026t1.onrender.com>
- Render service: `srv-dal7read0e5s738rldh0`
- Verified live application commit: `72eec24297a3925979c1573182c4edb09ad77dd1`
- Live deploy: `dep-db8694ou01pc73emjnv0` (confirmed Live for this documentation pass).

## Repository / Submission Baseline

**Use branch [`hotfix/iteration-9-smart-account-failure-state`](https://github.com/Ravin1010/SC6113-AY2026T1/tree/hotfix/iteration-9-smart-account-failure-state), not `main`, for the accepted project.**

Accepted application baseline: [`72eec24297a3925979c1573182c4edb09ad77dd1`](https://github.com/Ravin1010/SC6113-AY2026T1/tree/72eec24297a3925979c1573182c4edb09ad77dd1). Documentation-only commits after this application baseline do not change the hosted runtime. Obtain the checked-out documentation revision with `git rev-parse HEAD`; do not confuse a newer documentation head with a different hosted implementation.

The authoritative current-state summary is [FINAL_SUBMISSION_BASELINE.md](docs/final/FINAL_SUBMISSION_BASELINE.md). `main` is not the final submission branch at present.

## Setup / Local Run

Use Python with `venv`, Node.js/npm for contract tests, and MetaMask on Sepolia for wallet interaction. From a checkout of the accepted branch, POSIX-shell example:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
npm ci
python scripts/run-local-sepolia.py
```

Open **http://localhost:5000** (matching the development authentication origin). Windows users can activate `.venv\Scripts\activate` and use the equivalent Python commands. The helper loads addresses/chain/deployment from the tracked manifest and defaults to ignored `local-sepolia.db`; schema creation is lazy/idempotent. No contract deployment is performed. Keep Turso variables unset for ordinary local SQLite use. Without a working RPC, blockchain actions fail closed; basic pages/User Log can still run locally.

Supply the RPC credential and any overrides through the process environment. The application reads environment variables directly; copying `.env.example` does not itself load those values. Never commit credentials, production sessions or wallet secrets. The public deployment needs no local configuration.

Recognized environment-variable **names only** (see [.env.example](.env.example) and `app.py`):

- `APP_ENV`, `AUTH_ORIGIN`, `FLASK_SECRET_KEY`, `DATABASE_PATH`
- `BLOCKCHAIN_RPC_URL`, `BLOCKCHAIN_CHAIN_ID`, `BLOCKCHAIN_DEPLOYMENT_ID`, `BLOCKCHAIN_MANIFEST_PATH`
- `ROLE_REGISTRY_ADDRESS`, `FUNDING_CONTRACT_ADDRESS`, `REMITTANCE_CONTRACT_ADDRESS`
- `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`

The local helper supplies the frozen manifest/address settings; provide `BLOCKCHAIN_RPC_URL` privately. Production requires explicit HTTPS origin, secret and remote Turso credentials, but no production setting needs changing to assess this project. Never supply a seed phrase/private key to Flask or a testing utility.

## Testing

Accepted Iteration 11 evidence: **214 Python tests; 87 browser tests; 3 Solidity contracts, zero warnings; 10 sanity groups/50 rejections; comprehensive 71 scenarios/952 assertions; SQLite and libSQL integration 17 assertions each**. See [full results and caveats](docs/final/ITERATION_11_FINAL_VERIFICATION.md).

After the setup above, browser testing additionally needs Playwright/Chromium. Install locally without changing tracked package manifests:

```sh
npm install --no-save --package-lock=false playwright
npx playwright install chromium
npm run compile:contracts
npm run sanity:contracts
node scripts/iteration7-role-boundary.cjs
node scripts/iteration7-contract-evaluation.cjs
node scripts/remediation-wallet-characterization.cjs
python -m unittest discover -s tests
PYTHON=.venv/bin/python node --test tests/frontend.cjs
PYTHON=.venv/bin/python node tests/local-chain.cjs
LOCAL_DB_DRIVER=libsql PYTHON=.venv/bin/python node tests/local-chain.cjs
python scripts/profile-last-latency.py
python -m pip check
python -m compileall -q backend app.py
for f in static/js/*.js; do node --check "$f"; done
git diff --check
```

Use an isolated checkout for evaluation/profile scripts: they regenerate result files. Browser tests use controlled wallets and isolated SQLite; integration suites use local Ganache, including libSQL locally, not production Turso. Where a system Chromium is required, the existing runner accepts `CHROMIUM_EXECUTABLE_PATH`; runtime-provided Playwright may use `NODE_PATH`. No Sepolia write is needed for these suites. Linux Chromium may require system dependencies. These commands are reproduced from existing tooling, not a newly executed regression in this documentation pass.

The two later UI-only corrections each passed the existing 87 browser tests; the wording correction additionally passed 29 backend tests and three rendered-page checks. The layout correction passed focused 320/360/768/1280px checks. The full Iteration 11 suite was not rerun after them.

Latest visualization remediation: **12 focused tests, 99 full browser tests and 214 Python tests passed**, including 320/360/768/1280px checks. These supplement, not replace or rerun, the historical contract/integration suites. [Implementation and hosted read-only evidence](docs/final/FINAL_VISUALIZATION_REMEDIATION.md).

## Known Limitations

- Coursework/test-asset MVP: no real fiat/bank settlement, FX, production KYC/AML or regulatory-compliance claim.
- Render Free/cold starts, public RPC latency and Sepolia inclusion time can delay interaction. Pre-warm before assessment.
- MetaMask Added Protection / EIP-7702 wrapped execution may fail in some wallet/version/account states. Accepted traces show nested funding-call out-of-gas, preserved caller identity and safe terminal-failure recovery. This is not a universal Smart Account failure or a claim that the DApp enabled it. Review warnings carefully; use the standard wallet path for this testnet DApp where applicable. Never blindly resubmit an unresolved hash or bypass protections for unfamiliar DApps/real assets. See [bounded diagnosis](docs/usability/ITERATION_9_REMEDIATION.md).
- One canonical confirmation plus required authoritative post-state is the classroom success policy; it is not production financial finality.
- Activity is a cached, non-authoritative index; historical catch-up may remain incomplete. Explicit reconciliation and Refresh are available for external changes.
- Direct remittance scanning is intentionally low-volume. Admin ordinary-role self-assignment is accepted Low-severity I7-01, without transfer of Admin authority.
- Five classmates/friends are a convenience usability sample, not representative of migrant/remittance users. No production financial suitability is claimed.

## Documentation

- [Five required submission diagrams — editable sources and SVGs](docs/diagrams/README.md)
- [Current submission baseline and planned deliverable paths](docs/final/FINAL_SUBMISSION_BASELINE.md)
- [Iteration 6A — Sepolia deployment and ten-action evidence](docs/integration/ITERATION_6A.md)
- [Iteration 6B — Turso/Render and hosted lifecycle](docs/integration/ITERATION_6B.md)
- [Iteration 7 — testing, security and gas](docs/testing/ITERATION_7.md); [gas results](results/iteration7_gas.md)
- [Iteration 8 — problem evidence/research](docs/research/ITERATION_8.md)
- [Iteration 9 — five-person usability evaluation](docs/usability/ITERATION_9.md)
- [Remediation, performance and Added Protection incident](docs/usability/ITERATION_9_REMEDIATION.md)
- [Iteration 11 — final technical verification](docs/final/ITERATION_11_FINAL_VERIFICATION.md)
- [Final visualization remediation — current runtime and hosted verification](docs/final/FINAL_VISUALIZATION_REMEDIATION.md)

The required diagram set is complete. The technical report, consolidated final testing report, user manual, combined Individual Contribution Report, presentation slides, 10-minute presentation/demo video or live demonstration, and final submission packaging remain pending separate deliverables. Links above are evidence records, not substitutes for those unfinished artifacts.

## Contribution History

[Git commit history](https://github.com/Ravin1010/SC6113-AY2026T1/commits/hotfix/iteration-9-smart-account-failure-state/) records development progression and contribution evidence. It does not by itself establish formal member-by-member ownership or percentages. The final combined Individual Contribution Report will provide the agreed individual/group contribution summary; no allocation is invented here.
