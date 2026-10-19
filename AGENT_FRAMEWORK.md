# JoySage Agent Framework 说明

> 轻量级购物 Agent 框架，基于真实 joybuy-chatbot 项目架构复现，用于 SFT 训练数据生成。

---

## 1. 框架概述

### 设计目标

- 无需依赖 oxygent 内部框架（不 import oxygent-src），使用标准 Python
- 工具名、字段名、返回格式与真实 joybuy 项目对齐
- 每个工具内置完整 Mock 数据，可在无内网时独立运行
- 可驱动 SFT 数据生成（有内网用 LLM，无内网用 Mock）

### 与真实 oxygent 项目对照

| 真实 joybuy-chatbot | 本框架（JoySage） |
|---|---|
| `OxyRequest` | `AgentContext` |
| `FunctionHub` | `ToolRegistry` |
| `WorkflowAgent` | `ShoppingAgent` |
| `@hub.tool(description=...)` | `registry.register(name, fn)` |
| `await oxy_request.call(callee, args)` | `self._call_tool(name, params, ctx)` |
| `oxy_request.shared_data` | `ctx.shared_data` |
| `parse_json_dict_or_empty(response.output)` | 工具直接返回 dict |

---

## 2. 目录结构

```
agent后训练项目/
├── joybuy_agent/
│   ├── __init__.py              # 导出 AgentContext / ToolRegistry / ShoppingAgent
│   ├── core/
│   │   ├── context.py           # AgentContext（对应 OxyRequest）
│   │   ├── tool_registry.py     # ToolRegistry（对应 FunctionHub）
│   │   └── agent.py             # ShoppingAgent 基类（对应 WorkflowAgent）
│   ├── tools/
│   │   ├── __init__.py          # create_registry() — 注册所有工具
│   │   ├── sku_recall.py        # SkuRecallShopping（30条+matching池）
│   │   ├── sku_repurchase.py    # SkuRepurchaseRecall（10条历史订单）
│   │   ├── order_tools.py       # OrderQuerySkill + ShoppingPlaceOrderTool
│   │   └── calculator.py        # PythonCalculator
│   └── agents/
│       ├── shopping_agent.py    # SearchRecommendAgent
│       ├── similar_agent.py     # SimilarRecAgent
│       ├── compare_agent.py     # SkuCompAgent
│       ├── repurchase_agent.py  # RepurchaseAgent
│       ├── matching_agent.py    # MatchingAgent（新建场景）
│       ├── bundle_agent.py      # BundleAgent（新建场景）
│       └── order_agent.py       # OrderAgent
├── AGENT_FRAMEWORK.md           # 本文档
├── TOOL_DEFINITIONS.md          # 工具定义详细文档
└── sft_data/
    └── llm_gen_oxygen.py        # 数据生成脚本（--mock 模式对接本框架）
```

---

## 3. 工具层（tools/）

### 3.1 工具名与真实项目对应

| SFT 中的 tool_name | 真实 joybuy 对应 | 本框架文件 |
|---|---|---|
| `SkuRecallShopping` | sku_recall_hub.sku_recall + scenario_recall_hub | tools/sku_recall.py |
| `SkuRepurchaseRecall` | sku_recall_hub.sku_recall_history | tools/sku_repurchase.py |
| `OrderQuerySkill` | task_service_tools.query_order_detail/logistics | tools/order_tools.py |
| `ShoppingPlaceOrderTool` | task_service_tools（下单操作） | tools/order_tools.py |
| `PythonCalculator` | 内置 exec 工具 | tools/calculator.py |

### 3.2 SkuRecallShopping 召回模式

工具根据 params 字段自动选择召回策略：

```python
# 普通搜索模式（search_recommend / similar_rec / sku_comp）
result = registry.call("SkuRecallShopping", ctx, {
    "query": "降噪耳机",
    "max_price": 500,
    "page_size": 3,
})

# 精确匹配模式（sku_comp，按名称精确匹配）
result = registry.call("SkuRecallShopping", ctx, {
    "skus": ["索尼WF-C700N", "AirPods 4"],
})

# 搭配模式（matching_purchase，无价格约束）
result = registry.call("SkuRecallShopping", ctx, {
    "query": "茶几",
    "filters": {"style": "nordic", "max_count": 4},
})
```

**重要**：matching_purchase 场景**不传 max_price**——这是区分搭配购物和普通购物的关键训练信号。

### 3.3 Mock 商品池（30 条）

10 品类 × 3 款，price / rating / key_specs / sales 均为真实市场数据：

| 品类 | 价格区间 | 代表商品 |
|---|---|---|
| 手机 | ¥5299-6499 | 小米14 Pro / 华为Mate60 Pro / vivo X100 Ultra |
| 空气净化器 | ¥1599-1999 | 小米4 Pro / 352 X83C / IAM KJ900F |
| 跑步鞋 | ¥249-299 | 安踏氢跑5代 / 李宁䨻烁2 / 特步160X |
| 颈部按摩仪 | ¥299-469 | 米家 / 飞利浦PR3092 / 倍轻松 |
| 扫地机器人 | ¥2999-3599 | 石头G20S / 科沃斯X2 / 追觅L20 |
| 人体工学椅 | ¥1299-1999 | 西昊C300 / 保友金豪E2 / 网易严选C1 |
| 耳机 | ¥199-1299 | 漫步者TWS1 / 索尼WF-C700N / AirPods 4 |
| 显示器 | ¥699-1399 | 小米 / DELL S2722DC / LG 27GP850 |
| 炒锅 | ¥199-459 | 炊大皇 / 南山先生 / 苏泊尔钛系列 |
| 保温杯 | ¥129-229 | 小米MIGA / 膳魔师 / 虎牌MHK-A050 |

---

## 4. 7 个场景 Agent

### 4.1 SearchRecommendAgent（search_recommend）

```
用户搜索意图 → SkuRecallShopping（query + max_price） → final_response（推荐3款+选购建议）
```

**训练重点**：多约束搜索（预算+用途+人群）→ 精准参数转化。

### 4.2 SimilarRecAgent（similar_rec）

```
用户抱怨 → 识别抱怨维度 → SkuRecallShopping（调整参数） → final_response（改进款推荐）
```

**抱怨维度映射**：
- 「漏音」→ query 加 `密封/封闭式/隔音`
- 「保温」→ query 加 `保温/24h/真空双层`
- 「噪音」→ query 加 `静音/超静音`
- 「太重」→ query 加 `轻量/轻薄/便携`
- ...（共14种抱怨维度，见 similar_agent.py）

**训练重点**：抱怨语义 → 参数调整，推荐要解释为什么这款改进了对应缺点。

### 4.3 SkuCompAgent（sku_comp）

```
用户点名商品 → SkuRecallShopping（skus=精确名称列表） → final_response（含 Markdown 对比表格）
```

**训练重点**：
- final_response 必须包含 `| 维度 | 商品A | 商品B |` 格式对比表格
- 给出明确的倾向性建议（不能「两款都不错」含糊作答）

### 4.4 MatchingAgent（matching_purchase）—— 新建场景

```
用户描述主商品 → 识别风格标签 → SkuRecallShopping（filters.style）→ final_response（整套方案表格）
```

**关键设计**：
- **不传 max_price**（搭配购物不以价格为首要约束）
- `params["filters"]["style"]` 驱动匹配（nordic/mid_century/business_formal/fitness）
- final_response 必须包含整套方案汇总表格 + 风格搭配理由

**训练重点**：用户买了主商品 X → 帮配整套，而不是「推荐价格最低的」。

### 4.5 BundleAgent（bundle_purchase）—— 新建场景

```
解析预算+场景 → N×SkuRecallShopping（每品类一次，带 max_price=总预算×ratio）
            → PythonCalculator（算账）→ final_response（总价表格+预算分析）
```

**关键设计**：
- 多次调用 `SkuRecallShopping`（每品类独立召回），不是一次调用返回所有
- **必须调用 PythonCalculator**（否则 trajectory_grader 会扣分）
- 预算分配按使用频率：kitchen（炒锅35%+刀具30%+汤锅20%+煎锅15%）

**训练重点**：
1. 按品类拆解预算（每品类独立调用工具）
2. 用计算器算账，输出精确数字
3. 给出「升级/实用/性价比」多套方案

### 4.6 RepurchaseAgent（repurchase）

```
识别品类关键词 → SkuRepurchaseRecall（category_keyword + time_range）
→ final_response（历史购买记录 + 复购/升级/新品三种方案）
```

**训练重点**：
- products 第一个是历史购买商品（title/key_specs 中含「X月前购买」）
- 明确告知购买时间激活复购心智
- 区分「同款复购」vs「升级推荐」vs「同品牌新品」三种建议

### 4.7 OrderAgent（place_order）

```
意图识别（查询/退货/换货/价保/发票/下单/预约）
→ OrderQuerySkill 或 ShoppingPlaceOrderTool
→ final_response（含具体 App 操作路径）
```

**训练重点**：
- final_response 必须包含 App 操作路径：`京东 App → 我的订单 → XX → XX`
- 覆盖 10 种操作场景（退款/换货/物流/取消/价保/发票/提前还款/预约/下单/合并发货）

---

## 5. card_id 防幻觉机制

**规则**：product_cards 中每个 `card_id` 必须出现在某个 tool_call 步骤的 `tool_output.products` 中。

**实现**：`ShoppingAgent._build_trajectory()` 在序列化前 assert 校验：

```python
all_product_ids = set()
for s in self._steps:
    if s.step_type == "tool_call" and s.tool_output:
        for p in s.tool_output.get("products", []):
            all_product_ids.add(p["product_id"])

for s in self._steps:
    for card in s.product_cards:
        assert card["card_id"] in all_product_ids, "card_id 幻觉"
```

`trajectory_grader` 的 `CardIdValidator` 也会在评估时检验此规则，违反则整条轨迹评分为 0。

---

## 6. SFT 数据生成

### 6.1 Mock 模式（无内网）

```bash
cd agent后训练项目/sft_data
python3 llm_gen_oxygen.py -n 200 --mock           # 200条，均匀分配7个场景
python3 llm_gen_oxygen.py -n 50 --mock --scenario bundle_purchase  # 只生成bundle
```

Mock 模式：速度极快（200条 < 1秒），格式100%合规，但数据多样性受 TOPICS 题库限制。

### 6.2 LLM 模式（有内网）

```bash
python3 llm_gen_oxygen.py -n 100                  # 3个模型轮询，约30分钟
python3 llm_gen_oxygen.py -n 50 --scenario sku_comp  # 只生成对比场景
```

LLM 模式：内容多样，自然语言质量高，但速度慢（每条约30-120秒）。

### 6.3 推荐工作流

```bash
# 1. 先用 Mock 快速建立基础集（每场景50条，共350条）
python3 llm_gen_oxygen.py -n 350 --mock

# 2. 有内网时用 LLM 生成高质量补充数据
python3 llm_gen_oxygen.py -n 150

# 3. 统计分布
python3 -c "
import json
from collections import Counter
c = Counter()
with open('trajectories_final.jsonl') as f:
    for line in f:
        c[json.loads(line)['scenario_type']] += 1
for k,v in sorted(c.items()):
    print(f'{k}: {v}')
"
```

---

## 7. Mock 数据规范

### product_id 格式

| 场景 | 格式 | 示例 |
|---|---|---|
| 基础商品池 | `jd_XXXXXXXX`（8位数字） | `jd_10001001` |
| matching 专属 | `jd_match_XXXN` | `jd_match_001a` |
| repurchase 历史 | `jd_rep_XXX` | `jd_rep_001` |
| 订单相关 | `jd_order_guide` 或 `calc_result_001` | `calc_result_001` |

### 价格规范

- 手机：¥5000-7000
- 家电：¥200-4000（按品类）
- 日用品：¥20-500
- 不得出现小数点后超过2位

### 月销量格式

- `月销X万件`（X 为正整数，如 `月销1.8万`）
- 数量少的品类：`月销XXXX`（如 `月销3500`）

### rating 范围

- 4.6：入门/平价款
- 4.7：中端正常水平
- 4.8：中高端主流好评
- 4.9：明星旗舰爆款

---

## 8. 扩展指南

### 8.1 新增工具

1. 在 `joybuy_agent/tools/` 下创建文件，实现 `__call__(ctx, params) -> dict`
2. 在 `tools/__init__.py` 的 `create_registry()` 中注册
3. 在 `llm_gen_oxygen.py` 的 SYSTEM_PROMPT 规则 8 中添加工具名映射

### 8.2 新增场景

1. 在 `joybuy_agent/agents/` 下创建 Agent 类（继承 ShoppingAgent）
2. 在 `agents/__init__.py` 导出
3. 在 `llm_gen_oxygen.py` 的 `agent_map` 和 `TOPICS` / `SCENARIO_CONFIG` 中添加

### 8.3 扩充 Mock 数据

编辑 `tools/sku_recall.py` 中的 `MOCK_PRODUCT_POOL`，按格式添加商品即可。每个品类至少3条，避免过度重复。

---

## 9. 与 trajectory_grader 集成

生成的轨迹可直接用 `trajectory_grader` 评估：

```bash
cd trajectory_grader
streamlit run app.py
```

在侧边栏点「加载 JSONL 文件」→ 选择 `sft_data/trajectories_final.jsonl` → 选择一条评分。

期望结果：
- Mock 生成的轨迹：D1/D4 Gate PASS，D2 真实性可能偏低（Mock 数据不如真实网页信息）
- LLM 生成的轨迹：整体质量更高，D5 推理价值感得分更好
