# Mock sku_recall 真实契约改造设计

## 目标

保留 Mock 商品库和单 Agent ReAct 执行方式，但让训练轨迹中可见的 `sku_recall` 调用参数、返回字段、空召回行为和商品字段与真实 Shopping 项目一致。

## 契约

- 输入只允许 `query`。
- 价格、品牌、尺寸和使用场景直接包含在自然语言查询中。
- 输出固定包含 `success`、`query`、`count`、`sku_list`、`sku_map`、`products`、`recall_intent`、`executed_queries`、`brand_boost_targets`。
- 商品字段固定为 `sku_id`、`sku_name`、`brand_name`、`final_price`、`price`、`img_url`、`good`、`sales`、`keyword`。
- 空召回仍返回成功结构，`count=0`，不增加 Mock 专有的 `no_stock` 或 `message` 字段。

## 商卡映射

真实工具结果不包含展示索引。Agent 按所有召回结果在当前回复中的出现顺序生成 `[product:1]`、`[product:2]`，但不修改工具 JSON。

## 验证

- 校验 Schema 只接受 `query`。
- 校验成功和空召回的字段集合。
- 校验价格约束从自然语言中生效。
- 校验 Agent 生成的工具结果不包含旧字段和注入的 `index`。

## 训练 Query 策略

- 不以复现真实线上空召回率为训练目标。
- 正常训练题库使用真实用户表达风格，但每条 query 必须能命中 Mock 商品库。
- 无货和空召回作为显式专项场景，通过 `--include-empty` 开启，不默认混入训练数据。
- 用真实 query 回放只用于识别商品库覆盖缺口，不能直接作为训练质量指标。
