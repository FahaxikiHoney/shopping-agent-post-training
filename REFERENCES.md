# References and acknowledgements

This repository combines its own shopping-agent environment, data preparation, evaluation, and training adapters with the following research and open-source projects. Cite the original work when using the corresponding method or software. The upstream repositories and papers have their own licenses and citation requirements.

## Software

- **LLaMA-Factory** — fine-tuning framework. This release includes a LLaMA-Factory fork; see [`LLaMA-Factory/LICENSE`](LLaMA-Factory/LICENSE) and its notices for the code included in that directory. [Upstream repository](https://github.com/hiyouga/LLaMA-Factory).
- **slime** — LLM post-training and RL framework used by the adapter examples. [Upstream repository](https://github.com/THUDM/slime).
- **Megatron-LM** and **SGLang** — external training and rollout dependencies used by the Slime examples. They are not vendored as source in this repository. [Megatron-LM](https://github.com/NVIDIA/Megatron-LM), [SGLang](https://github.com/sgl-project/sglang).

## Papers and methods

### LLaMA-Factory

```bibtex
@article{zheng2024llamafactory,
  title={LlamaFactory: Unified Efficient Fine-Tuning of 100+ Language Models},
  author={Zheng, Yaowei and Zhang, Richong and Zhang, Junhao and Ye, Yanhan and Luo, Zheyan and Ma, Yongqiang},
  journal={arXiv preprint arXiv:2403.13372},
  year={2024},
  url={https://arxiv.org/abs/2403.13372}
}
```

### Group Relative Policy Optimization (GRPO)

```bibtex
@article{shao2024deepseekmath,
  title={DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models},
  author={Shao, Zhihong and others},
  journal={arXiv preprint arXiv:2402.03300},
  year={2024},
  url={https://arxiv.org/abs/2402.03300}
}
```

### slime

The slime project provides this software citation:

```bibtex
@misc{slime_github,
  author       = {Zilin Zhu and Chengxing Xie and Xin Lv and slime Contributors},
  title        = {slime: An LLM post-training framework for RL Scaling},
  year         = {2025},
  howpublished = {\url{https://github.com/THUDM/slime}}
}
```

### Qwen3

The primary ChatML SFT configuration uses a Qwen2.5 model, while the ReAct example uses Qwen3. Follow the model card and license of the exact checkpoint you download. See the [Qwen2.5 Technical Report](https://arxiv.org/abs/2412.15115) and [Qwen3 Technical Report](https://arxiv.org/abs/2505.09388).

## Acknowledgements

Thanks to the maintainers and contributors of LLaMA-Factory, slime, Megatron-LM, SGLang, and the broader open-source ML community. This repository is an independent project and is not an official project of those upstream teams or of any retailer mentioned in sample data.
