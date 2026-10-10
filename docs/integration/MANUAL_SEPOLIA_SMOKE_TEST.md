# Iteration 6A — completed manual Sepolia smoke test / reproduction guide

Post-wiring deployment verification passed at Sepolia block **11884361**.
All three contracts have exact-match Sourcify verification, verified Blockscout
source, accepted source contents and accepted compiler settings. Remix source
paths were `contracts/contracts/...`; locally reproduced build retains those paths
and exact metadata. Repository Solidity files and ABIs remain unchanged.

| Component | Verified public address |
|---|---|
| Admin | `0x4A779fA7d5eA106f1aDFB8369e65fCAA465ca7Fd` |
| RoleRegistry | `0x8E7A8Abf90cD4363F82489D14485Df7ACcaE4678` |
| deposit_money | `0x630863E58375Db128EFEfA51Ee369141cCbb839A` |
| paynow | `0xA2Ee37DD717a8758Eb864788456d047b296C00E8` |

Wiring transaction:
`0xa2b051bc68857ee471c8bf22d127907e903d69e79b70c40ec3426201b98a54c4`,
block 11884306. The transaction uses a wallet batch; its verified funding event
(log 388) records the correct Admin and trusted paynow. A read-only repeat-wiring
simulation returned `Already configured`. **Never submit another wiring call.**

## Start the prepared interface locally (no Render deployment)

Download/extract the supplied integration source package. Open a terminal in the
extracted project directory. Example PowerShell commands:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:AUTH_ORIGIN = "http://localhost:5000"
$env:BLOCKCHAIN_RPC_URL = "https://ethereum-sepolia-rpc.publicnode.com"
.\.venv\Scripts\python.exe scripts/verify-deployment.py --manifest deployment/sepolia.json --phase post-wiring --wiring-tx 0xa2b051bc68857ee471c8bf22d127907e903d69e79b70c40ec3426201b98a54c4
.\.venv\Scripts\python.exe scripts/run-local-sepolia.py
```

If this public RPC is unavailable locally, set a working Sepolia RPC URL privately.
Do not commit provider tokens or send credentials. The verifier must pass before
smoke transactions. Open **http://localhost:5000/main** in the MetaMask-enabled
browser. The helper uses a separate `local-sepolia.db` (ignored by Git), preserving
any existing classroom user.db. It uses a development-only ephemeral Flask secret;
restart requires a new login. No Turso/Render integration is involved.

Use the normal connect/nonce/message-signature login for each chosen wallet. Wallet
connection alone is not authentication. All transaction approvals stay in MetaMask.
Confirm Sepolia (11155111 / 0xaa36a7), verified deployment, wired/unpaused state and
matching authenticated/connected account. Account changes clear the session:
sign in again after each switch. Keep small test ETH for value and gas in each
wallet. Use **three public wallets**: existing Admin, Sender, a distinct Recipient.

## Minimal sequence covering all ten approved action types

Do not start a subsequent dependent step until the preceding transaction succeeds.
Record the actual hash and ID; example amounts below are Sepolia test ETH only.

| Step | Wallet / interface | Action | Expected evidence |
|---|---|---|---|
| 1 | Admin, dashboard Admin section | Authorize Sender's actual wallet | RoleAuthorized(Sender); Sender role becomes active |
| 2 | Admin, same section | Authorize Recipient's actual wallet | RoleAuthorized(Recipient); Recipient role becomes active |
| 3 | Sender, funding page | Deposit **0.003 test ETH** | FundsDeposited; available becomes 0.003 if initially empty |
| 4 | Sender, remittance page | Create **0.001 test ETH** for Recipient | RemittanceCreated + FundsReserved; capture actual ID; PENDING; available 0.002, reserved 0.001 |
| 5 | Recipient, remittance page | Enter that ID and Claim | RemittanceClaimed + ReservedFundsReleased; COMPLETED; reservation inactive; recipient payout confirmed (wallet net change also includes gas) |
| 6 | Sender, remittance page | Create second **0.001 test ETH** remittance | New actual ID; PENDING; funds reserved |
| 7 | Admin | Revoke Sender's ordinary **Sender** role | RoleRevoked; new deposits/creation disabled |
| 8 | Original Sender | Cancel second pending remittance | RemittanceCancelled + ReservedFundsUnlocked; CANCELLED; funds return to available despite revocation |
| 9 | Sender / balance owner, funding page | Withdraw **0.001 test ETH** available | FundsWithdrawn; withdrawal remains valid despite revocation |
| 10 | Admin | Pause | SystemPaused; all five financial controls disabled; balances/statuses unchanged |
| 11 | Admin | Unpause | SystemUnpaused; eligible withdrawal/exit controls restored; revoked Sender's deposit/create stay disabled |

Two creation transactions are needed to exercise both lifecycle outcomes. This
sequence covers exactly ten distinct transaction types without artificial actions.
Do not reauthorize/revoke repeatedly or send failed transactions for volume.

While paused, inspect disabled controls and getter state. If explicit revert evidence
is needed, run a **read-only eth_call** with a positive eligible withdrawal amount;
expect `System paused`. Do not send that failing transaction. Full-pause and
recipient-revocation exit rights are also covered by local sanity tests; the live
sequence above specifically demonstrates Sender cancellation/withdrawal after
revocation. Additional Recipient-revocation testing is optional and must be planned
before a pending claim, not used to reopen terminal records.

### Remix fallback

If local UI setup is unavailable, use your existing deployed Remix instances and
the same public addresses. Do **not** deploy again. For deposit set Remix Value to
`0.003 ether`, then call payable `deposit()`. **Reset Value to 0** for other calls.
A 0.001 test ETH amount equals `1000000000000000` wei for `transfer`/`withdraw`.
`revokeRole(SenderAddress,0)` revokes Sender (Recipient enum is 1). Use actual
remittance IDs. Sign each action manually; return evidence so backend/index/UI
can be checked afterward. Note whether actions were exercised through UI or Remix;
Remix testing alone does not prove live frontend wallet submission.

## UI / history observations

- Admin controls must be unavailable for Sender/Recipient accounts.
- Wrong-chain state disables writes; network switching is user initiated.
- No wallet connection or login signature is counted as a blockchain transaction.
- Submitted hash means pending; confirmed status requires a canonical receipt.
- The index uses six confirmations. Newly created remittances may initially be
  absent from indexed discovery; direct ID lookup uses verified contract state.
- After six confirmations, refresh activity. Compare actual tx/hash/block/log/event
  details; cached history remains labelled non-authoritative.
- At a narrow browser width, verify forms/navigation/hash cards remain readable.
  Physical-phone testing and comprehensive security/gas work remain later phases.

## Return only public evidence

Send Sender and Recipient public addresses; action name and actual transaction
hash for each signed action; actual remittance IDs; outcome/error and whether UI
or Remix was used. Include a screenshot only if it helps explain an issue. Never
send private keys, seed phrases, RPC credentials or signed session cookies.

This checkpoint is completed and user-accepted. The actual receipts, wallet roles,
amounts and final state are recorded in `deployment/live-smoke-evidence.json` and
`ITERATION_6A.md`. The sequence above remains an illustrative reproduction guide;
it must not replace the actual evidence. Final commit/push is authorized on the
feature branch only. No merge, Render deployment, Turso integration or Iteration 6B.

## Narrow correction recheck

Use the same verified deployment and existing test-wallet roles. Do not repeat wiring.
After a successful claim/cancel reaches the existing confirmation threshold, verify
that the selected ID shows COMPLETED/CANCELLED and both exit buttons are disabled
without pressing Refresh. Confirm funding changes after cancel/withdraw and own role
or pause changes after Admin actions.

For a MetaMask-batched transaction, verify that the receipt endpoint accepts the
wallet's verified contract-event participation even if the outer sender/target is a
wrapper/relayer. Do not accept a transaction lacking deployment-event association.

In browser Network tools, observe /api requests: menu clicks, dashboard section links
and tab focus may check the session but must not reload users/me, balances and the
remittance list. A new page loads its own sections. Switching networks must invalidate
and reload the read context; switching accounts must clear the session and require
fresh authentication before enabling actions. Explicit Refresh remains available.
