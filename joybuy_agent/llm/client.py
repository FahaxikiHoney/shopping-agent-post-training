# -*- coding: utf-8 -*-
"""
LLMClient — 调用 LLM API 生成回复，同时收集 raw_thinking。

各模型行为说明：
  JoyAI-LLM-Flash    : content=正文，reasoning_content=空，无思维链
  GLM-5.1            : content=空，reasoning_content=思维链（有system时全在rc里）
  OxygenLLM-35B-A3B  : content=思维链(英文)+正文(中文)，reasoning_content=空
  OxygenLLM-122B-A10B: 同上，但冷启动慢/不稳定
  DeepSeek-V4-Flash  : content=正文，reasoning_content=空，无思维链
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Tuple


class LLMClient:

    def __init__(
        self,
        model: str = "JoyAI-LLM-Flash",
        api_url: str | None = None,
        token: str | None = None,
    ) -> None:
        self.model = model
        self.api_url = api_url or os.environ.get("LLM_API_URL", "https://api.example.com/v1/chat/completions")
        self.token = token or os.environ.get("LLM_API_KEY", "")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Tuple[str, str]:
        """
        流式调用 LLM。

        Returns:
            (content, raw_thinking)
            - content:     最终给用户的回复文本
            - raw_thinking: 思维链（reasoning_content 或从 content 中提取）
        """
        # GPT-5.6-Luna 使用 /v1/responses 接口，格式不同
        _RESPONSES_MODELS = {"GPT-5.6-Luna-joybuilder", "GPT-5.6-Luna"}
        if self.model in _RESPONSES_MODELS:
            return self._generate_responses_api(system_prompt, user_prompt, max_tokens)

        # 有思维链的模型：不限制 max_tokens，让模型自然输出完整内容
        _THINKING_MODELS = {"GLM-5.1", "GLM-5", "GLM-5.2",
                            "OxygenLLM-122B-A10B", "OxygenLLM-35B-A3B",
                            "DeepSeek-R1"}
        # DeepSeek-V4-Flash 支持可选 thinking 参数
        _V4_FLASH_THINKING = {"DeepSeek-V4-Flash"}
        if self.model in _THINKING_MODELS:
            max_tokens = None  # 不传 max_tokens，由模型自己决定

        # 构建 payload，max_tokens 为 None 时不传该字段
        payload_dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            payload_dict["max_tokens"] = max_tokens
        # DeepSeek-V4-Flash 开启思考模式
        if self.model in _V4_FLASH_THINKING:
            payload_dict["thinking"] = {"type": "enabled", "budget_tokens": 3000}
        payload = json.dumps(payload_dict).encode("utf-8")

        req = urllib.request.Request(
            self.api_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST",
        )

        chunks: list[str] = []
        reasoning_chunks: list[str] = []

        with urllib.request.urlopen(req, timeout=180) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                ct = delta.get("content")
                rc = delta.get("reasoning_content") or delta.get("thinking")  # 兼容 V4-Flash thinking 字段
                if ct:
                    chunks.append(ct)
                if rc:
                    reasoning_chunks.append(rc)

        raw_thinking = "".join(reasoning_chunks).strip()
        result = "".join(chunks).strip()

        # ── DeepSeek-R1 ──────────────────────────────────────────────
        # content 里用 <think>...</think> 包裹思维链，后面是正文
        if "<think>" in result:
            import re as _re
            m = _re.search(r'<think>([\s\S]*?)</think>\s*([\s\S]*)', result)
            if m:
                raw_thinking = m.group(1).strip()
                result = m.group(2).strip()
            else:
                # </think> 没有闭合（截断），取 <think> 前面作为正文（可能为空）
                idx = result.find("<think>")
                raw_thinking = result[idx + len("<think>"):].strip()
                result = result[:idx].strip()

        # ── OxygenLLM 系列 ──────────────────────────────────────────
        # content = 英文思维链（Thinking Process:...）+ 中文正文混合
        # 找第一个「连续换行后紧跟中文字符」作为正文起点
        if result and (result.startswith("Thinking Process:") or
                       result.startswith("Thinking process:") or
                       result.startswith("Here's a thinking")):
            m = re.search(r'\n{2,}([一-鿿])', result)
            if m:
                raw_thinking = result[:m.start()].strip()
                result = result[m.start():].strip()
            else:
                # tokens 不够，正文还没生成，全部当 thinking
                raw_thinking = result
                result = ""

        # ── GLM-5.1 / GLM-5 ─────────────────────────────────────────
        # reasoning_content = 思维链（content 永远为空）
        # 通过 ===FINAL=== 分隔符提取正文（prompt 里已要求输出此分隔符）
        if not result and raw_thinking:
            import re as _re
            import textwrap as _tw

            # 策略1：===FINAL=== 分隔符（最可靠，prompt里要求输出）
            # GLM有时把它包在反引号里，所以匹配时兼容 `===FINAL===` 和 ===FINAL===
            for sep in ["===FINAL===", "`===FINAL===`", "===FINAL==="]:
                idx = raw_thinking.rfind(sep)
                if idx != -1:
                    result = _tw.dedent(raw_thinking[idx + len(sep):]).strip()
                    # 去掉可能残留的开头 ===FINAL=== 或反引号
                    result = result.lstrip("`").strip()
                    if result.startswith("===FINAL==="):
                        result = result[len("===FINAL==="):].strip()
                    raw_thinking = raw_thinking[:idx].strip()
                    break

            # 策略2：最后一个步骤编号 + 润色/重写关键词后的正文
            if not result:
                m = _re.search(
                    r'\d+\.\s*\*{0,2}(?:重新计算|最终输出|润色|生成回复|撰写|最终回复|输出回复|最终草稿|最终版本)[^：:]*[：:]\s*\n+([\s\S]+)$',
                    raw_thinking
                )
                if m:
                    result = _tw.dedent(m.group(1)).strip()

            # 策略3：最后一个 Word count 后的正文
            if not result:
                wc_idx = raw_thinking.rfind("Word count")
                if wc_idx != -1:
                    after_wc = raw_thinking[wc_idx:]
                    m = _re.search(r'Word count[^\n]*\n\s+([\s\S]+)$', after_wc)
                    if m:
                        candidate = _tw.dedent(m.group(1)).strip()
                        candidate = _re.sub(r'\s*\(\d+\)\s*\n', '\n', candidate)
                        if len(candidate) > 100:
                            result = candidate

            # 策略4：最后一个「您好！/根据您」开头的完整段落
            if not result:
                m = _re.search(
                    r'\n{2,}((?:您好[！!]|根据您|为您整理|针对您)[\s\S]{200,})$',
                    raw_thinking
                )
                if m:
                    result = _tw.dedent(m.group(1)).strip()

            # fallback
            if not result:
                result = raw_thinking

        # 去掉可能残留的标记前缀
        for prefix in ["[RESPONSE]", "===FINAL===", "`===FINAL===`"]:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()
        result = result.lstrip("`").strip()

        return result, raw_thinking

    def _generate_responses_api(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
    ) -> Tuple[str, str]:
        """调用 /v1/responses 接口（GPT-5.6-Luna 系列）"""
        responses_url = self.api_url.replace("/chat/completions", "/responses")
        payload = json.dumps({
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "stream": False,
            "max_output_tokens": max_tokens,
        }).encode("utf-8")

        req = urllib.request.Request(
            responses_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())

        # 取正文（跳过 reasoning 类型，找 message 类型）
        try:
            text = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    text = item["content"][0]["text"]
                    break
        except (KeyError, IndexError):
            text = ""

        return text.strip(), ""
