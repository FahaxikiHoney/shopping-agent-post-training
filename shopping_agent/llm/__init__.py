# -*- coding: utf-8 -*-
from shopping_agent.llm.client import LLMClient
from shopping_agent.llm import prompts

# 模型实测（2026-07）
# JoyAI-LLM-Flash      ~1s    content正常  无思维链
# DeepSeek-R1          ~40s   <think>中文思维链 + 正文，100%准确分离 ★★★
# GLM-5.1              ~100-300s reasoning_content中文思维链 + ===FINAL===提取正文
# OxygenLLM-35B-A3B    ~3s    content混thinking（英文），思维链太长吃完tokens不稳定
# DeepSeek-V4-Flash    ~30s   content正常  无思维链

# 快速生产（无思维链）
LLM_FAST = LLMClient(model="JoyAI-LLM-Flash")

# 思维链首选（DeepSeek-R1：<think>标签100%准确分离，速度适中）
LLM_THINKING = LLMClient(model="DeepSeek-R1")

# GLM-5.1（备选，思维链更长但速度慢）
LLM_THINKING_GLM = LLMClient(model="GLM-5.1")

# 批量生成轮询池
LLM_POOL = [
    LLMClient(model="DeepSeek-R1"),
    LLMClient(model="DeepSeek-R1"),
    LLMClient(model="DeepSeek-R1"),
]

def make_agent_with_thinking(registry, AgentClass):
    """创建带思维链的 Agent（默认 DeepSeek-R1 单模型）"""
    return AgentClass(registry, llm_client=LLM_THINKING)

__all__ = [
    "LLMClient", "prompts",
    "LLM_FAST", "LLM_THINKING", "LLM_THINKING_GLM",
    "LLM_POOL", "make_agent_with_thinking",
]
