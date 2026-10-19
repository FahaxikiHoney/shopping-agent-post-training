# Joybuy Mock 600 条真实 Query 全量审计报告 v11

## 产物

- 原始 Query：`sft_data/training-data/data/trajectory_inputs/queries_600.jsonl`
- 最新工具回放：`sft_data/mock_queries600_direct_replay_v11_20260817.json`
- 独立语义审计：`sft_data/mock_queries600_semantic_audit_v4_20260817.json`
- 定向真实模型轨迹：`sft_data/mock_live_semantic_recheck2_20260817.jsonl`
- 定向质量报告：`sft_data/mock_live_semantic_recheck2_quality_20260817.json`

## 全量结果

- Query 总数：600
- 高精度非空召回：59
- 安全空召回：541
- 分站点非空：DE 18、FR 14、NL 11、UK 16
- 未归一化但非空：3 条，分别为 LEGO 一般推荐、LEGO 品牌介绍、女孩益智玩具；均人工确认相关
- 独立 LLM judge：42 pass、17 warning、0 fail
- 定向真实模型复验：2/2 执行成功，2/2 质量门禁通过
- 自动化测试：96/96 通过

## 相比 v9 的变化

- 多品类 TV + 支架 + 投屏器 Query 不再被单次 `sku_recall` 错当成纯电视搜索；正式 runner 会通过 `bundle_purchase` 拆为三个独立需求。
- 75 英寸 Smart TV、G-Sync 显示器、Google TV、120/144Hz、中国彩妆和 RC 漂移车等真实规格已显式进入商卡标题。
- 中国访客零食的品牌展示从内部式 `THREEPOINTS` 等名称改为 `Three Squirrels`、`Bestore`、`Want Want`、`Haochidai`。
- TP07 商卡显式展示为 tower/column fan 对应站点本地化名称。
- 上述标题增强使独立 judge 中 Smart TV、G-Sync、中国彩妆、中国零食和塔式风扇等样本由 warning 转为 pass。
- 语义审计器补充 `socket.timeout` 自动重试，长批次可从 checkpoint 稳定续跑。

## 剩余 17 条 warning

剩余 warning 均不应通过伪造商品字段消除，主要包括：

- 实时促销、当前库存、最新款或最近上市
- 3–5 年精确保质期
- “高性价比”“很便宜”“适合女孩”等主观条件
- 杯子颜色、材质、耐用度等当前契约不可见属性
- 工程/3D 渲染适用性、低延迟、不留水痕等性能效果
- RC 车无刷电机、液压避震、零件供应等复杂参数

这些查询在最终回复中应继续通过免责声明、缺货说明或追问处理，而不是扩展为不可验证的事实。

## 结论

当前工具召回层在完整 600 条真实 Query 上保持 0 个语义 fail。Mock 与真实系统不要求轨迹结构和召回数量逐条一致，但在工具契约、专门子类型精度、多语言站点展示、事实约束、bundle 缺项表达和最终轨迹门禁方面已达到稳定可训练、可对比的能力标准。
