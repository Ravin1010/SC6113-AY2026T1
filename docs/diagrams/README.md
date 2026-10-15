# Required submission diagrams — accepted implementation

**DIAGRAM SET — APPROVED / FROZEN.** Grounded in application commit `54041cb257d85037ed4c45fe3f91da5d235a7eca` and documentation baseline `968f276b851e462f5ac8e8181506033ec4f75115`, on branch `hotfix/iteration-9-smart-account-failure-state`. These diagrams describe existing behaviour; they introduce no product/schema/deployment changes. No report, manual, slide deck or demo script is produced here.

| Required diagram | Editable source | Primary export | Establishes / intended reuse |
|---|---|---|---|
| System architecture | [system-architecture.mmd](system-architecture.mmd) | [SVG](system-architecture.svg) | Hosting, client/wallet/backend/persistence boundaries and financial authority; report/slides |
| Smart contract interaction | [smart-contract-interaction.mmd](smart-contract-interaction.mmd) | [SVG](smart-contract-interaction.svg) | Three roles, three contracts, reserve/release/unlock and direct wallet payout; report/testing report/slides |
| Data model | [data-model.mmd](data-model.mmd) | [SVG](data-model.svg) | Actual support tables, composite identifiers and two declared FK relationships; report/testing report |
| Process flow | [process-flow.mmd](process-flow.mmd) | [SVG](process-flow.svg) | User/business journey, alternative terminal paths and safe recovery; report/manual/slides |
| User-interface flow | [user-interface-flow.mmd](user-interface-flow.mmd) | [SVG](user-interface-flow.svg) | Real routes and screen navigation, not a redesign/wireframe; report/manual/slides |

## Reading the diagrams

### 1. System architecture

[View architecture](system-architecture.svg).

The browser executes the server-rendered HTML/CSS/vanilla JS. MetaMask signs the login message and user-approved transactions; **Flask never signs blockchain transactions or owns wallet keys**. Flask serves verified direct reads and unsigned preparation (fresh authorization, simulation and gas estimation), verifies receipts, and serves authoritative post-state reads consumed/checked by the frontend before final success.

The backend reaches the chain through RPC; the diagram abstracts that transport rather than adding infrastructure. Render hosts the Flask service. SQLite (local) and Turso/libSQL (production) are alternative support stores, not replicated financial ledgers. Their records cover User Log, auth support, application metadata and indexed Activity. Blockchain is authoritative for roles, pause, balances, reservations, remittance state **and financial transaction outcomes**. Browser sessionStorage contains only temporary presentation state scoped by wallet/chain/deployment/session; no credentials are diagrammed or serialized into these artifacts.

Evidence: [app.py](../../app.py), [API](../../backend/api.py), [verified reader](../../backend/blockchain.py), [preparation](../../backend/preparation.py), [database selection](../../backend/database.py), [Turso adapter](../../backend/turso.py), [frontend orchestration](../../static/js/app.js), [wallet authentication](../../static/js/auth.js), [cache](../../static/js/cache.js), [deployment manifest](../../deployment/sepolia.json).

### 2. Smart contract interaction

[View contract interaction](smart-contract-interaction.svg).

Solid arrows show external actions/calls or ETH payouts; dotted arrows show role/pause reads. The diagram is an interaction map, not an instruction to execute every path together. Roles are exactly **Sender, Recipient, Admin**. RoleRegistry's immutable Admin is separate from its two ordinary-role permission mappings; ordinary permissions do not create Admin authority.

- `transfer(recipient, amount)` creates PENDING and calls `reserveFunds`: sender available decreases and reserved increases by the same amount, atomically.
- `claim(id)` sets COMPLETED and calls `releaseFunds`: reservation is deactivated, sender reserved decreases, ETH is sent **directly to the designated recipient wallet**. Recipient available deposited funds do not increase.
- `cancel(id)` sets CANCELLED and calls `unlockFunds`: reservation is deactivated and sender reserved returns to available deposited funds.
- Status/accounting updates revert together if nested execution fails. Claim/Cancel require the stored designated party and a pending remittance, not a current ordinary-role grant. Withdrawal similarly preserves ownership rights after revocation. Pause blocks deposit/withdraw/create/claim/cancel; reads and Admin role management remain available.
- Funding coordination accepts only permanently configured paynow. One-time wiring is already complete; `setRemittanceContract` is configuration, not an eleventh user transaction type. Paynow and funding refer to the same registry. The five Admin functions plus deposit/withdraw/transfer/claim/cancel are the frozen ten action types.

Evidence: [RoleRegistry](../../contracts/RoleRegistry.sol), [funding](../../contracts/deposit_money.sol), [paynow source](../../contracts/transfer_money.sol), [Iteration 7 policy/security evaluation](../testing/ITERATION_7.md).

### 3. Data model

[View data model](data-model.svg).

This is a logical schema diagram with selected important columns, not every timestamp/constraint. PK means declared primary key; FK arrows point from the referencing table to its parent. Invisible source edges control layout only and do not represent relationships. Group boxes and the authority note are annotations, not tables.

Exactly seven tables exist:

| Actual table | Declared primary key | Declared parent relationship |
|---|---|---|
| `user` | None (`name`, `timestamp` only) | None; no wallet/person mapping |
| `auth_nonces` | `nonce` | None; `wallet_address` is not a declared FK |
| `app_wallets` | `wallet_address` | None |
| `auth_sessions` | `token_hash` | `wallet_address` → `app_wallets.wallet_address` |
| `indexed_transactions` | `chain_id`, `deployment_id`, `tx_hash` | None; wallet fields are not app-wallet FKs |
| `indexed_events` | `chain_id`, `deployment_id`, `tx_hash`, `log_index` | First three key fields → `indexed_transactions` |
| `indexing_state` | `chain_id`, `deployment_id`, `contract_address` | None |

`remittance_id` is index metadata, not a financial table/FK. No database remittance/balance/reservation entity is invented. Flask's signed session cookie is not another database table; revocable server validation uses the existing `auth_sessions` table. DB state is support/index/cache metadata; **financial state remains on-chain**. User Log deletion affects only `user`.

Evidence: [schema](../../backend/schema.sql), [database initialization](../../backend/database.py), [nonce/session operations](../../backend/api.py), [receipt/backfill indexing](../../backend/indexer.py). The schema comment saying “future verified indexer” is historical wording; implemented `indexer.py` now writes those tables. No schema change is proposed or made.

### 4. Process flow

[View process](process-flow.svg).

Name entry is optional: Save Name & Continue records a name/timestamp, while Open Dashboard bypasses it. Neither authenticates a wallet. The login signature establishes a session; account/network/session mismatches require correction/re-authentication before writes. Each action independently repeats fresh backend preparation checks, with contract execution enforcing its own rules. The chart's deposit/create/withdraw arrows denote successfully verified actions, not optimistic browser authorization.

All state-changing paths require user-controlled signing, a canonical successful receipt with **one confirmation**, and action-specific authoritative post-state before final success. The shared receipt/post-state gate is shown explicitly after the Claim/Cancel alternatives; it applies to deposit/create/withdraw/Admin actions too. Successful create IDs come from the verified `RemittanceCreated` event plus exact direct-state matching, not a guessed current count.

A wallet rejection with no hash commits nothing. An unresolved submitted hash stays locked; only verification is retried. Canonical terminal failed transactions permit a deliberate retry without claiming DApp success; generic 403/RPC failures do not silently clear the lock. No automatic resubmission occurs. Account/network changes invalidate the active context. Confirmed actions refresh affected financial state; full-list/Activity presentation is independent and must not delay confirmation. Activity historical reconciliation remains explicit and bounded; cached history is non-authoritative.

Evidence: [preparation](../../backend/preparation.py), [receipt API](../../backend/api.py), [transaction state machine](../../static/js/live.js), [targeted refresh](../../static/js/app.js), [frozen remediation/hotfix record](../usability/ITERATION_9_REMEDIATION.md).

### 5. User-interface flow

[View UI navigation](user-interface-flow.svg).

Nodes are existing screens, including the actual response to `POST /deleteUser`; that response is not a separate GET screen. The shared header permits navigation among Dashboard, Funding, Remittance and User Log from the existing pages, not just through Dashboard. The diagram highlights main routes/back links without drawing every shared-header link. Activity (`/main#activity`) and Admin (`/main#admin`) are Dashboard sections, not invented standalone pages. A shared MetaMask login panel and responsive menu are rendered by `base.html`; they are not separate routes. Admin controls are role-dependent; signing in alone does not grant a role.

The Remittance page has input forms, contextual guidance and verified action results/details, not a new remote-preview screen. The landing label sits above a responsive input/button row. User Log remains usable independently of wallet authentication. No new page or feature is proposed.

Evidence: [routes](../../app.py), [shared layout/navigation](../../templates/base.html), [landing](../../templates/index.html), [Dashboard](../../templates/main.html), [Funding](../../templates/depositMoney.html), [Remittance](../../templates/transferMoney.html), [form macros](../../templates/forms.html), [User Log](../../templates/viewUser.html), [delete confirmation](../../templates/deleteUser.html).

## Rendering and reuse

Sources use Mermaid flowcharts. SVGs are standalone vector exports with embedded styles, no screenshots/remote fonts or executable scripts. Use each SVG at full figure width; do not place all five on one report page. Architecture/contract/UI maps are suitable for an A4 landscape figure; data/process diagrams suit portrait pages. Retain captions/semantic qualifications when reusing them, and check final font size in the report/slides rather than shrinking dense figures into a narrow column. No duplicate PNGs are committed.

Reproducible renderer: `@mermaid-js/mermaid-cli` **11.12.0**, neutral theme, Arial/sans-serif, 18px source font, white background. Renderer dependencies belong outside the repository; they are not application dependencies. Example in a temporary directory (Chromium must be installed or supplied):

```sh
PUPPETEER_SKIP_DOWNLOAD=true npm install --prefix /tmp/sc-diagrams @mermaid-js/mermaid-cli@11.12.0
```

Write temporary JSON files (not application configuration):

- Puppeteer config: `{"executablePath":"/path/to/chromium","args":["--no-sandbox"]}`. The sandbox flag was used in this isolated environment; adapt it to your local Chromium security setup.
- Base Mermaid config: `{"theme":"neutral","fontFamily":"Arial, sans-serif","fontSize":18,"htmlLabels":false,"flowchart":{"htmlLabels":false,"curve":"linear","nodeSpacing":28,"rankSpacing":38,"padding":16}}`.
- Architecture config: same base JSON with top-level `"layout":"elk"` for its more compact routing. Other diagrams use the base layout.

From repository root:

```sh
for source in docs/diagrams/*.mmd; do
  config=/tmp/sc-diagrams-mermaid.json
  if [ "$source" = docs/diagrams/system-architecture.mmd ]; then config=/tmp/sc-diagrams-elk.json; fi
  /tmp/sc-diagrams/node_modules/.bin/mmdc -i "$source" -o "${source%.mmd}.svg" -p /tmp/sc-diagrams-puppeteer.json -c "$config" -b white
done
```

Verification in this iteration: all five sources parsed and rendered via Mermaid/Chromium; all five exported SVGs were opened in Chromium and visually inspected. XML, local links, seven-table/two-FK schema identity and documentation-only scope were checked. Existing application regression evidence is reused, not rerun or reattributed. Source versions are in [submission baseline](../final/FINAL_SUBMISSION_BASELINE.md); historical [Iteration 6A](../integration/ITERATION_6A.md), [6B](../integration/ITERATION_6B.md), [7](../testing/ITERATION_7.md) and [11](../final/ITERATION_11_FINAL_VERIFICATION.md) retain their original observations. Older six-confirmation/index-discovery descriptions are historical, not the current one-confirmation/direct-read model shown here.
