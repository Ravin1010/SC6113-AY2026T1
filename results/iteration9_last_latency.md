# Final latency transport characterization

Baseline `8fdb117e33cebdad69784938408f45e204984f26`. Real Web3 7.14 transport/middleware/ABI pipeline with a synthetic in-memory RPC and 5 ms delay per HTTP envelope; warmed static proof; no public-chain or hosted timing claim.
| Action | Logical messages before → after | HTTP transports before → after | ms before → after |
|---|---:|---:|---:|
| transfer | 12 → 10 | 8 → 5 | 59.15 → 42.02 |
| deposit | 12 → 8 | 10 → 5 | 65.48 → 38.83 |
| withdraw | 12 → 8 | 10 → 5 | 65.8 → 38.11 |
| claim | 11 → 9 | 8 → 5 | 58.35 → 39.02 |
| cancel | 11 → 9 | 8 → 5 | 55.78 → 40.1 |
| authorizeSender | 12 → 8 | 10 → 5 | 64.98 → 37.54 |
| pause | 9 → 7 | 7 → 5 | 49.33 → 37.91 |
| balances | 9 → 7 | 7 → 4 | 50.9 → 32.69 |

The CSV records every actual wire-method group, including middleware chain checks. Fresh latest header, chain identity, same-block dynamic validation, simulation/gas and final hash fence all remain. Cold proof is intentionally outside warm measurements.
