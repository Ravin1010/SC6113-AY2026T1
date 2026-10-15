# Iteration 11 — Final technical verification and repository freeze

Verification date: 15 October 2026 SGT (14 October UTC). Submission deadline supplied by owner: 18 October 2026, 11:59 PM. This record freezes the technical baseline, not the unfinished submission deliverables.

## Baseline and scope

- Branch: `hotfix/iteration-9-smart-account-failure-state`.
- Accepted starting head: `339cfb37e39dcf123e280d835d0070a1f61636ac`; working tree initially clean and remote branch matched.
- Its direct parent and hosted implementation: `0302ab0a4ac78b80384b5c6e26985af30fd1578d`.
- The sole intervening commit changes only `docs/usability/ITERATION_9_REMEDIATION.md` (174 added lines). No intervening runtime, test, configuration or deployment change.
- Production Solidity still matches frozen Iteration 3 commit `313a82a8514624efd9351f3d45180447ae6b966d`.
- This iteration adds only this verification document. No source/test/configuration changes, wallet signing, chain writes, database maintenance, deployment, main merge or submission-artifact production.

## Final local regression

Tests ran in a detached temporary worktree at the accepted head. Generated builds, test databases and regenerated gas/profile results stayed there; frozen repository evidence was not overwritten. Python used a fresh virtual environment with repository requirements; browser tests used real headless Chromium and controlled wallet/RPC fixtures. All chain execution was local Ganache.

| Suite | Final result |
|---|---|
| Solidity compile | solc 0.8.34; 3 deployable contracts; zero warnings; Shanghai, optimizer 200 |
| Contract sanity | 10 groups; 50 expected rejections; PASS |
| Iteration 7 role boundary | 8 assertions; PASS under accepted I7-01 policy |
| Comprehensive contract evaluation | 71 scenarios, 61 expected rejections, 952 assertions, 48 seeded model transitions; 10 gas measurements; PASS |
| Wallet characterization | 4 checks; PASS; generic distinct-caller wrapper test is not evidence about same-address EIP-7702 |
| Python/backend | 214 tests; PASS |
| Browser/frontend | 87 tests; 87 passed, 0 failed/skipped/cancelled |
| SQLite HTTP/local-chain integration | 17 assertions; 12 canonical events; repeat indexing unchanged; PASS |
| libSQL HTTP/local-chain integration | 17 assertions; 12 canonical events; repeat indexing unchanged; PASS |
| Dependencies | `pip check`: no broken requirements |
| Syntax | All six frontend JS modules checked; Python compileall passed |
| Repository | Initial clean tree; frozen Solidity diff empty; whitespace/diff check passed |
| Existing controlled latency profiler | Seven representative prepare actions still use 5 warm transports; balance read uses 4; PASS |

The Python log includes an intentionally injected database exception exercised by rollback tests; the suite finishes OK. Ganache reports unavailable native µWS support and successfully uses its JavaScript fallback. Neither is a code blocker. Dependency checking establishes installed-package compatibility, not a vulnerability audit or reproducible lock for unpinned Flask/gunicorn.

Reproduction commands (isolated checkout recommended because evaluation/profile scripts regenerate results):

```sh
npm run compile:contracts
npm run sanity:contracts
node scripts/iteration7-role-boundary.cjs
node scripts/iteration7-contract-evaluation.cjs
node scripts/remediation-wallet-characterization.cjs
python -m unittest discover -s tests
NODE_PATH=<runtime-node-modules> PYTHON=<venv-python> CHROMIUM_EXECUTABLE_PATH=<chromium> node --test tests/frontend.cjs
PYTHON=<venv-python> node tests/local-chain.cjs
LOCAL_DB_DRIVER=libsql PYTHON=<venv-python> node tests/local-chain.cjs
python scripts/profile-last-latency.py
python -m pip check
python -m compileall -q backend app.py
for f in static/js/*.js; do node --check "$f"; done
git diff --check
```

## Read-only hosted verification

Render metadata and latest-deploy lookup confirm service `srv-dal7read0e5s738rldh0`, deploy `dep-db7o5idg1s2s73b89t3g`, status **live**, implementation `0302ab0a4ac78b80384b5c6e26985af30fd1578d`. It completed at 2026-10-14 13:26:28 UTC. Documentation head `339cfb3` being newer is intentional, not a runtime mismatch.

Public URL: <https://sc6113-ay2026t1.onrender.com>.

| GET check | HTTP | Observed client elapsed seconds |
|---|---:|---:|
| Landing `/` | 200 | 39.99 initially; 5.38 on repeat |
| `/main` | 200 | 9.92 |
| `/depositMoney` | 200 | 9.18 |
| `/transferMoney` | 200 | 9.67 |
| `/viewUser` | 200 | 10.60 |
| `/static/styles.css` | 200 | 5.74 |
| `/static/js/live.js` | 200 | 5.25 |
| `/api/auth/session`, `/api/users/me`, balances, remittances, transactions | 401 each | Expected unauthenticated authorization failures |

These timings include client/network/proxy/service effects and do not isolate backend execution or establish a controlled cold-start benchmark. The initial delay and quicker repeat support pre-warming advice; they do not prove its exact cause. No sampled request returned 500. No real wallet authentication or hosted financial API session was created in this pass; accepted hosted authentication/financial evidence remains in the remediation record. This pass did not inspect or mutate production Turso data.

## Read-only chain snapshot

Read-only source: `https://ethereum-sepolia-rpc.publicnode.com`. Reads used `eth_chainId`, block-header reads and exact-block `eth_call` only, pinned to block **11914408**, hash `0x39b24f86d0b57b9b0cb7f165b98daa2001962c3888b32b8eaf4264a76d2ca5fa`. A final reread confirmed that hash. Chain ID is `11155111`.

| Check | Observed result |
|---|---|
| Registry | `0x8E7A8Abf90cD4363F82489D14485Df7ACcaE4678` |
| Funding | `0x630863E58375Db128EFEfA51Ee369141cCbb839A` |
| Paynow | `0xA2Ee37DD717a8758Eb864788456d047b296C00E8` |
| Immutable Admin | `0x4A779fA7d5eA106f1aDFB8369e65fCAA465ca7Fd` |
| Pause | false |
| Funding roleRegistry / remittanceContract | expected Registry / Paynow |
| Paynow roleRegistry / funding | expected Registry / Funding |
| Demo sender `0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a` | Sender and Recipient true |
| Demo recipient `0x890F63435Cf6F4D526F7062A282A94c74A50cFa3` | Sender and Recipient true |
| Remittance count | 14 |
| #3 | COMPLETED; 0.001 test ETH; reservation inactive |
| #12 | COMPLETED; 0.005 test ETH; reservation inactive |
| #13 | COMPLETED; 0.001 test ETH; reservation inactive |

The #3 parties match the original demo wallets. #12/#13 sender is `0xF84B634B34A031e99FDc85D34088af99B60D8300`, recipient is `0x8753E34d87bFF7fe31082cBd0DA4Ac2e3961B4D0`. No role or lifecycle transaction was sent. Wiring/state checks are not a new exhaustive runtime-bytecode/deployment-provenance audit; retain the accepted verified-deployment evidence.

## Data-visualization compliance decision

Assignment wording: “Responsive dashboard with transaction history, event logs, and relevant data visualizations.”

**SATISFIED at a basic dashboard-summary level**, with an explicit qualification: there is no chart/graph. Actual UI contains available/reserved balance cards, role/deployment summaries, remittance ID/status/amount/party presentation, and paginated transaction/event Activity cards. User Log has a Name/Timestamp table but is not financial visualization evidence. Responsive populated dashboards are tested at 360, 768 and 1280 px.

This assessment treats relevant numeric/status summaries as basic visual presentation and does not invent a mandatory chart type absent from the brief. It is not a guarantee of full assessor marks. A small status-count or balance chart could make visualization coverage more explicit, but is **OPTIONAL POLISH**, not a technical blocker; no implementation is recommended for this freeze.

## Final GitHub strategy and README decision

**Recommend B: leave main unchanged and explicitly submit the accepted branch plus immutable final commit permalink.** At inspection, main is `92707ce35aa22246d6cfd5592e85b52f33ddb7bc`, an ancestor 22 commits behind the accepted starting head. Preserve history; do not imply main contains the final work. Place the exact branch/commit link prominently in the later README and submission so assessors can find it immediately. A merge/default-branch change/tag is unnecessary during this verification freeze.

Render currently has auto-deploy **off** and configured branch `feature/iteration-6b-production-deployment`; its manually selected live commit is the verified hotfix above. Do not change these settings or redeploy merely for a documentation commit.

**README completion: MUST COMPLETE before submission.** Current README contains only the project title. Later authorized documentation work should add: overview/coursework scope; components and roles; hosted URL; verified Sepolia addresses; setup/run instructions; environment-variable names without credentials; test commands; exact accepted branch/commit; bounded Added Protection limitation; links to report/manual/testing evidence. No README was edited here.

## Demo guidance, limitations and remaining submission work

- Pre-warm the existing Render site shortly before the demo; allow time for periodic cold deployment proof and public RPC responses.
- Check existing standard-wallet authentication/selected-account alignment before presenting. Prefer the standard wallet execution path; review wallet warnings carefully, never bypass unfamiliar warnings or automatically disable protections.
- Reuse completed #3/#12/#13 and existing ten-action evidence. No new Sepolia transaction is required for this technical verification or transaction-type coverage. A separately approved live demonstration may use minimal actions, but must not blindly resubmit an unresolved hash.
- Prepare existing receipt/explorer links and screenshots as fallback in later demo preparation. Do not attempt every administrative/edge action live or change roles/pause for show.
- Added Protection/EIP-7702 nested-gas compatibility remains the accepted external limitation. The hotfix safely releases only canonical terminal failed-wrapper locks; it does not prevent future wallet-generated failures. No new contradictory evidence was found.
- One-confirmation canonical receipt plus action-specific authoritative post-state remain required. Indexed Activity is cached, non-authoritative, potentially incomplete and nonblocking; direct contract reads remain financial authority.
- Public RPC latency, Render Free/single-sync-worker characteristics, wallet interaction and Sepolia inclusion remain residual risks. Five-person usability evidence is not representative of migrant users or proof of production suitability.
- I7-01 Admin ordinary-role self-assignment remains an accepted Low limitation; Admin authority is immutable. This freeze is not a formal security audit or production-financial certification.
- Report, diagrams, manual, contribution records, slides, demo preparation and README remain separate submission work identified in Iteration 10. None were begun here.

References: [Iteration 7](../testing/ITERATION_7.md), [Iteration 8](../research/ITERATION_8.md), [frozen usability evaluation](../usability/ITERATION_9.md), [remediation and final incident diagnosis](../usability/ITERATION_9_REMEDIATION.md), [production persistence evidence](../integration/ITERATION_6B.md).

## Final decision

All required local suites passed. Hosted routes and protected authorization boundaries passed; live metadata matches the accepted implementation; pinned contract wiring/state checks passed. No genuine technical blocker was established. Only this document is committed; no generated database/build/cache/profile files are staged. No new chain write, deployment, infrastructure/configuration/database change or main merge occurred.

**TECHNICAL BASELINE — APPROVED / FROZEN**

## Post-freeze current-state update — 15 October 2026

The original verification/deployment facts and regression results above remain historical evidence. Two later UI-only commits were accepted: `da6a3c56a09857b129548b649d013ba2770a754b` (deposited-funds/claim wording) and `54041cb257d85037ed4c45fe3f91da5d235a7eca` (landing name input/button alignment). Their diff is limited to templates/CSS; no Solidity, backend, JavaScript, accounting, configuration or schema change.

Render now reports `54041cb257d85037ed4c45fe3f91da5d235a7eca` Live in deploy `dep-db83kbrncjis73eg8560`. The owner reports both UI changes working as expected. Each correction passed 87 browser tests; the wording change also passed 29 backend/three rendered-page checks, and layout had focused 320/360/768/1280px checks. **The full Iteration 11 regression was not rerun after these changes.** The current documentation foundation is [FINAL_SUBMISSION_BASELINE.md](FINAL_SUBMISSION_BASELINE.md); this note does not retroactively replace the original `0302ab0` deployment observation.
