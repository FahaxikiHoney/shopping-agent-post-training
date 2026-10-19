# Shopping Mock RL Environment

`ShoppingMockEnv` 将现有 Shopping Mock 工具封装为确定性的状态化交互环境，供在线 Rollout、GRPO/PPO 原型和策略回归使用。

## 接口

```python
from shopping_agent.react import ShoppingMockEnv

env = ShoppingMockEnv(max_steps=5)
observation = env.reset({
    "query": "Football hobby box",
    "site_code": "UK-Site",
    "scenario_type": "search_recommend",
    "sample_id": "demo-1",
})

observation = env.step({
    "type": "tool_call",
    "name": "sku_recall",
    "arguments": {"query": "Football hobby box"},
})

product = observation["latest_result"]["products"][0]
terminal = env.step({
    "type": "final",
    "content": (
        f"**{product['sku_name']}**: £{product['final_price']}."
        "[product:1]\n\n"
        "How would you like to narrow the options? "
        "<ClickText>Budget</ClickText> <ClickText>Brand</ClickText>"
    ),
})

print(terminal["reward"])
print(terminal["reward_detail"])
```

`step()` 同时接受以下动作：

- `{"type": "tool_call", "name": "sku_recall", "arguments": {...}}`
- OpenAI Function Calling 形式的 `{"function": {"name": ..., "arguments": ...}}`
- `{"type": "final", "content": "..."}`
- 普通字符串，直接视为最终回复
- JSON 字符串，解析后按结构化动作执行

## Observation

每次返回：

- `instruction`
- `task_id`
- `site_code`
- `scenario_type`
- `tools`
- `messages`
- `latest_result`
- `display_product_count`
- `step`
- `max_steps`
- `done`

工具原始返回中不注入展示编号。最终 `[product:X]` 仍按照本轮全部去重商品的出现顺序解释。

## Reward v1

奖励版本：`shopping-mock-reward-v1`。

| 结果 | 典型奖励 |
|---|---:|
| 合法检索并输出正确商卡 | 约 0.9–0.99 |
| 合法非购物直接回复 | 约 0.8–0.85 |
| 真实空召回并诚实说明 | 最高 0.45 |
| 购物请求未调用必需工具 | -0.60 |
| 原始 Query 有商品但故意搜空 | -0.40 |
| 工具有商品但未输出商卡 | -0.45 |
| 商卡越界、重复或凭空生成 | -0.50 |
| 达到最大步数仍未结束 | -0.80 |
| 非法动作耗尽步数 | -0.90 |

每次合法工具调用扣除默认 `0.01` 成本；最近三步内重复同一工具参数额外扣除 `0.07`。

奖励完全由工具结果、商卡、质量门禁、任务场景和动作历史确定，不调用 LLM Judge。

## 防奖励投机

- 明确购物请求不调用必需工具会获得负奖励。
- 原始 Query 可以召回商品，但模型通过改坏检索词制造空结果，会获得负奖励。
- 工具返回商品后不展示商卡会获得负奖励。
- 真实空召回奖励显著低于成功推荐，避免固定拒答成为最优策略。
- 重复调用和过长轨迹有成本。
- 动态优惠、隐私安全、商品使用问答等直接回复任务不强制搜索。

## 场景必需工具

| `scenario_type` | 必需工具 |
|---|---|
| `search_recommend` | `sku_recall` |
| `matching` | `scenario_related_recall` |
| `similar_rec` | `similar_sku_recommend` |
| `bundle_purchase` | 至少一次 `sku_recall` |

后续接入 veRL 时，可以在 AgentLoop 中把模型的单次 Function Call 直接传给 `step()`，并使用终局结果中的 `reward` 作为 sequence reward。
