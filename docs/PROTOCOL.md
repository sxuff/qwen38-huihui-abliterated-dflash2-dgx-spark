# Experimental protocol

## Primary operator question

How much does SGLang + DFlash2 accelerate the same abliterated Huihui-RadixArk NVFP4 target on one NVIDIA GB10?

The public result combines two configuration-matched sessions:

- No speculation: **12.31 tok/s**
- SGLang + DFlash2: **57.95 tok/s**
- Ratio: **4.71×**

The no-spec follow-up held the following constant:

- Exact target checkpoint and revision
- Exact runtime image ID
- Exact fixture bytes and sampler
- Exact context, memory, attention, Mamba, and scheduler settings
- Exact served-model identity and request count

The treatment removed the speculative algorithm, draft path, and draft-token flags. Both sessions used three repetitions across nine fixtures, with 27 rows and 18 declared performance rows. The sessions were collected separately, so the ratio is a matched-configuration historical-session comparison rather than a same-session paired estimate.

Required integrity checks:

- 27/27 unique requests complete with zero runtime errors
- Exactly 18 finite positive performance rows
- Positive completion-token counts and expected finish reasons
- Exact served-model identity in every stream
- At least 23/27 frozen automatic-quality passes
- At least 15 GiB `MemAvailable`
- At most 512 MiB swap growth
- No speculative flags in the no-spec launch receipt
- Positive verification-call delta and nonzero acceptance in DFlash2 mode
- Exact production model discovery and generation canary after restoration

The no-spec receipt is [`evidence/huihui-nospec-study.json`](../evidence/huihui-nospec-study.json). The qualified DFlash2 summary is [`results/summary.json`](../results/summary.json).

## Supporting qualification protocol

The original frozen protocol asked whether the fuller Huihui ModelOpt NVFP4 target materially beat the deployed Aday DFlash2 target. It intentionally collected one new DFlash2 arm against an immutable historical control:

- Candidate: exact `edp1096/Huihui-RadixArk-Qwen3.8-27B-abliterated-NVFP4` revision in `manifests/target.json`
- Historical control: output-redacted Aday DFlash2 rows in `controls/aday-dflash2-control.json`
- Runtime control: exact shared image ID `sha256:d551df08e966aee2fbac67c231f4c7dfad291b02d3b5e59f082f753c85cd33dd`
- Matching DFlash2 draft, fixtures, sampler, request count, and metric definition
- Payload equivalence after removing only the required `model` request field
- Positive DFlash verification-call delta during measured rows
- Promotion threshold: at least 1.10× the historical median and at least 23/27 quality passes

That study measured **41.44 tok/s to 57.95 tok/s** and passed every frozen gate. Its machine-readable contract remains [`protocol.json`](../protocol.json), and its original generated report is preserved at [`evidence/promotion-report-v3.md`](../evidence/promotion-report-v3.md).

The supporting qualification explains why the checkpoint was promoted. The primary repository claim is now the same-target **12.31 to 57.95 tok/s, 4.71×** DFlash2 acceleration.
