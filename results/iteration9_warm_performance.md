# Second controlled verified-read characterization

Baseline `bd571500c73690bd2a58a991d49fded4bb025ac9`; 11 remittances, empty-event history, 5 ms wait per controlled network round trip.
Offline transport grouping is emulated; real Web3 ABI/strict batch protocol and actual local-EVM integration are separately tested. These are not hosted timing results. Middleware/provider-specific additional calls and network/Turso transport are outside this fixture.
Cold means full proof per operation; warm means one priming proof excluded; dashboard means cold account followed by warm sequential financial/activity operations.

| Mode / endpoint | Messages before → after | Round trips before → after | ms before → after |
|---|---:|---:|---:|
| cold /api/users/me | 26 → 26 | 26 → 25 | 135.39 → 130.38 |
| cold /api/users/me/balances | 26 → 26 | 26 → 25 | 136.31 → 130.8 |
| cold /api/users/roles/<wallet> | 26 → 26 | 26 → 25 | 135.48 → 131.36 |
| cold /api/remittances | 46 → 46 | 46 → 26 | 239.75 → 135.53 |
| cold /api/transactions | 33 → 33 | 33 → 33 | 174.91 → 173.47 |
| cold /api/transactions/prepare | 31 → 30 | 31 → 28 | 163.63 → 148.34 |
| warm /api/users/me | 16 → 9 | 16 → 7 | 83.01 → 37.19 |
| warm /api/users/me/balances | 16 → 9 | 16 → 7 | 84.23 → 39.75 |
| warm /api/users/roles/<wallet> | 16 → 9 | 16 → 7 | 83.56 → 37.37 |
| warm /api/remittances | 36 → 29 | 36 → 8 | 186.99 → 42.54 |
| warm /api/transactions | 23 → 16 | 23 → 15 | 122.9 → 80.44 |
| warm /api/transactions/prepare | 21 → 13 | 21 → 10 | 110.23 → 53.53 |
| dashboard /api/users/me | 26 → 26 | 26 → 25 | 135.78 → 139.24 |
| dashboard /api/users/me/balances | 16 → 9 | 16 → 7 | 84.1 → 37.46 |
| dashboard /api/remittances | 36 → 29 | 36 → 8 | 186.86 → 42.39 |
| dashboard /api/transactions | 23 → 16 | 23 → 15 | 121.31 → 80.3 |

Full static proofs: one per cold operation; zero per warm operation; one per dashboard sequence. Warm runtime-code/historical-deployment anchor reads: previous 3/4 each; now 0/0. Current head/hash/chain checks remain fresh.
CSV includes contract-call, chain-ID, block-read, batch transport and full method breakdown. Historical indexing reconciliation work is unchanged.
