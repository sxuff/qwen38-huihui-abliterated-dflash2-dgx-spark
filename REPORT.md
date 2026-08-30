# Huihui-RadixArk DFlash2 on one DGX Spark

## Result

SGLang + DFlash2 increased the measured whole-request completion rate of the same abliterated Huihui-RadixArk target from **12.31 tok/s to 57.95 tok/s**, a **4.71×** acceleration.

| Mode | Median whole-request rate | Automatic quality | Runtime errors |
|---|---:|---:|---:|
| No speculation | 12.31 tok/s | 24/27 | 0/27 |
| SGLang + DFlash2 | **57.95 tok/s** | 24/27 | 0/27 |

The no-spec follow-up used the exact qualified image, checkpoint, fixture bytes, sampler, context allocation, memory settings, and SGLang arguments with speculative decoding removed. The two arms were collected in separate sessions, so 4.71× is a matched-configuration historical-session comparison rather than a same-session paired estimate.

## DFlash2 evidence

- Draft acceptance rate: **57.86%**
- Mean committed tokens per target verification: **5.05**
- Measured verification-call delta across the DFlash arm: **1,310**
- Complete requests: **27/27 per arm**
- Automatic quality: **24/27 in both modes**
- Runtime errors: **0 in both modes**
- Maximum swap growth: **0 bytes in both measured arms**
- No-spec launch receipt: no speculative algorithm or draft-model flags

With eight configured DFlash tokens, seven are draft proposals. The measured acceptance rate corresponds to 4.05 accepted draft tokens plus one target bonus token per verification step. Acceptance is an efficiency diagnostic, not a quality score.

## Stock reference

| Target | No speculation | SGLang + DFlash2 | DFlash2 ratio |
|---|---:|---:|---:|
| Stock RadixArk | 12.34 tok/s | 57.11 tok/s | 4.63× |
| **Huihui-RadixArk abliterated** | **12.31 tok/s** | **57.95 tok/s** | **4.71×** |
| Aday ARA abliterated | 12.33 tok/s | 41.44 tok/s | 3.36× |

Stock is the primary external reference. Huihui's DFlash2 rate is effectively stock-level, measuring 1.46% above stock across separate studies. This is not evidence of a controlled speedup over stock.

## Original qualification

Before the no-spec follow-up, the candidate was promoted against an immutable Aday DFlash2 control collected with the exact same runtime image. That frozen qualification measured **41.44 tok/s to 57.95 tok/s**, passed every preregistered lineage, identity, quality, DFlash-activation, and memory gate, and justified deployment. It is supporting qualification evidence, not the headline speed comparison.

The original machine-generated report is preserved at [`evidence/promotion-report-v3.md`](evidence/promotion-report-v3.md). Its frozen protocol remains [`protocol.json`](protocol.json), with the redacted control in [`controls/aday-dflash2-control.json`](controls/aday-dflash2-control.json).

## Evidence

- [`evidence/huihui-nospec-study.json`](evidence/huihui-nospec-study.json): public-safe no-spec summary and restoration receipt
- [`results/summary.json`](results/summary.json): qualified DFlash2 candidate summary
- [`evidence/cross-study-comparison.json`](evidence/cross-study-comparison.json): exact stock, Aday, and Huihui values with source hashes
- [`evidence/qualification.json`](evidence/qualification.json): frozen promotion gates
- [`assets/qwen38-huihui-radixark-result.png`](assets/qwen38-huihui-radixark-result.png): proof card

The production DFlash2 service was restored after the no-spec run and passed exact model discovery plus the `HUIHUI_DFLASH2_FINAL_OK` generation canary.
