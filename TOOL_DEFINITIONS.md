# 购物 Agent 工具定义文档

## 概述

本文档是 JoySage（购物平台对话式购物 Agent）后训练项目的工具定义参考标准，所有工具名称、参数字段和 Mock 数据均来自真实 shopping-chatbot 项目（`core/multi_agent/shopping/tool_list.py`）。

**工具来源**：基于真实 shopping-chatbot 项目，工具名与 `core/multi_agent/shopping/tool_list.py` 完全对齐。

---

## 工具一览表

| 工具名 | 所属场景 | 功能描述 | 输入关键字段 | 输出关键字段 |
|---|---|---|---|---|
| `SkuRecallShopping` | search_recommend / similar_rec / sku_comp / matching_purchase / bundle_purchase | 主搜索召回工具，覆盖关键词搜索、精确 SKU 匹配、跨品类召回、风格过滤 | `query` / `skus` / `min_price` / `max_price` / `filters` / `mode` / `fields` | `status` / `products[]`（含 product_id, title, price, rating, key_specs, sales）|
| `SkuImageRecall` | similar_rec（图搜子场景）| 基于图片视觉特征召回相似商品 | `image_features` / `constraints` / `topk` | `status` / `products[]` |
| `SkuRepurchaseRecall` | repurchase | 从用户历史订单中召回曾购商品及相似推荐 | `category_keyword` / `time_range` / `include_similar` / `predict_usage` | `status` / `products[]`（含历史购买信息）|
| `ShoppingPlaceOrderTool` | place_order | 下单、预约购买、限量抢购、换货等全流程购物操作 | `product_id` / `quantity` / `address` / `payment_method` / `action` / `order_id` | `status` / `products[]`（含订单号、预计送达时间）|
| `OrderQuerySkill` | place_order（售后子场景）/ repurchase（历史查询）| 订单查询、退换货申请、物流跟踪、地址修改 | `order_id` / `category_keyword` / `time_range` / `status` / `issue_type` / `user_intent` | `status` / `products[]`（含历史订单详情）|
| `PythonCalculator` | bundle_purchase | 预算分配计算、多方案对比算账 | `code`（Python 表达式字符串）| `status` / `products[]`（含计算结果的 key_specs 字段）|
| `WebSearchTool` | 兜底（不常用）| 网页搜索兜底，用于无货/无法匹配时的补充 | `query` | `status` / `results[]` |

---

## 各场景工具详细说明

---

### 1. similar_rec — 相似品推荐

#### 1.1 场景说明

用户对当前被推荐商品不满意（抱怨颜色/价格/功能缺失），Agent 需要识别**抱怨维度**，在保持核心约束的前提下调整工具参数重新搜索。这是训练数据的核心难点——工作流 `similar_rec_overseas.py` 只能按品类盲推，训练后的 Agent 能识别抱怨维度并精准调整。

**典型抱怨维度 → 参数变化映射**：

| 抱怨维度 | 工具参数调整 |
|---|---|
| 颜色单一 | `filters.color_variety_min` 加约束，`exclude_skus` 排除已被拒商品 |
| 价格太贵 | `max_price` 降至抱怨商品价格的 50-60%，保留性能下限 |
| 缺少某功能 | `filters.has_xxx: true` 加硬性功能过滤 |
| 视觉想找同款 | 改用 `SkuImageRecall`（视觉特征召回） |
| 之前买过想找类似 | 改用 `SkuRepurchaseRecall`（历史订单融合） |

#### 1.2 工具调用顺序

```
用户抱怨 → 识别抱怨维度
  ├── 颜色/功能/价格抱怨 → [Step 1] SkuRecallShopping（调整参数版）→ [Step 2] final_response
  ├── 图片相似搜索      → [Step 1] SkuImageRecall → [Step 2] final_response
  └── 历史购买模糊回忆  → [Step 1] SkuRepurchaseRecall → [Step 2] final_response
```

#### 1.3 SkuRecallShopping 输入/输出 Schema

**输入 Schema（相似品推荐模式）**：

```json
{
  "query": "string — 带抱怨维度关键词的搜索词，如'旗舰手机 多配色 同价位替代'",
  "min_price": "number — 价格下限（可选），抱怨太贵时从原价50%起",
  "max_price": "number — 价格上限，保持原约束或根据抱怨降低",
  "filters": {
    "color_variety_min": "integer — 抱怨颜色单一时设置，如4（至少4种配色）",
    "has_auto_water_supply": "boolean — 抱怨缺自动上下水时设置为true",
    "has_mop_cleaning": "boolean — 抱怨缺拖地功能时设置为true",
    "suction_aw_min": "integer — 抱怨吸力不够时设置吸力下限",
    "battery_min_minutes": "integer — 抱怨续航不足时设置续航下限（分钟）",
    "style": "string — 风格约束，如'business_formal'",
    "colors": ["array — 指定颜色列表"]
  },
  "exclude_skus": ["array — 排除用户已经看过/拒绝的商品，如'iPhone 15 128G'"]
}
```

**输出 Schema**：

```json
{
  "status": "SUCCESS | NO_RESULT | CALLER_ERROR",
  "products": [
    {
      "product_id": "string — 格式 mock_XXXXXXXX，如 mock_simrec_001a",
      "title": "string — 商品完整标题",
      "price": "number — 当前售价（元）",
      "is_platform_self": "boolean — 是否平台自营",
      "rating": "number — 评分（4.5-4.9）",
      "key_specs": "string — 核心规格，如'7种配色/徕卡光学/骁龙8 Gen3'",
      "sales": "string — 月销量，如'月销1.8万'"
    }
  ]
}
```

#### 1.4 SkuImageRecall 输入/输出 Schema

**输入 Schema**：

```json
{
  "image_features": {
    "dominant_color": "string — 主色调，如'white'/'beige'",
    "style": "string — 视觉风格，如'minimalist'/'vintage'",
    "category": "string — 品类，如'羊毛衫/针织衫'"
  },
  "constraints": {
    "exclude_pattern": "boolean — true表示排除有花纹款",
    "color_preference": "string — 'solid'（纯色）/'patterned'（花纹）"
  },
  "topk": "integer — 返回候选数量，建议3-5"
}
```

**输出 Schema**：与 SkuRecallShopping 输出相同。

#### 1.5 Mock 数据示例（相似品推荐）

```json
{
  "step_id": 1,
  "step_type": "tool_call",
  "tool_name": "SkuRecallShopping",
  "tool_input": {
    "query": "旗舰手机 多配色 同价位替代",
    "min_price": 5000,
    "max_price": 6000,
    "filters": {"color_variety_min": 4},
    "exclude_skus": ["iPhone 15 128G"]
  },
  "tool_output": {
    "status": "SUCCESS",
    "products": [
      {
        "product_id": "mock_simrec_001a",
        "title": "小米 14 Pro 12+256G 7配色（白银紫绿黑橙青）",
        "price": 5499.0,
        "is_platform_self": true,
        "rating": 4.8,
        "key_specs": "7种配色/徕卡光学/骁龙8 Gen3",
        "sales": "月销1.8万"
      },
      {
        "product_id": "mock_simrec_001b",
        "title": "vivo X100 Pro 12+256G 5配色（星迹蓝/落日橙/辰夜黑/白月光/翡翠绿）",
        "price": 5799.0,
        "is_platform_self": true,
        "rating": 4.7,
        "key_specs": "5种配色/蔡司光学/天玑9300",
        "sales": "月销1.2万"
      }
    ]
  }
}
```

---

### 2. sku_comp — 商品对比

#### 2.1 场景说明

用户想对比 2-4 款商品，Agent 需要**并行召回所有商品详情**，并根据用户场景**动态调整对比维度的权重**。工作流 `sku_comp.conf` 里的维度是写死的，训练后的 Agent 能根据用户场景（老人用/户外/办公/游戏）自动加权。

**对比维度动态权重原则**：
- 老人用 → 操作简便 > 摄影AI辅助 > 续航 > 性能
- 徒步户外 → GPS精度 > 防水等级 > 户外续航 > 导航地图
- 商务办公 → 静音性 > 跨设备切换 > 续航 > 自定义按键

#### 2.2 工具调用顺序

```
用户提出N款商品对比
  → [Step 1] SkuRecallShopping（mode: parallel_exact_match，一次召回所有SKU）
  → [Step 2] final_response（含动态维度加权的对比表格 + 场景推荐）

多轮增量对比（用户追加新商品）：
  → 保留历史已对比商品
  → [Step 1] SkuRecallShopping（包含原有+新增商品，更新scenario_focus）
  → [Step 2] final_response（重构对比表）
```

#### 2.3 SkuRecallShopping 输入/输出 Schema（对比模式）

**输入 Schema**：

```json
{
  "skus": ["array — 精确商品名列表，如['小米14 Ultra', '华为Mate60 Pro', 'vivo X100 Pro']"],
  "mode": "string — 固定值 'parallel_exact_match'，表示并行精确匹配",
  "scenario_focus": "string — 用户场景，如'outdoor_hiking'/'office_productivity'/'elderly_use'",
  "fields": ["array — 需要返回的对比维度，如['影像', '通讯', '性能', '系统', '续航']"],
  "categories": ["array — 跨品类对比时使用，如['扫地机器人', '洗地机']"],
  "topk_per_category": "integer — 跨品类时每个品类返回数量",
  "use_case_keywords": ["array — 使用场景关键词，如['宠物毛', '80平']"]
}
```

**输出 Schema**：与 SkuRecallShopping 标准输出相同，`key_specs` 字段包含各对比维度的具体参数值。

#### 2.4 Mock 数据示例（3商品并行对比）

```json
{
  "step_id": 1,
  "step_type": "tool_call",
  "tool_name": "SkuRecallShopping",
  "tool_input": {
    "skus": ["小米14 Ultra", "华为Mate60 Pro", "vivo X100 Pro"],
    "mode": "parallel_exact_match",
    "fields": ["影像", "通讯", "性能", "系统", "续航"]
  },
  "tool_output": {
    "status": "SUCCESS",
    "products": [
      {
        "product_id": "mock_skucmp_001a",
        "title": "小米14 Ultra 16+512G 钛金属",
        "price": 5999.0,
        "is_platform_self": true,
        "rating": 4.9,
        "key_specs": "徕卡四摄/1英寸主摄/骁龙8 Gen3/IP68/5300mAh",
        "sales": "月销8500"
      },
      {
        "product_id": "mock_skucmp_001b",
        "title": "华为Mate60 Pro 12+512G",
        "price": 5999.0,
        "is_platform_self": true,
        "rating": 4.9,
        "key_specs": "XMAGE四摄/卫星通话/麒麟9000S/玄武架构/5000mAh",
        "sales": "月销1.2万"
      },
      {
        "product_id": "mock_skucmp_001c",
        "title": "vivo X100 Pro 16+512G 蔡司版",
        "price": 5499.0,
        "is_platform_self": true,
        "rating": 4.8,
        "key_specs": "蔡司APO超级长焦/天玑9300/2K屏/5400mAh",
        "sales": "月销7800"
      }
    ]
  }
}
```

---

### 3. search_recommend — 搜索推荐

#### 3.1 场景说明

最常见的场景，用户输入购物需求（含品类/预算/使用场景/人群），Agent 调用 SkuRecallShopping 检索 3-5 款商品，按多维度筛选后给出有倾向性的推荐。这是整个数据集中条数最多的场景（35条）。

**核心训练目标**：多约束精准召回（预算+品类+使用人群+场景）。

#### 3.2 工具调用顺序

```
用户搜索需求（含约束）
  → [Step 1] SkuRecallShopping（传入全部约束）
  → [Step 2] final_response（3-5款推荐+分人群建议）

复杂需求（如参数矛盾）：
  → [Step 1] SkuRecallShopping（第一次，宽松召回）
  → [Step 2] SkuRecallShopping（第二次，加过滤精排）
  → [Step 3] final_response
```

#### 3.3 SkuRecallShopping 输入/输出 Schema（搜索推荐模式）

**输入 Schema**：

```json
{
  "query": "string — 完整搜索关键词，含品类+场景+人群，如'颈部按摩仪 老人 一键操作 简单'",
  "min_price": "number — 价格下限（可选）",
  "max_price": "number — 价格上限，用户明确提及时必填",
  "is_platform_self": "boolean — 是否限定平台自营，默认true",
  "filters": {
    "brand": "string — 品牌名（用户指定时传入）",
    "is_new": "boolean — 是否新品",
    "promotion": "string — 促销类型"
  },
  "sort": "string — 排序方式，'sales_desc'/'rating_desc'/'price_asc'",
  "page_size": "integer — 返回数量，建议3-5"
}
```

**输出 Schema**：标准 `products[]` 数组，每个商品含 product_id, title, price, is_platform_self, rating, key_specs, sales。

#### 3.4 Mock 数据示例（搜索推荐）

```json
{
  "step_id": 1,
  "step_type": "tool_call",
  "tool_name": "SkuRecallShopping",
  "tool_input": {
    "query": "颈部按摩仪 老人 一键操作 简单",
    "max_price": 500,
    "is_platform_self": true
  },
  "tool_output": {
    "status": "SUCCESS",
    "products": [
      {
        "product_id": "mock_11223344",
        "title": "小米米家颈椎按摩仪 3档强度 一键启动 热敷功能",
        "price": 349.0,
        "is_platform_self": true,
        "rating": 4.8,
        "key_specs": "3档力度/15分钟自动断电/热敷功能",
        "sales": "月销3.2万件"
      },
      {
        "product_id": "mock_55667788",
        "title": "飞利浦肩颈按摩仪 PR3092 老人款 双键操作",
        "price": 469.0,
        "is_platform_self": true,
        "rating": 4.7,
        "key_specs": "5档强度/40-50℃热敷/锂电池4小时续航",
        "sales": "月销1.8万件"
      },
      {
        "product_id": "mock_99001122",
        "title": "倍轻松颈椎按摩器 智能感应 老年人专用款",
        "price": 299.0,
        "is_platform_self": true,
        "rating": 4.6,
        "key_specs": "贴合人体颈部/12分钟定时/极简一键设计",
        "sales": "月销1.5万件"
      }
    ]
  }
}
```

---

### 4. matching_purchase — 搭配购物

#### 4.1 场景说明

用户已有一件核心商品，想找搭配品。**核心特征：不传价格约束**，工具输入里没有 `max_price` 字段，只有风格/颜色/材质/场合关键词。这是与组合购物（bundle_purchase）的根本区别。

**搭配维度**：
- 服装搭配：颜色呼应（同色系/对比色）+ 场合适配
- 家居搭配：材质对话（原木配原木）+ 风格协调（北欧/轻奢/工业）
- 3C 搭配：兼容性（型号匹配）+ 颜色一致性
- 餐桌搭配：材质/色系/风格协调

#### 4.2 工具调用顺序

```
用户描述核心商品（颜色/材质/风格）
  → [Step 1] SkuRecallShopping（传风格关键词 + match_with，无价格）
  → （必要时进行第二次召回，补充品类）
  → [Step N] final_response（含搭配逻辑说明+避坑提示）
```

#### 4.3 SkuRecallShopping 输入/输出 Schema（搭配模式）

**输入 Schema**：

```json
{
  "query": "string — 搭配品品类+风格关键词，如'男士领带 商务正装 真丝'",
  "filters": {
    "colors": ["array — 推荐颜色列表，如['酒红', '银灰', '深红', '宝蓝']"],
    "style": "string — 风格约束，如'business_formal'/'nordic'/'casual'",
    "material": "string — 材质约束，如'cashmere_or_wool'",
    "materials": ["array — 多材质可选列表"],
    "shape": ["array — 形状约束，如['round', 'rectangle_simple']"]
  },
  "match_with": "string — 核心商品描述（英文），如'deep_blue_suit'/'beige_fabric_sofa_nordic'",
  "tags": ["array — 风格标签，如['vintage', 'minimalist']"]
}
```

**注意**：搭配购物模式下，`min_price` 和 `max_price` 均不传入，由此区别于 search_recommend 和 bundle_purchase。

**输出 Schema**：标准 `products[]`，`key_specs` 中包含材质/颜色/搭配逻辑说明。

#### 4.4 Mock 数据示例（服装搭配）

```json
{
  "step_id": 1,
  "step_type": "tool_call",
  "tool_name": "SkuRecallShopping",
  "tool_input": {
    "query": "男士领带 商务正装 真丝",
    "filters": {
      "colors": ["酒红", "银灰", "深红", "宝蓝"],
      "style": "business_formal"
    },
    "match_with": "deep_blue_suit"
  },
  "tool_output": {
    "status": "SUCCESS",
    "products": [
      {
        "product_id": "mock_match_001a",
        "title": "Calvin Klein 真丝领带 经典酒红色 商务款",
        "price": 459.0,
        "is_platform_self": true,
        "rating": 4.8,
        "key_specs": "100%桑蚕丝/7cm经典宽度/酒红配深蓝(色彩学经典配色)",
        "sales": "月销1800"
      },
      {
        "product_id": "mock_match_001b",
        "title": "海澜之家 商务领带 银灰提花 真丝混纺",
        "price": 199.0,
        "is_platform_self": true,
        "rating": 4.7,
        "key_specs": "银灰色/低调商务/适合正式会议",
        "sales": "月销4500"
      }
    ]
  }
}
```

---

### 5. bundle_purchase — 组合购物

#### 5.1 场景说明

用户提出一个使用场景和总预算，需要 Agent 拆分成多个品类分别搜索，再通过 `PythonCalculator` 算账对比，给出 2-3 套预算分配方案。**每条 bundle_purchase 样本必须包含 `PythonCalculator` 调用**。

**预算分配原则**：
- 按使用频率分配：使用频率高的品类分配更多预算
- 给出多套方案（升级派/实用派/性价比派）
- 每套方案算出合计与余量

#### 5.2 工具调用顺序

```
用户提出场景 + 总预算
  → [Step 1] SkuRecallShopping（品类1，传对应预算上限）
  → [Step 2] SkuRecallShopping（品类2，传对应预算上限）
  → [Step N] SkuRecallShopping（品类N）
  → [Step N+1] PythonCalculator（算账：各品类商品价格相加，输出多套方案合计）
  → [Step N+2] final_response（展示预算分配表格 + 方案对比 + 建议）
```

#### 5.3 SkuRecallShopping 输入 Schema（组合购物模式）

```json
{
  "query": "string — 单品类搜索词，如'炒锅 不粘锅 麦饭石/钛合金'",
  "max_price": "number — 该品类的预算上限（按比例拆分），如900",
  "min_price": "number — 该品类的预算下限（可选）",
  "is_platform_self": "boolean — 是否限定平台自营"
}
```

#### 5.4 PythonCalculator 输入/输出 Schema

**输入 Schema**：

```json
{
  "code": "string — Python 代码字符串，计算各方案总价和余量，示例如下"
}
```

**Python 代码格式示例**：

```python
a = 459 + 699 + 369 + 269   # 升级派：苏泊尔钛+双立人+WMF+Tefal
b = 459 + 459 + 369 + 269   # 实用派：苏泊尔钛+十八子作+WMF+Tefal
c = 199 + 459 + 369 + 269   # 性价比派：炊大皇+十八子作+WMF+Tefal
print(f'方案A 升级派: {a}, 余{2000-a}')
print(f'方案B 实用派: {b}, 余{2000-b}')
print(f'方案C 性价比派: {c}, 余{2000-c}')
```

**输出 Schema**：

```json
{
  "status": "SUCCESS",
  "products": [
    {
      "product_id": "calc_b2",
      "title": "预算分配",
      "price": 0.0,
      "is_platform_self": false,
      "rating": 5.0,
      "key_specs": "A升级派1796(余204)/B实用派1556(余444)/C性价比1296(余704)",
      "sales": "—"
    }
  ]
}
```

#### 5.5 Mock 数据示例（5000元客厅音响）

```json
[
  {
    "step_id": 1,
    "step_type": "tool_call",
    "tool_name": "SkuRecallShopping",
    "tool_input": {"query": "客厅书架音箱 hifi", "min_price": 2500, "max_price": 4000, "is_platform_self": true},
    "tool_output": {
      "status": "SUCCESS",
      "products": [
        {"product_id": "mock_bundle_001a", "title": "JBL Stage A170 落地式音箱 一对", "price": 3499.0, "is_platform_self": true, "rating": 4.8, "key_specs": "落地式/双6.5寸低音/适合15-25㎡客厅", "sales": "月销680"}
      ]
    }
  },
  {
    "step_id": 2,
    "step_type": "tool_call",
    "tool_name": "SkuRecallShopping",
    "tool_input": {"query": "功放 蓝牙HiFi 客厅", "min_price": 800, "max_price": 1500},
    "tool_output": {
      "status": "SUCCESS",
      "products": [
        {"product_id": "mock_bundle_001c", "title": "天逸 AD-86D 高保真合并功放", "price": 1180.0, "is_platform_self": true, "rating": 4.8, "key_specs": "2×120W/蓝牙5.0/4-8Ω通用", "sales": "月销380"}
      ]
    }
  },
  {
    "step_id": 3,
    "step_type": "tool_call",
    "tool_name": "PythonCalculator",
    "tool_input": {
      "code": "a = 3499 + 1180 + 200\nb = 4999\nprint(f'方案A 分体派: {a}元, 余{5000-a}')\nprint(f'方案B 一体派: {b}元, 余{5000-b}')"
    },
    "tool_output": {
      "status": "SUCCESS",
      "products": [{"product_id": "calc_b1", "title": "预算分配", "price": 0.0, "is_platform_self": false, "rating": 5.0, "key_specs": "方案A:4879元(余121)/方案B:4999元(余1)/差120", "sales": "—"}]
    }
  }
]
```

---

### 6. place_order — 购物下单

#### 6.1 场景说明

用户明确要下单、查订单、申请退换货、查物流。本场景包含两个主工具：
- `ShoppingPlaceOrderTool`：执行购物操作（下单/预约/抢购/换货）
- `OrderQuerySkill`：查询操作（订单状态/退换货申请/物流跟踪）

**重要规则**：`ShoppingPlaceOrderTool` 必须传 `product_id`，不能只传品类名称，否则返回 `CALLER_ERROR`。如果用户没有明确商品 ID，必须先调用 `SkuRecallShopping` 确认商品。

#### 6.2 工具调用顺序

**正确流程（已知商品 ID）**：
```
用户明确下单（商品已在对话中出现）
  → [Step 1] ShoppingPlaceOrderTool（product_id 来自前文推荐）
  → [Step 2] final_response（含订单号+预计送达时间）
```

**正确流程（未知商品 ID）**：
```
用户说"帮我下单一台电吹风"（未指定具体商品）
  → [Step 1] SkuRecallShopping（先搜索确认商品）
  → [Step 2] final_response（确认商品，询问用户是否下单）
  -- 用户确认后 --
  → [Step 3] ShoppingPlaceOrderTool（使用 Step 1 返回的 product_id）
  → [Step 4] final_response（下单成功）
```

**错误流程（负样本示例，tool_call_order_wrong）**：
```
用户说"帮我下单一台便宜的电吹风"
  → [Step 1] ShoppingPlaceOrderTool（直接传 category，缺少 product_id）← CALLER_ERROR
  → [Step 2] SkuRecallShopping（补救搜索）← 顺序错误，属于 reward hacking
```

#### 6.3 ShoppingPlaceOrderTool 输入/输出 Schema

**基础下单输入**：

```json
{
  "product_id": "string — 必填，商品ID，如'mock_11223344'",
  "quantity": "integer — 数量，默认1",
  "address": "string — 收货地址，'DEFAULT'表示默认地址，或具体地址字符串",
  "payment_method": "string — 支付方式，'default'表示默认支付",
  "services": ["array — 增值服务，如['碎屏险', '延保3年']"],
  "invoice": {"type": "string", "title": "string"},
  "promotion": "string — 使用优惠券/满减活动名称（可选）"
}
```

**预约购买输入**：

```json
{
  "product_id": "string — 商品ID",
  "quantity": 1,
  "action": "reserve",
  "scheduled_time": "string — 预约到货时间，如'2026-08-01 10:00'"
}
```

**限量抢购输入**：

```json
{
  "product_id": "string — 商品ID",
  "quantity": 1,
  "action": "flash_sale",
  "release_time": "string — 开售时间，如'2026-07-20 10:00:00'",
  "limit_per_account": "integer — 限购数量"
}
```

**输出 Schema**：

```json
{
  "status": "SUCCESS | FAILED | CALLER_ERROR",
  "products": [
    {
      "product_id": "string — 下单的商品ID",
      "title": "string — 商品标题",
      "price": "number — 实付价格",
      "is_platform_self": true,
      "rating": 4.8,
      "key_specs": "string — 含订单号+预计送达时间，如'订单号 ORDER-EXAMPLE-001/预计明天 18:00 前送达'",
      "sales": "string — '平台自营'"
    }
  ]
}
```

#### 6.4 OrderQuerySkill 输入/输出 Schema

**订单查询输入**：

```json
{
  "order_id": "string — 订单号（可选），如'ORDER-EXAMPLE-001'",
  "category_keyword": "string — 品类关键词（按品类查时使用），如'空气净化器'",
  "time_range": "string — 时间范围，'all'/'last_30_days'/'last_6_months'",
  "status": "string — 订单状态筛选，'completed'/'pending'/'refund'"
}
```

**退换货申请输入**：

```json
{
  "order_id": "string — 订单号",
  "issue_type": "string — 问题类型，'quality_issue'/'not_as_described'/'wrong_item'",
  "user_intent": "string — 用户意图，'refund'/'exchange'",
  "action": "apply_return"
}
```

**输出 Schema**：

```json
{
  "status": "SUCCESS",
  "products": [
    {
      "product_id": "string — 历史订单商品ID",
      "title": "string — 商品标题",
      "price": "number — 购买价格",
      "is_platform_self": true,
      "rating": 4.8,
      "key_specs": "string — 购买时间/订单号/当前状态，如'购买于2025-09-12/订单ORDER-EXAMPLE-002'",
      "sales": "string — 原装型号或兼容型号"
    }
  ]
}
```

#### 6.5 Mock 数据示例（下单成功）

```json
{
  "step_id": 1,
  "step_type": "tool_call",
  "tool_name": "ShoppingPlaceOrderTool",
  "tool_input": {
    "product_id": "mock_11223344",
    "quantity": 1,
    "address": "DEFAULT",
    "payment_method": "default"
  },
  "tool_output": {
    "status": "SUCCESS",
    "products": [
      {
        "product_id": "mock_11223344",
        "title": "小米米家颈椎按摩仪 3档强度 一键启动 热敷功能",
        "price": 349.0,
        "is_platform_self": true,
        "rating": 4.8,
        "key_specs": "订单号 ORDER-EXAMPLE-001/预计明天 18:00 前送达",
        "sales": "平台自营"
      }
    ]
  },
  "error_type": null
}
```

---

### 7. repurchase — 复购召回

#### 7.1 场景说明

用户想复购历史上买过的商品，可能记不清品牌/型号，Agent 通过 `SkuRepurchaseRecall` 查询历史订单，找到相关商品，并推荐复购或升级替代。典型触发词：「之前买过」「想再买」「帮我查一下当时买的是哪款」「该换了」。

**标准复购流程** = `SkuRepurchaseRecall` 查历史 + 必要时 `SkuRecallShopping` 补召回配件。

#### 7.2 工具调用顺序

**直接复购（记得品牌）**：
```
用户说"之前买的无糖奶茶帮我再买一箱"
  → [Step 1] SkuRepurchaseRecall（category_keyword + time_range）
  → [Step 2] final_response（显示历史订单+推荐复购+相似品）
```

**复购+配件搜索（如滤网换购）**：
```
用户说"净化器滤网该换了"
  → [Step 1] OrderQuerySkill（查历史订单，找净化器型号）
  → [Step 2] SkuRecallShopping（按型号召回对应滤网）
  → [Step 3] final_response（显示历史订单信息+滤网推荐）
```

#### 7.3 SkuRepurchaseRecall 输入/输出 Schema

**输入 Schema**：

```json
{
  "category_keyword": "string — 品类关键词，如'洗衣液'/'无糖奶茶'/'滤芯'",
  "time_range": "string — 时间范围，'last_3_months'/'last_6_months'/'last_1_year'/'all'",
  "include_similar": "boolean — 是否同时返回相似推荐（历史品类的新款/替代款），默认true",
  "predict_usage": "boolean — 是否预测用量/到期时间，默认false",
  "show_alternatives": "boolean — 是否展示平替商品，默认false",
  "show_new_edition": "boolean — 是否展示新版本/升级款",
  "suggest_bundle": "boolean — 是否推荐搭配商品",
  "include_subscription": "boolean — 是否推荐订阅购"
}
```

**输出 Schema**：

```json
{
  "status": "SUCCESS | NO_RESULT",
  "products": [
    {
      "product_id": "string — 历史购买或推荐商品的ID",
      "title": "string — 商品标题（历史品加'你X个月前购买过'标注）",
      "price": "number — 当前售价",
      "is_platform_self": true,
      "rating": 4.9,
      "key_specs": "string — 含购买时间/订单号/耗材型号等关键信息",
      "sales": "string — 月销量"
    }
  ]
}
```

#### 7.4 Mock 数据示例（复购洗衣液）

```json
{
  "step_id": 1,
  "step_type": "tool_call",
  "tool_name": "SkuRepurchaseRecall",
  "tool_input": {
    "category_keyword": "洗衣液",
    "time_range": "last_6_months"
  },
  "tool_output": {
    "status": "SUCCESS",
    "products": [
      {
        "product_id": "mock_rep_001",
        "title": "蓝月亮亮白洗衣液 3kg×2瓶 深层洁净",
        "price": 89.0,
        "is_platform_self": true,
        "rating": 4.9,
        "key_specs": "你2个月前购买1组(订单[ORDER_ID])/3kg×2瓶/月销5万",
        "sales": "月销5万"
      }
    ]
  },
  "error_type": null
}
```

#### 7.5 Mock 数据示例（复购+配件联动）

```json
[
  {
    "step_id": 1,
    "step_type": "tool_call",
    "tool_name": "OrderQuerySkill",
    "tool_input": {
      "category_keyword": "空气净化器",
      "time_range": "all",
      "status": "completed"
    },
    "tool_output": {
      "status": "SUCCESS",
      "products": [
        {
          "product_id": "mock_42118801",
          "title": "小米米家空气净化器4 Pro 除甲醛CADR 500m³/h",
          "price": 1599.0,
          "is_platform_self": true,
          "rating": 4.8,
          "key_specs": "购买于2025-09-12/订单ORDER-EXAMPLE-002/已使用约9个月",
          "sales": "原装滤芯型号 M16-FLP-T"
        }
      ]
    }
  },
  {
    "step_id": 2,
    "step_type": "tool_call",
    "tool_name": "SkuRecallShopping",
    "tool_input": {
      "query": "米家空气净化器4 Pro 滤芯 M16-FLP-T 原装",
      "is_platform_self": true
    },
    "tool_output": {
      "status": "SUCCESS",
      "products": [
        {
          "product_id": "mock_42118899",
          "title": "小米米家空气净化器4 Pro 原装滤芯 除甲醛增强版 M16-FLP-T",
          "price": 249.0,
          "is_platform_self": true,
          "rating": 4.9,
          "key_specs": "原装H13级HEPA+椰壳活性炭/适配4 Pro/CCM甲醛F4级",
          "sales": "月销1.8万件"
        }
      ]
    }
  }
]
```

---

## SFT 数据格式规范

### trajectory_id 命名规则

```
格式：sft_{场景缩写}_{三位序号}
```

| 场景 | 缩写 | 示例 |
|---|---|---|
| search_recommend | ecom | sft_ecom_001 ~ sft_ecom_035 |
| similar_rec | simrec | sft_simrec_001 ~ sft_simrec_008 |
| sku_comp | skucomp | sft_skucomp_001 ~ sft_skucomp_008 |
| matching_purchase | match | sft_match_001 ~ sft_match_007 |
| bundle_purchase | bundle | sft_bundle_001 ~ sft_bundle_008 |
| place_order | order | sft_order_001 ~ sft_order_003 |
| repurchase | history | sft_history_001 ~ sft_history_003 |
| 负样本 | bad | sft_bad_001 ~ sft_bad_024 |

### steps 结构规范

每条 trajectory 的 `steps` 数组由以下两种类型交替组成：

**tool_call 类型**：

```json
{
  "step_id": 1,
  "step_type": "tool_call",
  "tool_name": "string — 真实工具名",
  "tool_input": {"object — 工具输入参数"},
  "tool_output": {
    "status": "SUCCESS | FAILED | CALLER_ERROR | NO_RESULT",
    "products": ["array — 商品列表或计算结果"]
  },
  "error_type": "null（正常）| CALLER_ERROR（参数错误）| TIMEOUT（超时）| NO_RESULT（无结果）"
}
```

**final_response 类型**：

```json
{
  "step_id": 2,
  "step_type": "final_response",
  "content": "string — 面向用户的完整回复（Markdown 格式）",
  "product_cards": [
    {
      "card_id": "string — 必须与 tool_output 中某个 product_id 完全一致",
      "display_price": "number — 展示价格，必须与 tool_output 中该商品 price 一致",
      "reason": "string — 30-50字的推荐理由，包含核心差异化优势"
    }
  ]
}
```

### product_cards 与 product_id 的对应关系

**关键约束**（违反此规则为 `card_id_hallucination` 负样本）：

1. `product_cards[].card_id` 必须出现在本 trajectory 某个 `tool_output.products[].product_id` 中
2. `product_cards[].display_price` 必须与对应 product_id 的 `price` 字段完全一致（不能改价）
3. `final_response` 文本中提到的价格必须与 `product_cards[].display_price` 一致
4. 不能在 tool_output 中不存在的商品上生成 product_card

**正确示例**：

```json
// tool_output 中有：{"product_id": "mock_11223344", "price": 349.0}
// product_cards 中必须是：{"card_id": "mock_11223344", "display_price": 349.0}
```

**错误示例（负样本）**：

```json
// tool_output 中没有此 product_id，但 product_cards 里凭空出现
// {"card_id": "mock_99999999", "display_price": 299.0} ← card_id_hallucination
```

### 各场景 final_response 质量标准

| 场景 | 必须满足 | 禁止出现 |
|---|---|---|
| **search_recommend** | 3-5款推荐，有明确首选标注，有场景化建议 | 超过用户预算的商品，没有推荐理由 |
| **similar_rec** | 明确说明是针对哪个抱怨维度调整的，新推荐与被拒商品有明显差异 | 推荐与被拒商品雷同，忽视抱怨维度 |
| **sku_comp** | 包含 Markdown 对比表格，有明确的场景化推荐，不是简单参数罗列 | 维度权重与用户场景脱节，只列参数不给结论 |
| **matching_purchase** | 解释搭配逻辑（色彩/材质/风格），包含避坑提示 | 提到价格约束，推荐与核心商品风格明显冲突 |
| **bundle_purchase** | 含预算分配表格，至少 2 套方案，必须有 PythonCalculator 算账结果 | 总价超出用户预算，没有给出明确推荐方案 |
| **place_order** | 下单成功回复包含订单号+预计送达时间；失败回复有具体指引步骤 | 订单号与 tool_output 不一致，捏造送达时间 |
| **repurchase** | 明确标注历史购买时间+订单号，复购推荐与历史商品型号对应 | 历史商品信息与 tool_output 不一致，凭空捏造购买记录 |

---

## Mock 数据规范

### product_id 格式

```
格式：mock_{XXXXXXXX}
```

| 类型 | 格式 | 示例 |
|---|---|---|
| 普通搜索结果商品 | `mock_` + 8位数字 | mock_11223344, mock_55667788 |
| similar_rec 场景商品 | `mock_simrec_` + 3位序号 + 字母 | mock_simrec_001a, mock_simrec_002b |
| sku_comp 场景商品 | `mock_skucmp_` + 3位序号 + 字母 | mock_skucmp_001a, mock_skucmp_003c |
| matching_purchase 场景 | `mock_match_` + 3位序号 + 字母 | mock_match_001a, mock_match_003b |
| bundle_purchase 场景 | `mock_bundle_` + 3位序号 + 字母 | mock_bundle_001a, mock_bundle_002c |
| repurchase 场景 | `mock_rep_` + 3位序号 | mock_rep_001, mock_rep_002 |
| PythonCalculator 结果 | `calc_` + `b` + 数字 | calc_b1, calc_b2 |
| 历史购买商品 | `mock_` + 8位数字（复购时同原始商品ID） | mock_42118801 |

### 价格范围参考

| 品类 | 低价区间 | 中价区间 | 高价区间 |
|---|---|---|---|
| 手机 | ¥1000-2000 | ¥2000-4000 | ¥4000-7000 |
| 家电（大件）| ¥500-1500 | ¥1500-4000 | ¥4000-10000 |
| 小家电 | ¥99-299 | ¥299-999 | ¥999-3000 |
| 服装单品 | ¥99-299 | ¥299-999 | ¥999-5000 |
| 家居家具 | ¥99-499 | ¥499-2000 | ¥2000-8000 |
| 食品饮料（箱装）| ¥30-60 | ¥60-150 | ¥150-400 |
| 3C 配件 | ¥29-99 | ¥99-399 | ¥399-1500 |
| 厨具 | ¥99-299 | ¥299-999 | ¥999-3000 |

### 月销量参考格式

月销量字段 `sales` 统一使用以下格式：

```
"月销{数字}{单位}"
```

| 销售量级 | 格式示例 |
|---|---|
| 头部爆款（>2万）| "月销3.2万件" / "月销5万" |
| 畅销款（5000-2万）| "月销1.8万" / "月销1.2万" / "月销8500" / "月销6500" |
| 正常销售（1000-5000）| "月销4500" / "月销2200" / "月销1500" |
| 小众/高端款（<1000）| "月销680" / "月销420" / "月销380" |
| 特殊商品（PythonCalculator）| "—"（横线，表示非实际销售商品）|

**注意**：万以上的写 `X万` 或 `X.X万`，不写 `X0000`。单位件/组可省略，保持风格统一。

### rating 评分范围

```
范围：4.5 ~ 4.9（浮点数，保留1位小数）
```

| 评分 | 适用场景 |
|---|---|
| 4.9 | 顶级爆款，品牌旗舰，口碑标杆 |
| 4.8 | 主流推荐款，品牌主力型号 |
| 4.7 | 次推款，性价比选择 |
| 4.6 | 入门选择，有明显短板 |
| 4.5 | 不推荐但仍出现（对比时作为反例）|

**约束**：不使用 4.5 以下的评分（低于 4.5 的商品不应出现在推荐结果中）；PythonCalculator 结果的 rating 固定为 5.0。

### 订单号格式

```
格式：[ORDER_ID]
示例：ORDER-EXAMPLE-001, ORDER-EXAMPLE-002
```

### is_platform_self 字段规范

- 绝大多数推荐商品 `is_platform_self: true`（平台自营）
- 部分高端/进口/小众商品可以 `false`（第三方旗舰店）
- PythonCalculator 结果的 `is_platform_self: false`

---

*本文档对应数据集：`sft_data/trajectories_final.jsonl`，共 74 条 trajectory，7 个核心场景。所有工具名来自 shopping-chatbot 项目 `core/multi_agent/shopping/tool_list.py`，所有商品信息均为模拟生成。*
