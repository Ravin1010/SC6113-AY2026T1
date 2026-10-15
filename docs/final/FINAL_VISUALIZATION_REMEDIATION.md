# Final visualization remediation — SC6113

## Requirement and bounded implementation

The assignment requires a responsive dashboard with transaction history, event logs and relevant data visualizations. Existing cards/status/Activity presentation lacked a dedicated chart. **Remittance Status Overview** adds semantic HTML/CSS bars with visible PENDING, COMPLETED and CANCELLED labels/counts and a total.

The source is the **same already-loaded response** to `/api/remittances?limit=20&offset=0`: newest-first current page, up to 20; wallet-related records for ordinary users and broader visibility for Admin under existing API rules. It is not a complete-system statistic. Blockchain remains financial authority; the chart is presentation only. No additional API/RPC request, polling, cache, endpoint, dependency or data store was added. It re-renders in the existing list cycle and clears during loading, read failure and account invalidation. Unknown statuses are counted separately, never silently assigned to a known bar. Empty loaded data displays zero counts and an empty-state message; unavailable state hides the data instead of implying authoritative zeros.

Text labels and numeric counts convey meaning without color. Decorative bars are hidden from assistive technology; the definition list has an accessible label and the status message is a polite live region. Bars scale to the largest known status count, explicitly labelled, without percentage claims or animation.

## Implementation and accepted local verification

Implementation: `72eec24297a3925979c1573182c4edb09ad77dd1` — **Add remittance status visualization**. Files: `templates/main.html`, `static/js/live.js`, `static/styles.css`, `tests/frontend.cjs`.

| Check | Recorded result |
|---|---|
| Focused real-browser visualization tests | 12 passed: empty, each status alone, mixed/unknown, counts/bars, existing Refresh, account invalidation, failed read, request-count boundaries and four viewports |
| Full frontend/browser regression | 99 passed; zero failures/skips/cancellations |
| Python/backend regression | 214 passed; controlled rollback exception is an expected test fixture |
| Responsive checks | 320 / 360 / 768 / 1280px passed; labels/counts visible and no horizontal page overflow |
| Syntax | `node --check static/js/live.js` and `node --check tests/frontend.cjs` passed |
| Dependency/whitespace | `python -m pip check` and `git diff --check` passed |

These results were obtained during the implementation pass and reused here, not rerun or relabelled as hosted tests. Existing browser request assertions show account/balance/list/history reads remain one each for initial dashboard population. No costly contract/local-chain suite was rerun for this frontend-only addition; historical [Iteration 11](ITERATION_11_FINAL_VERIFICATION.md) results remain dated evidence.

## Exact deployment and hosted read-only verification — 15 October 2026

- Public URL: <https://sc6113-ay2026t1.onrender.com>
- Render service: `srv-dal7read0e5s738rldh0`.
- Live commit: `72eec24297a3925979c1573182c4edb09ad77dd1`.
- Live deploy: `dep-db8694ou01pc73emjnv0`; Render metadata reports **live**, completed 05:29:58 UTC.
- Owner performed manual exact-commit deployment. The generic connector deploy action was not used because it cannot select the commit and the configured branch differs. This continuation did not deploy again.
- Cloud-browser GET `/` and `/main` succeeded. Render access logs at approximately 05:35 UTC show HTTP 200; CSS and all six frontend modules loaded with 200/304. `/api/auth/session` returned the expected guest 401.
- Dashboard DOM contains the new heading, all three categories, explanatory scope, hidden data region and “Sign in to load remittance status counts.” Existing account/funding/remittance/Activity sections remain present. Guest session content stays hidden; no wallet was connected or signature requested.
- No application JavaScript exception was observed. Browser-extension metadata messages were unrelated to application source; optional `/favicon.ico` returned 404 (non-blocking). Direct scratch-browser navigation was unavailable; the cloud browser and Render logs supplied the successful hosted observations.
- Non-zero hosted counts were **not observed** because no authenticated wallet session was used. Controlled browser tests provide populated/unknown/refresh case coverage; no transaction was needed to populate a demonstration.

## Authority, scope and freeze

Exactly three roles (Sender, Recipient, Admin), three contracts and ten action types remain unchanged. Claim pays the Recipient wallet directly without crediting their Available deposited funds; Cancel restores the Sender's deposited availability. No Sepolia transaction was submitted for this remediation. No role grant/revocation, Solidity/ABI/address/manifest change, backend financial/API change, database schema/production-data change, RPC/environment/service configuration change or main merge occurred.

Limits: current page only, up to 20; no historical trend analytics, complete-system BI, new performance benchmark or production-financial suitability claim. This docs-only freeze follows the implementation; identify its exact documentation SHA from Git HEAD/history, not the live-runtime SHA above. Technical Report figure conversion/pagination is document work and does not alter this deployment.

**FINAL VISUALIZATION REMEDIATION — VERIFIED / FROZEN**
