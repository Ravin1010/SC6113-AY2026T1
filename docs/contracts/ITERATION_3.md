# Iteration 3 — smart-contract implementation only

Baseline: `92707ce35aa22246d6cfd5592e85b52f33ddb7bc` on `main`.
Branch: `feature/iteration-3-smart-contracts`.

## Classroom reuse

The baseline repository contains the deposit/transfer frontend ABIs but no Solidity
sources. The previously inspected classroom sources in Remix Gist
`35a42b089368b2a290547b147b514423` record only the latest supplied addresses/amount.
This implementation retains `deposit_money.sol` / contract `deposit_money` and
`transfer_money.sol` / contract `paynow`, and evolves their funding/remittance
responsibilities. Only `RoleRegistry` is added as an application contract.

The useful classroom method names `deposit`, `deposit_view`, `transfer` and
`transaction` remain, but their signatures/semantics intentionally change:

- `deposit()` is payable and credits `msg.sender` using `msg.value`.
- `deposit_view()` returns the caller's available and reserved balances.
- `transfer(address recipient, uint256 amount)` creates a funded remittance for
  `msg.sender` and returns its ID.
- `transaction(uint256 id)` reads a specific remittance rather than a latest record.

Amounts are wei. These ABIs are not compatible with the historical frontend.
The frontend and historical configured addresses remain unchanged on this branch;
later integration must use separately deployed evolved contracts and verified ABIs.

## Reproducible local verification

Use Node.js 22 or 24 and npm:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run compile:contracts
npm run sanity:contracts
```

Pinned development-only dependencies: solc 0.8.34, ethers 6.16.0 and Ganache 7.9.2.
Compilation uses optimizer 200 runs and Shanghai EVM output. Generated ABI/bytecode
and compiler input are written to ignored `build/contracts/`, never into the frontend.

Sanity verification deploys only to a deterministic, isolated in-memory EVM with
chain ID 31337. No RPC URL, secrets, Sepolia transactions or deployment script are
used. The receiver fixture is compiled in memory, not added as an application contract.
These are focused implementation checks, not the later full security/test/gas suite.
Ganache may fall back to its JavaScript transport on newer Node versions; this
does not prevent the in-memory checks. No gas benchmark is performed.

## Transaction model

The ten external state-changing MVP actions are:

| Contract | Actions |
| --- | --- |
| RoleRegistry | authorizeSender, authorizeRecipient, revokeRole, pause, unpause |
| deposit_money | deposit, withdraw |
| paynow | transfer (create), claim, cancel |

`setRemittanceContract` is setup only. `reserveFunds`, `releaseFunds` and
`unlockFunds` are trusted contract coordination only. None count toward the ten.
`IRemittanceConfiguration` is a read-only interface, not a deployed fourth contract.

## Permanent wiring

Future deployment order (not executed):

1. Deploy RoleRegistry; its deployer is the permanent sole Admin/Auditor.
2. Deploy deposit_money with that registry address.
3. Deploy paynow with that registry and funding address.
4. Registry Admin calls deposit_money.setRemittanceContract(paynowAddress) once.

Setup rejects zero/noncontract addresses and mismatched registry/funding references.
Once set, the trusted remittance address cannot be replaced or cleared. Before
setup, creation and reservation coordination are blocked. Verify the intended
contract bytecode/address before this irreversible setup; matching getters alone
are not proof of a candidate contract's authenticity.

## Safety and accounting

- Registry Admin alone changes ordinary roles/pause. Only Sender/Recipient exist
  in the revocation enum, so Admin authority cannot be revoked or transferred.
- Available/reserved balances are per owner; reservations retain ID, original
  sender, recipient and amount, plus active flag. Used IDs cannot be reserved again.
- totalAvailable + totalReserved must not exceed actual funding-contract ETH.
  Forced/unsolicited ETH can cause surplus, but creates no withdrawable credit;
  no surplus-sweep or extra administrative withdrawal action is introduced.
- Only the wired paynow coordinates reservations. Release takes no arbitrary
  recipient parameter: it pays the recipient stored at reservation creation.
- Create/reserve, claim/payment and cancel/unlock are atomic. Solidity reverts
  roll back state across both contracts if a funding operation or payout fails.
- Status/accounting effects precede ETH callbacks. Small local nonReentrant
  modifiers protect all funding mutations and all remittance lifecycle actions.
  No OpenZeppelin dependency/inheritance framework is necessary for this guard.
- Revocation blocks new role-dependent activity, not existing withdrawal/claim/
  cancellation rights. Full pause temporarily blocks all five financial actions.
- Direct empty-calldata ETH transfers are not accepted; use deposit().

## Focused checks

The sanity runner checks three deployable application contracts, the exact ten
MVP ABI actions, required event signatures, Admin/one-time wiring constraints,
untrusted reservation calls, identity/amount/balance checks, atomic create rollback,
locked withdrawal rejection, both terminal states, role revocation exit rights,
full pause and available reads/role changes, ETH payout rollback and reentrant
recipient/withdrawal callbacks. Accounting is checked after each lifecycle group.

## Deferred work / unchanged scope

No Flask, SQLite, existing HTML/CSS/JavaScript/ABIs/addresses, Render, Remix,
Google Drive, report or slides are changed. No merge to main or public deployment.
Sepolia deployment, address/ABI verification, backend/frontend integration,
free durable SQLite-compatible provider selection and comprehensive testing/gas
analysis remain later work. Loss of the single Admin key prevents future Admin
actions, including unpause, by the frozen single-Admin/no-transfer design.
