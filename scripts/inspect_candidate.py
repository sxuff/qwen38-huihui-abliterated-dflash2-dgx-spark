#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPOSITORY = "edp1096/Huihui-RadixArk-Qwen3.8-27B-abliterated-NVFP4"
REVISION = "21565d389fe573a32c1c425e0c7ade204ddb2263"
BASE_MODEL = "huihui-ai/Huihui-Qwen3.8-27B-abliterated"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-root", type=Path, default=root / "evidence/hub-metadata")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    names = ["config.json", "hf_quant_config.json", "model.safetensors.index.json"]
    raw = {name: (args.metadata_root / name).read_bytes() for name in names}
    config = json.loads(raw["config.json"])
    quant = json.loads(raw["hf_quant_config.json"])
    index = json.loads(raw["model.safetensors.index.json"])
    layers = quant["quantization"]["quantized_layers"]
    counts: dict[str, int] = {}
    for spec in layers.values():
        algo = spec["quant_algo"]
        counts[algo] = counts.get(algo, 0) + 1
    lm_head = layers.get("lm_head")
    if lm_head != {"quant_algo": "NVFP4", "group_size": 16}:
        raise SystemExit(f"lm_head is not NVFP4 group-16: {lm_head}")
    if counts != {"FP8": 208, "NVFP4": 193}:
        raise SystemExit(f"unexpected quantized-layer counts: {counts}")
    weight_map = index["weight_map"]
    lm_keys = sorted(key for key in weight_map if key.startswith("lm_head"))
    mtp_keys = sorted(key for key in weight_map if key.startswith("mtp."))
    if "lm_head.weight_scale_2" not in lm_keys or len(mtp_keys) != 15:
        raise SystemExit("model index does not prove the expected lm_head scales and MTP tensors")

    receipt = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "revision": REVISION,
        "base_model": BASE_MODEL,
        "quant_method": config["quantization_config"]["quant_method"],
        "excluded_modules": config["quantization_config"]["ignore"],
        "quantized_layer_counts": counts,
        "lm_head_policy": lm_head,
        "lm_head_index_keys": lm_keys,
        "mtp_index_key_count": len(mtp_keys),
        "model_index_metadata": index["metadata"],
        "source_file_sha256": {name: hashlib.sha256(raw[name]).hexdigest() for name in names},
        "conclusion": "The pinned artifact uses ModelOpt NVFP4 W4A4 for lm_head and every language-model MLP, FP8 for attention/Gated DeltaNet projections, and retains BF16 vision and MTP tensors.",
    }
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
