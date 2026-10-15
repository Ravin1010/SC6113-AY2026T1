# Final submission baseline — SC6113

Current-state foundation recorded 15 October 2026. **Cross-Border Remittance DApp with Recipient Claim and Status Tracking** is a Sepolia test-asset coursework MVP, not a production financial/remittance service. Technical work and the five required diagrams are accepted/frozen; the other final deliverables listed below remain pending.

## Accepted source and live version

| Item | Accepted value |
|---|---|
| Repository | <https://github.com/Ravin1010/SC6113-AY2026T1> |
| Submission branch | `hotfix/iteration-9-smart-account-failure-state` |
| Documentation checkpoint audited | `02f67fe28be24b62b859d945c050f1a738111f8d` (prior submission foundation); this evidence freeze is a documentation-only child of the live implementation. Obtain its exact SHA with `git rev-parse HEAD`. |
| Accepted application commit | [`72eec24297a3925979c1573182c4edb09ad77dd1`](https://github.com/Ravin1010/SC6113-AY2026T1/tree/72eec24297a3925979c1573182c4edb09ad77dd1) |
| Render URL | <https://sc6113-ay2026t1.onrender.com> |
| Service / live deploy | `srv-dal7read0e5s738rldh0` / `dep-db8694ou01pc73emjnv0` |
| Live implementation | `72eec24297a3925979c1573182c4edb09ad77dd1` |
| Network / chain ID | Ethereum Sepolia / `11155111` |
| Deployment ID | `sc6113-sepolia-11884239` |

Render metadata confirms implementation `72eec24297a3925979c1573182c4edb09ad77dd1` **Live**, deploy `dep-db8694ou01pc73emjnv0`, finished 2026-10-15 05:29:58 UTC. The owner performed exact-commit deployment; this continuation performed read-only verification and no deployment. The subsequent documentation-only freeze is not a runtime change. `main` remains non-authoritative; use the explicit submission branch and distinguish live implementation from documentation HEAD.

## Frozen deployment

| Component | Address |
|---|---|
| RoleRegistry | `0x8E7A8Abf90cD4363F82489D14485Df7ACcaE4678` |
| deposit_money | `0x630863E58375Db128EFEfA51Ee369141cCbb839A` |
| paynow | `0xA2Ee37DD717a8758Eb864788456d047b296C00E8` |
| Immutable Admin | `0x4A779fA7d5eA106f1aDFB8369e65fCAA465ca7Fd` |

Addresses are cross-checked against [the unchanged manifest](../../deployment/sepolia.json) and accepted Iteration 11 evidence. This documentation pass did not perform a new on-chain deployment/state audit. Do not use older classroom addresses or redeploy the frozen contracts.

## Current architecture and financial semantics

- MetaMask EIP-191 wallet-signature authentication establishes a Flask application session; blockchain writes are prepared unsigned by the backend and signed/submitted by the user's wallet. No server wallet/private keys.
- Three roles: Sender, Recipient, Admin. Only immutable Admin grants/revokes ordinary roles and controls pause. Admin can technically hold ordinary permissions (accepted Low limitation I7-01); those permissions cannot confer/replace Admin authority.
- Three interacting contracts: RoleRegistry (roles/pause), deposit_money (deposits, available/reserved accounting, trusted reservation/payout), paynow/transfer_money (participant/lifecycle enforcement).
- Lifecycle: deposit → available deposited funds → create/reserve → designated recipient claim **or** originating sender cancel → terminal status. Claim pays directly to the recipient's wallet, not their DApp available balance. Cancel restores the sender's deposited availability; only available funds may be withdrawn.
- Blockchain is financial authority for roles, pause, balances, reservations, remittance parties/amount/status and transaction outcomes. Remittance discovery is direct verified-contract scanning, not index-dependent.
- SQLite locally and Turso in production store User Log, nonce/session/wallet support, indexed transactions/events and indexing progress. Activity is non-authoritative, cached and independently reconciled; browser sessionStorage is only a scoped presentation cache.
- Remittance Status Overview presents PENDING / COMPLETED / CANCELLED counts and bars from the same currently loaded remittance page (up to 20). No additional API/RPC request, polling, cache or chart dependency is introduced. Unknown statuses are reported separately; the visualization is presentation only, not historical or system-wide analytics.
- One canonical confirmation plus required action-specific direct post-state gates success. Hash preservation, pending/no-resubmit lock, verification-only retry, account-switch reauthentication and reorg/deployment checks remain in force.

Exact ten state-changing transaction types (deployment/setup excluded):

1. `authorizeSender`
2. `authorizeRecipient`
3. `revokeRole`
4. `pause`
5. `unpause`
6. `deposit`
7. `withdraw`
8. `transfer` (create remittance)
9. `claim`
10. `cancel`

## Accepted verification and usability evidence

[Iteration 11](ITERATION_11_FINAL_VERIFICATION.md) records the full regression at source `339cfb37e39dcf123e280d835d0070a1f61636ac`, whose runtime is `0302ab0a4ac78b80384b5c6e26985af30fd1578d`:

- solc 0.8.34: three deployable contracts, zero warnings;
- sanity: 10 groups / 50 expected rejections; role boundary: 8 assertions;
- comprehensive: 71 scenarios / 61 expected rejections / 952 assertions / 48 seeded model transitions / ten gas measurements;
- wallet characterization: 4 checks; Python: 214 passed; browser: 87 passed;
- SQLite and libSQL local-chain integration: 17 assertions each, 12 canonical events each, idempotent repeat indexing;
- dependency compatibility, JS/Python syntax and diff checks passed;
- read-only hosted pages/auth boundaries and pinned contract wiring/state passed at the recorded time.

Two subsequent changes were UI/presentation only, confirmed by inspecting the commit range: `da6a3c56a09857b129548b649d013ba2770a754b` clarifies deposited funds/claim/cancel; `54041cb257d85037ed4c45fe3f91da5d235a7eca` aligns the name input/save button responsively. Each passed 87 browser tests. Wording also passed 29 backend tests and three rendered-page checks; layout had focused 320/360/768/1280px validation/submission/layout checks. These are targeted follow-up results, **not a rerun of the full Iteration 11 suite**. Owner manually verified both changes on the then-current `54041cb` hosted deployment; this is owner-observed evidence, not a new automated hosted test here.

The later status visualization passed 12 focused tests, 99 full browser tests and 214 Python tests, plus 320/360/768/1280px, syntax/dependency/diff checks. Current live markup/assets and guest safety were checked read-only; non-zero hosted counts were not observed without a wallet session. See [final visualization remediation](FINAL_VISUALIZATION_REMEDIATION.md). Historical Solidity/local-chain totals above were not rerun for this frontend-only change.

Iteration 9 contains five real classmates/friends' sessions (45 normalized rows), conservatively analysed without population inference or SUS claims. Remediation and post-freeze failure recovery are accepted/frozen. Original participant evidence and historical checkpoints remain unchanged. No fresh participant study is claimed.

## MetaMask compatibility and residual limitations

**MetaMask Added Protection / EIP-7702 wrapped-execution gas-budgeting compatibility issue:** accepted protected Create/Claim traces show nested out-of-gas in funding reserve/release calls; original caller identity and intended calldata were preserved. This is strongly consistent with upstream gas-estimation behaviour, not officially confirmed as the exact upstream issue for every wallet/version. No RoleRegistry/lifecycle defect or DApp-triggered Smart Account activation is established. Failed outer execution commits no successful DApp state; the recovery hotfix clears only canonical, sufficiently confirmed terminal failure locks without accepting unrelated successful transactions.

Bounded guidance: “MetaMask Added Protection / Smart Account wrapped execution may fail for this Sepolia coursework DApp in some wallet/version/account states. If a protected transaction fails, the DApp safely detects the failure and allows retry. Use the standard wallet transaction path for this testnet DApp where applicable.” Never automatically disable protections, switch account mode, authorize framework contracts as users or blindly resubmit a pending hash. One successful Smart Account case is not universal compatibility. Sepolia support/eligibility details remain an evidence gap, not a blanket unsupported-network diagnosis.

Other residuals: Render Free/cold periodic proof and public RPC latency; wallet interaction/chain inclusion; one-confirmation short-reorg trade-off; incomplete non-authoritative historical index; low-volume direct scanning; current-page status chart only (no historical trends or advanced BI); convenience-sample usability limitations; unpinned Flask/gunicorn dependencies. No formal security audit, representative usability, scalability, real fiat/FX/KYC/AML, fee reduction or production-financial suitability claim. No new chain write or infrastructure maintenance is needed for this documentation foundation.

## Evidence navigation

| Evidence | Record |
|---|---|
| Sepolia deployment / ten-action receipts | [Iteration 6A](../integration/ITERATION_6A.md) |
| Required diagrams — complete | [Diagram index, five sources and SVGs](../diagrams/README.md) |
| Production persistence / hosted lifecycle | [Iteration 6B](../integration/ITERATION_6B.md) |
| Tests / security / gas | [Iteration 7](../testing/ITERATION_7.md), [gas results](../../results/iteration7_gas.md) |
| Problem research and claim boundaries | [Iteration 8](../research/ITERATION_8.md), [evidence CSV](../../results/iteration8_evidence.csv) |
| Actual usability evaluation | [Iteration 9](../usability/ITERATION_9.md), [45-row dataset](../../results/iteration9_usability.csv) |
| Remediation / performance / final incident diagnosis | [Iteration 9 remediation](../usability/ITERATION_9_REMEDIATION.md) |
| Full final technical verification (historical) | [Iteration 11](ITERATION_11_FINAL_VERIFICATION.md) |
| Current visualization/runtime verification | [Final visualization remediation](FINAL_VISUALIZATION_REMEDIATION.md) |
| Setup / assessor entry point | [README](../../README.md) |

Older documents include dated policies and deployment snapshots. Use their final acceptance sections and this current-state summary rather than treating intermediate checkpoint wording as current behaviour.

## Submission deliverable status and locations

The diagrams are complete. Other final-deliverable paths below are recommendations, not completed artifacts or drafts. Historical testing/usability/deployment records are evidence, not substitutes for a consolidated report or the final demo. No separate checklist is needed.

| Status | Deliverable | Location / recommended location |
|---|---|---|
| COMPLETE | Five required diagrams | [Sources and SVG exports](../diagrams/README.md) |
| PENDING | 10–15 page technical report | `docs/report/TECHNICAL_REPORT` (format/export decided later) |
| PENDING | Consolidated final testing/deployment report | `docs/testing/FINAL_TESTING_REPORT.md` |
| PENDING | User manual | `docs/manual/USER_MANUAL.md` |
| PENDING | Combined Individual Contribution Report | `docs/contributions/INDIVIDUAL_CONTRIBUTION_REPORT.md` |
| PENDING | Presentation slides | `docs/presentation/` |
| PENDING | 10-minute presentation/demo video or live demonstration | `docs/presentation/` (preparation/evidence links later) |
| PENDING | Final submission packaging/check | existing `docs/final/` |

**Original foundation-pass scope (historical):** No report, diagram, testing-report, manual, contribution-report or slide draft was created in that pass. Formal contributions must be agreed with members; Git history provides evidence, not invented percentages. No main merge/default-branch change, code/test/configuration/schema change, chain write or Render deployment occurred in this foundation pass.

## Diagram completion update — 15 October 2026

The [five required diagrams](../diagrams/README.md) are now complete as editable Mermaid sources and SVG exports. The status table above now reflects this completion; diagrams are no longer a remaining deliverable. Reports, manual, contribution report and slides remain separate unfinished work. This diagram-only update does not change the accepted/live application baseline.
