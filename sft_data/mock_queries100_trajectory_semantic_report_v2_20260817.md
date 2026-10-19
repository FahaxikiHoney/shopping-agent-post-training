# Joybuy Mock 100 条完整轨迹独立语义审计

## 产物

- 完整轨迹：`sft_data/mock_queries100_live_v12_20260817.jsonl`
- 自动质量门禁：`sft_data/mock_queries100_live_v12_quality_20260817.json`
- 独立语义审计：`sft_data/mock_queries100_trajectory_semantic_audit_v2_20260817.json`

## 结果

- 完整执行：100/100
- 自动质量门禁：100/100，0 warning，0 issue
- 独立最终回复语义审计：80 pass、20 warning、0 fail
- 自动化测试：100/100

## 独立审计发现并修复的问题

1. `Welcher frische Fisch ist heute reduziert?` 未覆盖 `heute reduziert` 动态表达；现添加实时活动免责声明。
2. `welche sind die neusten getränke ...` 未识别 `neusten` 词形；现添加新品时间不可验证说明。
3. UK 站点歧义 Query `2.56` 的模型澄清示例使用了 `¥`；最终回复归一化会把默认人民币符号替换成站点币种 `£`。
4. 质量门禁同步补齐 `heute reduziert` 和 `neusten`，避免未来回归。

## 剩余 warning 构成

- 无库存或安全空召回
- Query 本身过短、歧义或缺少商品类别
- 客服/订单/优惠券等超出购物检索工具能力的问题
- 实时促销、当前库存、最新款、外部商店价格等动态数据不可用
- 颜色、材质、耐用度、适用人群等当前商品契约不可见或主观条件

这些 warning 均没有无关商品、工具外事实、错误语言或隐藏缺货，因此不应通过虚构数据强制变成 pass。
