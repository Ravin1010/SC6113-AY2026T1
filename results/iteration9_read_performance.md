# Controlled verified-read characterization

Baseline: `324a0f913b432ae0b0746f5ade5128860fbf303b`. Synthetic RPC fixture; 11 remittances, empty-event historical catch-up; 5 ms injected per counted RPC operation.
Counts cover the verified-reader and endpoint operation, not authentication/HTTP/Turso transport. First account request is cold; subsequent requests share verified static evidence. No public RPC or new transactions.

| Endpoint | Before RPC | After RPC | Before full verify | After full verify | Before ms | After ms |
|---|---:|---:|---:|---:|---:|---:|
| /api/users/me | 26 | 26 | 1 | 1 | 133.81 | 134.77 |
| /api/users/me/balances | 26 | 16 | 1 | 0 | 134.23 | 83.29 |
| /api/remittances | 56 | 36 | 1 | 0 | 287.48 | 185.01 |
| /api/transactions | 33 | 23 | 1 | 0 | 173.31 | 120.65 |
| /api/transactions/prepare | 31 | 21 | 1 | 0 | 161.65 | 108.95 |

Warm reads still fetch runtime bytes, chain ID, historical/verification anchors, fresh snapshot, pause/count and endpoint-specific state. A 60-second expiry/restart/input change reruns full proof.
These measured local numbers are not hosted speed claims. Real RPC latency, remittance scanning, index catch-up and synchronous dashboard ordering remain limitations.
