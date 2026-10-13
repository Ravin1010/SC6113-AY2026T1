# Final controlled preparation/read characterization

Baseline: 558fb854168a355f8373e60272ebe53c09e56c7c. Five ms emulated round-trip wait; 11 remittances, empty-event history. Logical messages differ from transports. No hosted timing claims.
| Implementation / operation | Messages | Round trips | Elapsed ms |
|---|---:|---:|---:|
| before dashboard /api/users/me | 26 | 25 | 129.72 |
| before dashboard /api/users/me/balances | 9 | 7 | 36.89 |
| before dashboard /api/remittances | 29 | 8 | 42.14 |
| before dashboard /api/transactions | 16 | 15 | 80.12 |
| before warm /api/transactions/prepare/transfer | 13 | 10 | 54.19 |
| before warm /api/transactions/prepare/deposit | 11 | 9 | 47.98 |
| before warm /api/transactions/prepare/withdraw | 12 | 10 | 52.93 |
| before warm /api/transactions/prepare/claim | 13 | 10 | 53.01 |
| before warm /api/transactions/prepare/cancel | 13 | 10 | 53.46 |
| before warm /api/transactions/prepare/authorizeSender | 12 | 10 | 53.55 |
| before warm /api/receipt | 10 | 9 | 47.29 |
| after dashboard /api/users/me | 26 | 25 | 130.88 |
| after dashboard /api/users/me/balances | 9 | 7 | 37.32 |
| after dashboard /api/remittances | 29 | 8 | 43.53 |
| after warm /api/transactions/prepare/transfer | 12 | 8 | 43.01 |
| after warm /api/transactions/prepare/deposit | 10 | 8 | 42.54 |
| after warm /api/transactions/prepare/withdraw | 10 | 8 | 42.81 |
| after warm /api/transactions/prepare/claim | 11 | 8 | 42.59 |
| after warm /api/transactions/prepare/cancel | 11 | 8 | 42.46 |
| after warm /api/transactions/prepare/authorizeSender | 10 | 8 | 42.73 |
| after warm /api/receipt | 8 | 8 | 41.95 |
| after cached SQLite HTTP /api/transactions | 0 | 0 | 1.17 |

After /api/transactions is DB-only: zero RPC messages/round trips. Explicit POST sync retains bounded historical indexing separately. Before dashboard readiness awaited indexed Activity; after readiness excludes Activity.
Browser performance evidence, including local input validation and confirmation-visible latency, is recorded separately by tests/frontend.cjs when FRONTEND_PERF_OUTPUT is set.
Middleware/provider-specific calls, Turso/network latency, wallet approval and Sepolia block inclusion are outside this fixture.
