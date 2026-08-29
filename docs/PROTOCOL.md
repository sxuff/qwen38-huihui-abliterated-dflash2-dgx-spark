# Experimental protocol

This repository runs one new DFlash2 candidate arm on one NVIDIA GB10 and compares it with an immutable historical DFlash2 control.

- Candidate: exact `edp1096/Huihui-RadixArk-Qwen3.8-27B-abliterated-NVFP4` revision in `manifests/target.json`.
- Historical control: exact output-redacted Aday DFlash2 rows in `controls/aday-dflash2-control.json`.
- Runtime control: candidate and historical arm use exact image ID `sha256:d551df08e966aee2fbac67c231f4c7dfad291b02d3b5e59f082f753c85cd33dd`.
- DFlash2 draft, fixtures, sampler, request count, and metric definition match the prior arm.
- Payload equivalence removes only the required `model` request field. Full hashes must differ because the served model identifiers differ.
- Candidate collection: three repetitions across nine fixtures, 27 rows total.
- Performance aggregate: exactly 18 finite positive rows across copy-Python, copy-JSON, code, JSON, math, and prose.
- Every row must have positive completion tokens, an expected finish reason, a raw-stream digest, and the exact candidate response-model alias.
- DFlash activation requires a positive verification-call delta between metrics captured immediately before and after the 27 measured requests.
- Safety: at least 15 GiB `MemAvailable`; at most 512 MiB swap growth.
- Promotion: at least 1.10× the historical median, at least 23/27 automatic-quality passes, no errors, all lineage and denominator gates, matching normalized payload hashes, active measured DFlash2, and passed memory gates.
- Displaced service: exact model discovery and generation canary before stop, then exact identity and generation canary after restoration.

This design intentionally avoids rerunning no-spec. It answers the operator question: does the fuller ModelOpt NVFP4 target materially beat the currently deployed DFlash2 target? It does not estimate the candidate's no-spec speedup and is not a same-session paired comparison.

The machine-readable frozen contract is [`protocol.json`](../protocol.json).
