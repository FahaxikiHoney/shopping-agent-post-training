# Third-party notices

The project integrates or redistributes third-party software. Each component remains subject to its own license; check the license file shipped with that component before modifying or redistributing it.

| Component | Location/use | License or terms |
|---|---|---|
| LLaMA-Factory fork | `LLaMA-Factory/` | Apache-2.0; see [`LLaMA-Factory/LICENSE`](LLaMA-Factory/LICENSE) and included notices. |
| slime | External runtime dependency for RL examples | See [upstream repository](https://github.com/THUDM/slime) for current source and license. Not bundled as source here. |
| Megatron-LM | External runtime dependency | See [upstream repository](https://github.com/NVIDIA/Megatron-LM) for current source and license. Not bundled as source here. |
| SGLang | External runtime dependency | See [upstream repository](https://github.com/sgl-project/sglang) for current source and license. Not bundled as source here. |
| Model checkpoints | Downloaded separately by users | Governed by the exact model card and license. No model weights are included. |
| Included datasets | `sft_data/`, `LLaMA-Factory/llamafactory/`, and `slime_joybuy_rl/data/` | Not covered automatically by the root MIT code license. The maintainer must provide dataset-specific terms and provenance before release. |

The top-level MIT license covers the original project code only, except where a file or directory contains its own license or third-party notice. When in doubt, follow the more specific license shipped with the component.
