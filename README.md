# Qwen3.8-27B Huihui abliterated NVFP4-lm_head + DFlash2 on one DGX Spark

A pinned, single-arm validation of `edp1096/Huihui-RadixArk-Qwen3.8-27B-abliterated-NVFP4` with the same SGLang + DFlash2 runtime previously exercised on the ARA-abliterated checkpoint.

The candidate quantizes the `lm_head` and all 192 language-model MLP projections to NVFP4 W4A4. The earlier Aday artifact kept its `lm_head` in BF16. This study tests whether the fuller ModelOpt packing recovers DFlash2 throughput without regressing the frozen automatic-quality workload.

## Status

**Qualified and deployed.** The formal promotion gate used the exact-image Aday control and passed every frozen requirement. For the public speed comparison, the primary baseline is the measured stock RadixArk checkpoint, not Aday ARA.

![Measured result](assets/qwen38-huihui-radixark-result.png)

| DFlash2 target | Median whole-request rate | Draft acceptance | Mean committed tokens per verification | Frozen automatic quality |
|---|---:|---:|---:|---:|
| Stock RadixArk | 57.11 tok/s | 42.14% | 3.95 | 24/27 |
| **Huihui-RadixArk abliterated** | **57.95 tok/s** | **57.86%** | **5.05** | **24/27** |
| Aday ARA abliterated, secondary reference | 41.44 tok/s | 70.71% | 5.95 | 23/27 |

Huihui measured **1.46% above stock**, which is best described as **stock-level speed** because the runs came from separate study sessions and used different final image IDs. The **1.40×** figure applies only to Huihui versus the Aday ARA control.

### Is 57.86% acceptance bad?

No. SGLang defines acceptance rate as accepted draft tokens divided by proposed draft tokens, excluding the target model's bonus token. With eight configured DFlash tokens, seven are draft proposals. Huihui accepted an average of **4.05 of those seven drafts**, then committed the target bonus token, for **5.05 output tokens per verification step**.

Acceptance is an efficiency diagnostic, not a quality score or a request-success rate. Huihui's **57.86%** is 15.71 percentage points above stock's **42.14%**, while its whole-request throughput is effectively tied with stock. Aday ARA reached a higher **70.71%** acceptance rate but only **41.44 tok/s**, showing why acceptance cannot be interpreted alone. End-to-end speed also depends on target-model execution cost, draft overhead, response trajectories, kernels, and memory behavior.

Operational evidence for Huihui:

- Runtime errors: **0/27**
- Exact response-model identity: **27/27**
- Normalized payload matches against the formal Aday control: **27/27**
- Measured DFlash verification-call delta: **1,310**
- Minimum host `MemAvailable`: **27.76 GiB**
- Swap growth: **0 bytes**

The exact post-hoc stock, Huihui, and Aday values and source-summary hashes are in [`evidence/cross-study-comparison.json`](evidence/cross-study-comparison.json). Stock and Huihui used identical fixture bytes, sampler settings, DFlash2 draft revision, SGLang base commit, base image digest, and overlay file hashes. Their final image IDs and collection sessions differ, so the stock comparison is a public reference rather than the preregistered promotion control.

The formal control remains the completed, output-redacted Aday DFlash2 arm from [`sxuff/qwen38-27b-abliterated-nvfp4-dflash2-dgx-spark`](https://github.com/sxuff/qwen38-27b-abliterated-nvfp4-dflash2-dgx-spark), pinned in [`controls/aday-dflash2-control.json`](controls/aday-dflash2-control.json). It preserves the original promotion decision without making Aday the headline baseline.

## Frozen promotion gates

The candidate must satisfy all of these:

- 27/27 unique requests complete with zero runtime errors.
- Every normalized request payload hash matches the historical control after removing only the required `model` identifier. Full payload hashes must differ because the served model names differ.
- Median whole-request completion rate is at least 1.10× the historical Aday DFlash2 result of 41.4351 tok/s.
- At least 23/27 frozen automatic-quality checks pass, matching or exceeding the historical control.
- All 18 performance rows have finite positive rates, all 27 rows have positive completion-token counts and expected finish reasons, and every stream reports the exact candidate model alias.
- DFlash2 records a positive verification-call delta during the 27 measured requests, acceptance length greater than one, and nonzero acceptance rate.
- Host `MemAvailable` remains at least 15 GiB.
- Swap growth remains at or below 512 MiB.

The full contract is in [`protocol.json`](protocol.json).

## Pinned components

- Candidate: `edp1096/Huihui-RadixArk-Qwen3.8-27B-abliterated-NVFP4@21565d389fe573a32c1c425e0c7ade204ddb2263`
- Behavioral source: `huihui-ai/Huihui-Qwen3.8-27B-abliterated`
- DFlash2 draft: `z-lab/Qwen3.8-27B-DFlash2@50307d4c4cde6860d4eee73e2547cd786fe8e8a4`
- Benchmark runtime image: exact historical control `sha256:d551df08e966aee2fbac67c231f4c7dfad291b02d3b5e59f082f753c85cd33dd`
- Candidate-labeled image built as an attribution check: `sha256:b1dc79ca75f22c3f12e53cd096880a116ca80bcd97a66dab151dc78170831512`. The qualified service deliberately reuses the exact benchmark image above so runtime identity remains matched.
- Hardware: one NVIDIA DGX Spark GB10

## Precision policy

Verified against the pinned Hub configuration and model index:

| Component | Precision |
|---|---|
| 192 language-model MLP projections | NVFP4 W4A4, group size 16 |
| `lm_head` | NVFP4 W4A4, group size 16 |
| 208 attention and Gated DeltaNet projections | FP8 |
| Vision tower | BF16 |
| MTP tensors | BF16 |

The inspection receipt is [`evidence/candidate-inspection.json`](evidence/candidate-inspection.json) and is independently reproduced offline by `scripts/inspect_candidate.py` from the pinned Hub metadata included in `evidence/hub-metadata/`.

## Download and verify

```bash
python3 scripts/download.py target \
  --destination "$HOME/models/Huihui-RadixArk-Qwen3.8-27B-abliterated-NVFP4-21565d389fe5/snapshot" \
  --reserve-gib 8

python3 scripts/download.py draft \
  --destination "$HOME/models/Qwen3.8-27B-DFlash2-50307d4c4cde"
```

Every expected file, byte count, and SHA-256 digest is frozen in `manifests/` and checked before launch.

## Run the one-arm validation

```bash
MODEL_DIR=/path/to/candidate/snapshot \
DRAFT_DIR=/path/to/pinned/dflash2/draft \
RUN_ROOT="$PWD/private/primary" \
./scripts/run_study.sh
```

The runner temporarily stops the current Aday model, launches the candidate under a disjoint study-owned container name, collects only `candidate-dflash2`, then restores and generation-tests the previous authenticated service regardless of pass or failure. Promotion is a separate, reversible step.

## Install the qualified service

Benchmark and production use the exact historical runtime image. Its executable root filesystem is identical to the candidate-labeled image; target identity is instead enforced through the hash-verified mounted checkpoint, served-model receipt, and deployment canaries.

```bash
QWEN38_PROXY_KEY_FILE="$HOME/.config/qwen38/proxy.key" ./scripts/install_service.sh
systemctl --user enable --now \
  qwen38-huihui-radixark-dflash2.service \
  qwen38-huihui-radixark-dflash2-proxy.service
```

SGLang binds only to `127.0.0.1:8002`. The Docker-bridge client endpoint at `172.17.0.1:8001` requires bearer authentication.

## Metric

The primary rate is completion tokens divided by whole request wall time. It includes prefill and first-token latency. Streaming chunks may contain multiple speculative tokens, so the repository does not infer a synthetic post-first-token decode rate from chunk arrival times.

## Reproduce repository checks

```bash
./scripts/ci.sh
```

## License and attribution

Repository-authored material is MIT-licensed. The SGLang compatibility overlay remains under Apache-2.0; see [`NOTICE`](NOTICE) and [`THIRD_PARTY_LICENSES/Apache-2.0.txt`](THIRD_PARTY_LICENSES/Apache-2.0.txt). Model weights are not redistributed here.

Model and method lineage: Huihui AI supplies the abliterated behavioral source. The target card credits RadixArk's Qwen3.8 NVFP4 work and sakamakismile's Huihui NVFP4 reference. z-lab publishes the DFlash2 draft, based on DFlash2 by Inco AI. Exact links and revisions are listed in `NOTICE`.
