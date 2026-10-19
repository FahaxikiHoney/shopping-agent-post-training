"""Run standalone SFT inference and save final Joybuy outputs.

This is intentionally separate from training. It loads the SFT model, asks the
model for a tool call, executes Joybuy mock tools, feeds back a train-style
<tool_response>, then asks for the final response.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from joybuy_agent.react.agent import ReActJoybuyAgent
from joybuy_agent.react.environment import JoybuyMockEnv
from joybuy_agent.react.tools import execute_tool
from slime_joybuy_rl.joybuy_slime.action_parser import parse_actions


SFT_TEST_SYSTEM_PROMPT = """You are a Joybuy shopping assistant.

Workflow:
- Before any product search result is available, output exactly one tool call.
- After a <tool_response> is available, write the final recommendation directly.
- Do not output <think> blocks, hidden reasoning, or internal tool planning in the final answer.
- If tool results contain products, the final answer must cite selected products with exact lowercase cards like [product:1].
- Use each product card at most once.
- Recommend only products grounded in the tool result fields.
- Keep the answer concise and use the same main language as the user.
"""


def iter_queries(path: Path | None, cli_queries: List[str], limit: int) -> Iterable[Dict[str, Any]]:
    count = 0
    for query in cli_queries:
        yield {
            "query": query,
            "scenario_type": "search_recommend",
            "site_code": "UK-Site",
            "task_id": f"cli_{count}",
        }
        count += 1
        if limit and count >= limit:
            return

    if path is None:
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")

    for index, item in enumerate(data):
        meta = item.get("_meta") or {}
        conversations = item.get("conversations") or []
        query = str(meta.get("user_query") or "").strip()
        if not query:
            for turn in conversations:
                if turn.get("from") in {"human", "user"}:
                    content = str(turn.get("value") or turn.get("content") or "").strip()
                    if not content.startswith("<tool_response>"):
                        query = content
                        break
        if not query:
            continue
        yield {
            "query": query,
            "scenario_type": str(meta.get("scenario_type") or "search_recommend"),
            "site_code": str(meta.get("site_code") or "UK-Site"),
            "task_id": str(meta.get("trajectory_id") or f"test_{index}"),
        }
        count += 1
        if limit and count >= limit:
            return


def load_model(model_path: str, adapter_path: str = "", dtype: str = "auto"):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[INFO] loading tokenizer: {model_path}", flush=True)
    torch_dtype = {
        "auto": "auto",
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }[dtype]
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    print(f"[INFO] loading model: {model_path}", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype=torch_dtype,
        trust_remote_code=True,
    )
    if adapter_path:
        from peft import PeftModel

        print(f"[INFO] loading LoRA adapter: {adapter_path}", flush=True)
        model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    print("[INFO] model ready", flush=True)
    return tokenizer, model


def generate_text(
    tokenizer,
    model,
    messages: List[Dict[str, str]],
    *,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    repetition_penalty: float,
    no_repeat_ngram_size: int,
) -> str:
    import torch

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    do_sample = temperature > 0
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=temperature if do_sample else None,
            top_p=top_p if do_sample else None,
            repetition_penalty=repetition_penalty,
            no_repeat_ngram_size=no_repeat_ngram_size,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = output_ids[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def run_one(
    tokenizer,
    model,
    task: Dict[str, Any],
    *,
    max_steps: int,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    repetition_penalty: float,
    no_repeat_ngram_size: int,
    strict_tool_first: bool,
) -> Dict[str, Any]:
    print(f"[INFO] testing: {task['query']}", flush=True)
    env = JoybuyMockEnv(max_steps=max_steps)
    env.reset(task)
    messages = [
        {"role": "system", "content": SFT_TEST_SYSTEM_PROMPT},
        {"role": "user", "content": _strict_tool_prompt(task["query"]) if strict_tool_first else task["query"]},
    ]
    model_outputs: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    tool_results: List[Dict[str, Any]] = []
    terminal = None

    for _ in range(max_steps):
        print(f"[INFO] generate step {len(model_outputs) + 1}/{max_steps}", flush=True)
        output = generate_text(
            tokenizer,
            model,
            messages,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            no_repeat_ngram_size=no_repeat_ngram_size,
        )
        print(f"[INFO] generated {len(output)} chars", flush=True)
        model_outputs.append(output)
        actions = parse_actions(output)
        tool_actions = [action for action in actions if action.get("type") == "tool_call"]

        if not tool_actions:
            terminal = env.step({"type": "final", "content": clean_final_output(output)})
            messages.append({"role": "assistant", "content": output})
            break

        messages.append({"role": "assistant", "content": output})
        response_blocks = []
        for action in tool_actions:
            normalized = _normalize_action(action)
            print(f"[INFO] tool_call: {normalized['name']} {normalized['arguments']}", flush=True)
            tool_calls.append(normalized)
            terminal = env.step(normalized)
            result = execute_tool(
                normalized["name"],
                normalized["arguments"],
                task.get("site_code") or "UK-Site",
            )
            tool_results.append({
                "name": normalized["name"],
                "arguments": normalized["arguments"],
                "result": result,
            })
            print(f"[INFO] tool_result products={len(result.get('products') or [])}", flush=True)
            response_blocks.append(format_tool_response(result))
            if terminal.get("done"):
                break

        if terminal and terminal.get("done"):
            break
        messages.append({"role": "user", "content": "\n\n".join(response_blocks)})

    if terminal is None or not terminal.get("done"):
        final = clean_final_output(model_outputs[-1]) if model_outputs else ""
        terminal = env.step({"type": "final", "content": final})

    final_output = _extract_final_output(model_outputs)
    reward_detail = terminal.get("reward_detail") or {}
    print(
        "[INFO] finished "
        f"reward={terminal.get('reward')} "
        f"reward_type={reward_detail.get('reward_type')}",
        flush=True,
    )
    preview = (final_output or model_outputs[-1] if model_outputs else "").replace("\n", " ")
    print(f"[INFO] final preview: {preview[:240]}", flush=True)
    return {
        "task": task,
        "model_outputs": model_outputs,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "final_output": final_output,
        "reward": terminal.get("reward"),
        "reward_detail": reward_detail,
        "transcript": messages,
    }


def _strict_tool_prompt(query: str) -> str:
    return (
        f"{query}\n\n"
        "No tool result is available yet. The first step must output only one tool call. "
        "Do not write a final recommendation yet. Do not output [product:X] yet. "
        "Use exactly this format:\n"
        "<tool_call>\n"
        "{\"name\":\"sku_recall\",\"arguments\":{\"query\":\"rewrite the user need as a complete search query\"}}\n"
        "</tool_call>"
    )


def format_tool_response(result: Dict[str, Any]) -> str:
    products = result.get("products") or []
    if products:
        lines = [
            f"<tool_response>\nTool returned {len(products)} products.",
            "Now write the final recommendation. Cite selected products exactly as [product:1], [product:2], etc.",
            "Do not output <think> or internal planning.",
        ]
        for index, product in enumerate(products, 1):
            title = product.get("sku_name") or product.get("title") or ""
            price = product.get("final_price", product.get("price", ""))
            sales = product.get("sales") or product.get("good") or ""
            specs = product.get("keyword") or product.get("match_reason") or ""
            lines.append(f"  [{index}] {title} {price} {sales} | {specs}")
        lines.append("</tool_response>")
        return "\n".join(lines)
    return (
        "<tool_response>\n"
        "Tool returned 0 products. Do not invent product cards. Ask for broader conditions or explain no match.\n"
        "</tool_response>"
    )


def write_outputs(records: List[Dict[str, Any]], output_jsonl: Path, output_md: Path) -> None:
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    lines = ["# Joybuy SFT Test Outputs", ""]
    for index, record in enumerate(records, 1):
        task = record["task"]
        lines.extend([
            f"## {index}. {task['query']}",
            "",
            f"- reward: `{record.get('reward')}`",
            f"- reward_type: `{(record.get('reward_detail') or {}).get('reward_type')}`",
            "",
            "### Final Output",
            "",
            record.get("final_output") or "",
            "",
            "### Raw Model Outputs",
            "",
        ])
        for step, output in enumerate(record.get("model_outputs") or [], 1):
            lines.extend([f"#### Step {step}", "", "```text", output, "```", ""])
    output_md.write_text("\n".join(lines), encoding="utf-8")


def _normalize_action(action: Dict[str, Any]) -> Dict[str, Any]:
    name = str(action.get("name") or "")
    arguments = dict(action.get("arguments") or {})
    arguments = ReActJoybuyAgent._normalize_tool_arguments(name, arguments)
    return {"type": "tool_call", "name": name, "arguments": arguments}


def _extract_final_output(outputs: List[str]) -> str:
    if not outputs:
        return ""
    final = outputs[-1].strip()
    if "<tool_call>" in final:
        return ""
    return clean_final_output(final)


def clean_final_output(text: str) -> str:
    import re

    cleaned = text or ""
    cleaned = re.sub(r"<tool_call>[\s\S]*?</tool_call>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^[\s\S]*?</think>\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?<!\[)[\u4fd2\uff3b\{\(（<]*\s*product\s*:\s*(\d+)\]", r"[product:\1]", cleaned)
    cleaned = re.sub(r"\[\s*product\s*:\s*(\d+)\s*\]", r"[product:\1]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*瓢峄焠g\s*", "", cleaned)
    return cleaned.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--adapter-path", default="")
    parser.add_argument("--input", default="")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output-jsonl", default="slime_joybuy_rl/output/sft_test_outputs.jsonl")
    parser.add_argument("--output-md", default="slime_joybuy_rl/output/sft_test_outputs.md")
    parser.add_argument("--max-steps", type=int, default=3)
    parser.add_argument("--max-new-tokens", type=int, default=1200)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--repetition-penalty", type=float, default=1.08)
    parser.add_argument("--no-repeat-ngram-size", type=int, default=6)
    parser.add_argument("--strict-tool-first", action="store_true")
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16", "float32"], default="float16")
    args = parser.parse_args()

    tokenizer, model = load_model(args.model_path, args.adapter_path, args.dtype)
    input_path = Path(args.input) if args.input else None
    tasks = list(iter_queries(input_path, args.query, args.limit))
    records = [
        run_one(
            tokenizer,
            model,
            task,
            max_steps=args.max_steps,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            repetition_penalty=args.repetition_penalty,
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            strict_tool_first=args.strict_tool_first,
        )
        for task in tasks
    ]
    write_outputs(records, Path(args.output_jsonl), Path(args.output_md))
    print(f"wrote {len(records)} records to {args.output_jsonl}")
    print(f"markdown report: {args.output_md}")


if __name__ == "__main__":
    main()
