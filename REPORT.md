# Huihui-RadixArk NVFP4-lm_head DFlash2 validation

**Promotion verdict: PROMOTE.**

One candidate arm versus a frozen historical control. Exact runtime image, fixtures, sampler, draft, and normalized payload fields match; collection sessions differ.

- Historical Aday DFlash2: **41.44 tok/s**
- Candidate DFlash2: **57.95 tok/s**
- Historical-control ratio: **1.40x**
- Automatic quality: **24/27 candidate** versus **23/27 historical**
- Exact outputs across different targets: **14/27**
- Completion-token count matches: **14/27**
- Measured DFlash verification-call delta: **1310**
- DFlash final acceptance: **0.5785714285714286 rate**, **5.05 tokens**
- Minimum MemAvailable: **27.76 GiB**
- Maximum swap growth: **0 bytes**

## Per-fixture median whole-request tok/s

| Fixture | Historical Aday | Candidate | Ratio |
|---|---:|---:|---:|
| code | 50.15 | 66.82 | 1.33x |
| copy_json | 70.58 | 72.43 | 1.03x |
| copy_python | 68.85 | 70.66 | 1.03x |
| json | 30.29 | 30.95 | 1.02x |
| literal | 9.22 | 12.54 | 1.36x |
| math | 41.37 | 52.30 | 1.26x |
| prose | 22.69 | 21.55 | 0.95x |
| reasoning | 49.41 | 43.23 | 0.87x |
| tool | 39.92 | 40.09 | 1.00x |

Promotion requires every preregistered lineage, denominator, model-identity, payload, speed, quality, measured-DFlash, and memory gate to pass.
