# Joybuy Mock 固定 100 条真实 Query 闭环报告

## 样本与产物

- 原始数据：`sft_data/training-data/data/trajectory_inputs/queries_600.jsonl`
- 固定样本：`sft_data/queries_600_sample100_seed20260817.jsonl`
- 抽样方式：种子 `20260817`，UK / DE / FR / NL 各 25 条
- 工具直放：`sft_data/mock_queries100_direct_replay_v10_20260817.json`
- 独立语义审计：`sft_data/mock_queries100_semantic_audit_v10_20260817.json`
- 完整模型轨迹：`sft_data/mock_queries100_live_v11_20260817.jsonl`
- 自动质量报告：`sft_data/mock_queries100_live_v11_quality_20260817.json`

## 最终结果

- 完整模型执行：100 / 100 成功
- 自动质量门禁：100 / 100 通过，0 warning，0 issue
- 工具直放：21 条非空召回，79 条安全空召回
- 独立 LLM 语义审计：15 pass，6 warning，0 fail
- 完整轨迹：28 条带商卡，72 条无商卡
- 两个标注 bundle 样本均自动进入 `bundle_purchase`
- 平均 `sku_recall` 1.8 次，最大 5 次
- 商卡重复 0 条
- “首次空召回后放宽并命中”的残余案例 0 条
- 自动化测试：95 / 95 通过

## 本轮发现并修复的问题

1. 批跑器此前强制使用 `search_recommend`，没有利用真实样本的 bundle 标签；现默认 `--scenario auto`。
2. TV 支架和投屏器需求会被 `tv` / `laptop` 带偏；现按独立 bundle 项搜索，无货时明确报告组合未配齐。
3. 编号采购清单会被连接词错误拆分；现优先按编号条目拆分。
4. 仓鼠、米糕、防晒、d’alba、Kérastase、Ariana Grande 等无货意图会被放宽为泛品类；现锁定原 Query，只允许一次精确搜索。
5. 浴室柜会被普通收纳柜冒充；现作为专门子类型闭集处理。
6. 普通搜索可能产生数十次空工具调用；现每条 `search_recommend` 最多 5 次 `sku_recall`。
7. 荷兰语 `kan je ...` 会因 `je` 被误判为法语；现改为多语言强标记计分。
8. 长英文 Query 在非英语站点可能错误回退到站点语言；现补齐 `what/search/best/how` 等英文强标记，短 Query 仍使用站点语言。
9. 部分品类有货、部分无货时最终回复可能漏报缺项；现自动添加本地化的“推荐未完全覆盖”说明。
10. Smart TV、Google TV、120/144Hz、G-Sync、中国彩妆、RC 漂移车等可证实信息已进入本地化商卡标题。

## 保留的 warning

6 个语义 warning 都属于契约字段无法严格证明的属性，例如实时促销/最新、3–5 年保质期、主观质量、精确颜色材质、复杂 RC 参数，以及 bundle 中缺货的配件。Mock 不补造字段，而是在最终回复中给出免责声明或明确缺货。

## 结论

当前 Mock 已达到“可用于真实 Query 轨迹训练与能力对比”的标准：不追求与真实多 Agent 轨迹逐步一致，但工具契约、语言、站点本地化、事实约束、专门子类型精度、bundle 缺项表达和轨迹质量均具备稳定自动门禁。当前主要限制来自商品库覆盖，而不是轨迹框架或调用契约。
