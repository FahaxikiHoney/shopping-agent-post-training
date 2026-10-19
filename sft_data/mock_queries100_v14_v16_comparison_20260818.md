# Joybuy Mock 100 条修复前后对比（v14 → v16）

日期：2026-08-18

## 结论

- Mock 已达到可用于轨迹训练与真实轨迹能力对比的基础标准：工具契约一致、场景召回可用、商卡可追溯、语言/币种/事实约束与直出安全路由均有门禁。
- 本轮不是追求与真实系统逐步完全一致，而是保证相同购物任务下具备合理的检索、候选筛选、商卡展示和无结果处理能力。
- 同口径 LLM Judge 平均分由 **0.8055** 提升到 **0.9035**；满分由 **72** 条提升到 **78** 条；零分由 **19** 条降到 **9** 条。

## 核心指标

| 指标 | v14 | v16 | 变化 |
|---|---:|---:|---:|
| 执行完成 | 100/100 | 100/100 | 持平 |
| 规则门禁通过 | 99/100 | 100/100 | +1 |
| 有商卡轨迹 | 22/100 | 34/100 | +12 |
| 无工具轨迹 | 16 | 5 | -11 |
| 场景召回轨迹 | 8 | 4 | -4 |
| LLM Judge 平均分 | 0.8055 | 0.9035 | +0.0980 |
| LLM Judge 满分 | 72 | 78 | +6 |
| LLM Judge 零分 | 19 | 9 | -10 |

## 五维通过数

| 维度 | v14 | v16 | 变化 |
|---|---:|---:|---:|
| D1 需求理解 | 82/100 | 91/100 | +9 |
| D2 事实准确 | 100/100 | 100/100 | +0 |
| D3 推荐质量 | 86/100 | 99/100 | +13 |
| D4 完整性 | 88/100 | 100/100 | +12 |
| D5 推荐价值 | 77/100 | 84/100 | +7 |

## 多站点商卡覆盖

| 站点 | v14 有商卡轨迹 | v16 有商卡轨迹 |
|---|---:|---:|
| DE-Site | 6 | 9 |
| FR-Site | 9 | 8 |
| NL-Site | 4 | 5 |
| UK-Site | 3 | 12 |

## 本轮修复

- Judge 不再强制美元符号，并纳入原价、销量、关键词、规格和匹配原因，减少正确内容被误判为幻觉。
- 明确购物 Query 默认至少调用一次 `sku_recall`，同时保留政治、隐私、缺图和商品使用安全问答的直接回复能力。
- Query 层新增多类高置信 Mock 商品，不对 100 条逐条硬编码，也不为所有未知 Query 无限制造商品。
- 场景型搜索继续并行使用主召回与 `scenario_related_recall`，最终商卡仍由模型从两路候选中选择。
- 修复帐篷灯误召回帐篷、站外价格免责声明、商品使用问答误搜索等问题。
- 新增隐私越权安全直出：拒绝默认授权、拒绝取消脱敏、拒绝跳过账号归属确认；该单条规则门禁和 LLM Judge 均为 1.0。

## 剩余问题

v16 仍有 9 条零分，主要不是轨迹格式或商卡协议错误，而是 Mock 商品覆盖与空召回后的服务策略不足：

### 回复价值或完整性不足（2 条）

- `Nothing Ear ecouteurs Bluetooth sans Fil avec Intégration de ChatGPT, Son Haute résolution 24 Bits, Réduction Active de Bruit Intelligente, Égaliseur avancé et Jusqu’à 40,5 Heures d’écoute - Noir`：失败维度 d1_need_understanding, d5_recommendation_value；助手在无货时正确说明了情况，但未主动推荐替代品且缺乏推荐理由。
- `Hi3 Freestanding Side by Side refrigerator, 544 L RS3P558NEID`：失败维度 d1_need_understanding, d5_recommendation_value；助手如实说明了无货情况，但未主动推荐替代品，缺乏推荐理由。

### 空召回后替代或检索策略不足（6 条）

- `你好 我想找一个适用于180*200cm床的床单或者床笠，有链接推荐吗，我找了一圈只看到成套的或者床笠尺寸150*200的。谢谢`：失败维度 d1_need_understanding；助手如实反馈了无货情况，但在无货时缺乏主动寻找替代方案的意识，服务不够完善。
- `类似白芷的香料还有哪些？`：失败维度 d1_need_understanding；助手在工具无果时仅说明情况未推替代品，需求理解不充分，但无货处理符合基本要求。
- `Recommend a shampoo without sulfates for pored hair with dandruff and itchy scalp`：失败维度 d1_need_understanding；助手如实处理了无货情况，但未按规则尝试推荐替代品，需求理解环节存在不足
- `i need shoes that help with foot odour`：失败维度 d1_need_understanding；助手正确识别需求但未在无货时提供替代品，仅做了澄清引导
- `je veux voir les meilleures offres pour: la ps5 et la ps5 pro, évidemment neuve`：失败维度 d1_need_understanding；助手正确理解了需求并在无货时合理说明，但未主动尝试推荐替代品，服务体验有提升空间。
- `立体空调`：失败维度 d1_need_understanding；助手如实反馈了无货情况，但未能理解用户模糊意图且未提供替代方案。

### 商品覆盖或推荐相关性不足（1 条）

- `SCHOLL 2 en 1 exfoliant et lissant`：失败维度 d1_need_understanding, d3_recommendation_quality, d5_recommendation_value；助手如实反馈了无货情况，但缺乏主动性，未尝试更广泛的搜索来为用户提供替代方案，整体服务体验不理想

建议下一轮优先补充可泛化的商品族与别名，例如明确型号耳机/冰箱、专业洗发护发、足部除味鞋、PS5 主机、Scholl 足部护理和立式空调；不要针对单条 Query 写死返回。

## 最终产物

- 原始 100 条：`sft_data/mock_queries100_live_v16_20260818_raw.jsonl`
- 规则门禁：`sft_data/mock_queries100_live_v16_20260818_quality.json`
- 清洗训练格式：`sft_data/mock_购物助手_思考链_清洗后_100条_v16_20260818.jsonl`
- v16 合并 Judge：`sft_data/mock_queries100_live_v16_llm_eval_merged_20260818.jsonl`
- v14 同口径 Judge：`sft_data/mock_queries100_live_v14_llm_eval_merged_fixedjudge_20260818.jsonl`
- LLM Judge 代码：`llm_evaluation/evaluate.py`
- LLM Judge 使用说明：`llm_evaluation/README.md`

## 说明

- LLM Judge 存在少量随机性；本报告使用重试结果覆盖临时 503/超时，并对 direct_response 使用对应评估口径。
- v16 没有重新调用模型跑完 100 条；它以 v15 的 99 条不受影响轨迹加上重新生成的隐私安全轨迹组成。因为本次代码改动只影响隐私越权直出路由，这样可避免无关模型随机波动。
