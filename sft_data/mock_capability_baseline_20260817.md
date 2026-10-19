# Shopping Mock 当前能力基线（2026-08-17）

## 验证范围

本基线验证 Mock 是否达到真实购物项目所需的能力标准，不要求轨迹阶段、工具步数、召回数量或商品集合与真实项目完全一致。

验证维度：

1. `sku_recall` 工具契约与商品字段。
2. UK、DE、FR、NL 四站点多语言检索。
3. GBP/EUR 预算、价格过滤和预算计算。
4. 商品标题、品牌、销量和币种本地化。
5. 商卡索引、去重、ClickText 和工具错误。
6. 站外比价、精确保质期等工具缺失事实的免责声明。
7. 普通搜索、组合购买、场景搭配等不同轨迹路径。

## 真实模型 Smoke Suite

运行命令：

```bash
PYTHONPYCACHEPREFIX=/tmp/codex-pycache \
python3 scripts/run_mock_capability_smoke.py \
  --output sft_data/mock_capability_smoke_20_20260817.jsonl
```

固定样本：

| ID | 站点 | 场景 | 主要能力 |
|---|---|---|---|
| `uk_tv_constraints` | UK | 普通搜索 | 75 英寸、4K、£700 预算 |
| `uk_bundle_budget` | UK | 组合购买 | 两品类召回、GBP 预算计算、商卡与预算一致 |
| `de_multitool_budget` | DE | 普通搜索 | 德语复合词、多功能工具、€150 预算 |
| `de_shelf_life_grounding` | DE | 普通搜索 | 长保质期需求和事实免责声明 |
| `fr_matching` | FR | 场景搭配 | 法语品类、Nordic 风格池、单次场景工具 |
| `fr_quiet_aircon_budget` | FR | 普通搜索 | 静音空调、€300 预算、功率单位本地化 |
| `nl_external_price_comparison` | NL | 普通搜索 | Red Bull、Lidl 站外比价免责声明 |
| `nl_nail_polish_budget` | NL | 普通搜索 | 商品子类型 `nagellak`、€15 预算 |
| `uk_bundle_natural_language` | UK | 组合购买 | `and` 连接词、自然语言 GBP 总预算 |
| `de_bundle_natural_language` | DE | 组合购买 | `und` 连接词、德语形态变化、EUR 总预算 |
| `fr_bundle_natural_language` | FR | 组合购买 | `et` 连接词、法语自然预算表达 |
| `nl_bundle_natural_language` | NL | 组合购买 | `en` 连接词、荷兰语自然预算表达 |
| `uk_bundle_three_categories` | UK | 组合购买 | 逗号、`and`、三品类 GBP 预算 |
| `de_bundle_three_categories` | DE | 组合购买 | 德语三品类、Tastatur 本地化 |
| `fr_bundle_three_categories` | FR | 组合购买 | 法语三品类、clavier 本地化 |
| `nl_bundle_three_categories` | NL | 组合购买 | 荷兰语三品类、toetsenbord 本地化 |
| `uk_bundle_partial_recall` | UK | 组合购买 | 部分空召回、GBP 预算和缺失品类说明 |
| `fr_bundle_partial_recall` | FR | 组合购买 | 法语部分空召回和组合未配齐说明 |
| `uk_bundle_all_empty` | UK | 组合购买 | 全部空召回、不调用预算、不生成商卡 |
| `fr_bundle_all_empty` | FR | 组合购买 | 法语全空召回与语言感知连接词 |

运行结果：

- 核心样本：8/8 完成。
- 自然语言 bundle 扩展：4/4 完成。
- 三品类 bundle 扩展：4/4 完成。
- 部分召回 bundle 扩展：2/2 完成。
- 全空召回 bundle 扩展：2/2 完成。
- 合计：20/20 完成。
- 网关错误：首条出现一次 HTTP 503，退避重试后恢复。
- 轨迹状态：20/20 `done`。
- 工具错误：0。
- 自动质量门禁：20/20 通过，0 warning，0 issue。

## 人工审计补充

自动门禁通过后，人工检查发现空调标题中的中文“1.5 匹”被渲染成无单位裸数字 `1.5`。

修复后四站点分别使用：

- UK：`1.5 HP`
- DE：`1,5 PS`
- FR：`1,5 CV`
- NL：`1,5 pk`

法语目标样本重新运行：

```bash
python3 scripts/run_mock_capability_smoke.py \
  --case fr_quiet_aircon_budget \
  --output sft_data/mock_capability_smoke_fr_aircon_fixed_20260817.jsonl
```

结果：1/1 完成，质量门禁 1/1 通过，0 warning，0 issue。

## 当前证据

- 自动化测试：84/84 通过。
- 跨站点 Smoke：20/20 完成。
- Smoke 质量门禁：20/20 通过。
- 修复后空调目标复跑：1/1 通过。
- `sku_recall` 参数始终只有 `query`。
- 商品型工具输出使用统一真实商品字段。
- UK 使用 GBP；DE、FR、NL 使用 EUR。
- 最终回复跟随 Query 语言，短 Query 使用站点语言兜底。
- 无商品时不生成商卡；有商品时商卡索引合法且去重。
- 预算工具商品与最终组合商卡保持一致。
- 外部实时价格和精确保质期无法确认时明确说明数据边界。

## 尚未视为完成的范围

以下内容仍需持续回归，不应仅凭本次 20 条 Smoke 宣称全部长尾能力完成：

- 600 条 Query 中未覆盖的长尾商品品类。
- 四个以上品类、无明显连接词或多轮补充条件的组合购买表达。
- 商品规格字段进一步丰富后的事实一致性。
- 模型网关高并发下的 429/503 稳定性。
- 新增商品或本地化规则后的全库标题重复与语言泄漏。

## 第十四轮统一全库与精确属性审计

- 统一审计 `MOCK_PRODUCTS` 与 `MATCHING_PRODUCTS`：原始记录 641 条，合并重复建档后为 631 个唯一 SKU，覆盖 122 个品类。
- 为此前缺失的 55 个品类补齐 UK/DE/FR/NL 本地化名称；仍使用一套标准商品库，没有复制四套站点数据。
- 10 组同商品跨商品池重复建档已统一为同一 SKU 和同一商品字段；不同商品通过材质、风格或子类型描述区分。
- 四站点全库静态审计结果：缺失品类 0、中文标题 0、中文品牌 0、内部编号泄漏 0、不同 SKU 标题碰撞 0、同 SKU 跨池标题不一致 0。
- 增加通用数值属性硬过滤，支持容量、毫米规格和重量；`77-mm ND filter`、`1 L with straw`、`5 mm yoga mat`、`5 kg dumbbell` 均只返回精确匹配。
- 场景搭配会尊重单个需求中的显式风格和属性，例如 Nordic 沙发需求中的 `modern striped rug` 会选择现代条纹地毯，而不是固定取品类第一款。
- `matching` 场景增加确定性路由保护：模型首次错误选择 `sku_recall` 时，自动恢复为一次 `scenario_related_recall` 并保留全部搭配品类。
- 拉丁品类别名改为词边界匹配，修复 `Bafang` 被短词 `fan` 误识别为风扇；收据打印机和 3D 打印耗材采用子类型闭集过滤，宁可空召回也不返回家用打印机。
- 自动化测试：59/59 通过。
- 四条跨站点真实模型样本：4/4 通过质量门禁，0 warning、0 issue；修复后 DE 返回清洁套装和 77mm ND 滤镜两张卡，FR 只返回 1L 吸管水壶，NL 只返回 5mm 瑜伽垫与 5kg 哑铃。
- UK 场景路由专项样本：1/1 通过质量门禁，模型错误规划被纠正为 `scenario_related_recall`，最终准确返回棉麻窗帘和现代条纹地毯。

## 第十五轮百条召回相关性清洗

- 对 100 条回放中上一轮 41 个非空命中逐条人工审计，不再把“有商品”直接视为“召回正确”。
- 修复旧 `KEYWORD_RULES` 的拉丁裸子串匹配，例如 `inflatable` 中的 `tab` 不再误命中平板电脑。
- 为露营/移动空调、游戏椅、泳池机器人、背包肩带垫、无线投屏器、电视柜、背部喷雾、Giotto、Koriderm、麻花等专门需求增加闭集过滤；标准库没有对应商品时返回空，而不是退化到宽泛品类。
- 专门子类型 Query 在 Agent 层锁定原始用户需求，只允许执行一次原 Query 搜索；模型不能在空召回后自行放宽成办公椅、普通吸尘器等大类。
- 非 bundle 场景全部空召回时强制使用 Query/站点语言生成无结果回复，修复荷兰语 Query 最终出现中文道歉的问题。
- 白醋宽查询只保留醋类商品；`70mai` 作为品牌收窄到对应记录仪；商品标题保留 `Pro` 型号；`tv screen` 与 `tv scherm` 支持安全词边界识别。
- 增加实时事实边界：询问“今日降价、当前活动、最新款”等信息时，最终回复明确说明工具没有实时活动状态或上新时间，无法确认动态结论。
- 质量门禁同步检查动态促销/新旧程度免责声明，并补齐法语、荷兰语、德语和中文空召回模板识别。
- 最新 100 条工具 Query 高精度重放：29 条相关召回、71 条安全空召回；相比 41 条命中，主要减少的是已确认的跨品类和子类型误召回，不以降低空召回率为目标。
- 分站点相关命中：UK 7/25、DE 11/25、FR 5/25、NL 6/25。
- 自动化测试：65/65 通过。
- 真实模型定向验证：动态折扣、法语游戏椅空召回、荷兰语背部喷雾空召回、70mai 精确召回共 4/4 通过质量门禁，0 warning、0 issue。

## 第十六轮可重复百条批跑与语义门禁

- 新增正式批跑入口 `scripts/run_mock_query_batch.py`，支持固定随机种子、四站点均衡抽样、逐条落盘、递增退避、断点续跑、定点重跑和自动质量报告。
- `--resume` 只跳过已完成 sample；`--resume --rerun --sample-id ...` 可在原结果文件中定点重跑已完成但质量不合格的样本。
- 重跑结束后自动按 `sample_id` 压缩输出，只保留最新结果，避免追加日志中的历史失败污染通用质量检查。
- 使用真实 `queries_600.jsonl` dry-run 验证：固定种子 `20260817` 抽取 100 条，UK/DE/FR/NL 各 25 条。
- 四站点真实模型小批验证 4/4 完成；网关 503 由递增退避恢复，随后 `--resume` 验证为零模型调用且报告保持一致。
- 人工检查发现 `L'Oréal Elvive hair mask` 被返回普通洗发水，说明纯格式门禁仍不足；新增发膜和护发素闭集过滤后，该 Query 为 1 次空召回、0 张商卡、英语本地化无结果回复。
- 质量门禁新增专门子类型语义校验：根据返回 SKU 回查统一原始商品库，确认商品标题、规格或描述包含对应子类型。旧发膜错误轨迹被准确判失败，修复轨迹通过。
- 在原 4 条输出中通过 `--resume --rerun --sample-id anonymous-session` 只重跑问题样本；最终执行 4/4、质量 4/4、0 warning、0 issue。
- 自动化测试：73/73 通过。
- 使用文档：`docs/mock-query-batch-runner.md`。

## 第十七轮六百条全量兜底审计

- 使用当前工具层直接回放完整 `queries_600.jsonl`：600 条中 128 条非空、472 条空召回；初始发现 13 条“归一化未识别品类但关键词兜底返回商品”的高风险样本。
- 13 条问题主要包括：JBL Bar→蓝牙音箱、Galaxy Buds 3/4→手机、SmartTag2→手机、平板保护套→平板、床笠→四件套、`Mate-kaart`→Mate 手机、Apple Watch Ultra 3→普通 Apple Watch。
- 为 JBL Bar/回音壁、Galaxy Buds 明确型号、SmartTag、防丢器、平板保护套、Apple Watch Ultra、电视柜和床笠等配件或型号需求增加闭集过滤。
- 新增 LEGO 品牌归一化：一般 LEGO Query 只返回 LEGO 商品；不存在的 `LEGO Star Wars 75412` 返回空；`max 10€` 预算表达现在可以正确过滤超预算商品。
- 儿童益智玩具不再返回 RC 漂移车，改为只返回商品字段明确包含编程、STEM、益智或拼图的商品。
- 移除手机品类的裸 `mate` 关键词，仅保留 `Huawei Mate`、`Mate 60`、`Mate 70` 等安全表达，修复荷兰语 `Mate-kaart` 误召回。
- 修复后再次全量回放：118 条非空、482 条空召回；高风险兜底命中由 13 条降为 3 条。
- 剩余 3 条分别为一般 LEGO 推荐、LEGO 品牌介绍和女孩益智玩具，人工审计均确认召回相关。
- 四站点真实模型定向验证：FR `jbl bar`、DE Galaxy Buds 3/4、NL SmartTag2 均为 1 次空召回和本地语言回复；UK 女孩益智玩具为 1 次召回、2 张相关商卡。
- 定向样本 4/4 通过质量门禁，0 warning、0 issue。
- 自动化测试：74/74 通过。
- 全量复跑产物：`sft_data/mock_queries600_direct_replay_v2_20260817.json`。

## 第十八轮六百条同品类精度与规格门禁

- 对上一轮 118 个非空召回继续逐条审计，不只检查跨品类误召回，也检查同品类内的子类型、配件、品牌、用途和最低规格是否真正满足 Query。
- 品类归一化和旧关键词兜底统一改为“最长、最具体别名优先”；专门需求支持多个约束同时取交集，避免 `anchovy dried fish` 只按“鱼干”返回鳕鱼、`mobile airco raamafdichting` 只按“移动空调”返回挂机。
- 新增 `mAh`、`W`、`GB` 数值规格过滤：支持 `mindestens 20.000 mA Stunden`、`mindestens 65 W` 等多语言最低约束；无上下限词时按精确规格过滤。德语充电宝样本现在只返回 `BASEUS Star-Lord 20000mAh 65W`。
- 对洗衣凝珠、曲面显示器、吸拖一体机、空调扇、吊扇、手机壳/贴膜、3D 打印耗材、窗封套件、洗衣篮、毛发吸附球、12V 电视、3C 认证、巧克力饮料等专门需求增加闭集过滤；标准库无对应商品时安全空召回。
- 修复墙架拼写噪声：`wall slef without using drill` 能稳定归一化为置物架并返回唯一免打孔商品，不再因 Query 中出现 `tent` 而返回帐篷。
- 键盘鼠标本地化标题保留实际子类型，德语结果区分 `Tastatur`、`Maus` 和 `Tastatur-Maus-Set`，不再把鼠标显示为键盘。
- 对“中国访客熟悉的零食”仅保留标准库中的中国品牌商品；对“几百元手机”按人民币 999 元上限处理，避免返回旗舰机。
- 最终 600 条工具层静态回放：64 条高精度非空召回、536 条安全空召回；不以降低空召回率为目标。未明确归一化但非空的样本仍为 3 条，分别是一般 LEGO 推荐、LEGO 品牌介绍和女孩益智玩具，人工确认均相关。
- 质量门禁新增“最终引用商卡必须满足用户原始数值规格”检查，能够拦截 20,000mAh/65W Query 中引用 22.5W、33W 或 45W 商品的轨迹。
- 四站点真实模型定向验证：UK 免打孔墙架 1 张卡、DE 20,000mAh/65W 充电宝 1 张卡、FR 竖屏带音箱显示器安全空召回、NL 游泳防水包安全空召回；4/4 通过，0 warning、0 issue。
- 自动化测试：79/79 通过。
- 最终全量产物：`sft_data/mock_queries600_direct_replay_v6_20260817.json`；真实模型产物：`sft_data/mock_live_precision4_20260817.jsonl`；质量报告：`sft_data/mock_live_precision4_quality_20260817.json`。

## 第十九轮范围约束、可解释标题与最终商卡门禁

- 屏幕尺寸由单一精确值扩展为精确值、最小值和区间三种约束；`65-75 Zoll` 不再误当成精确 75 英寸，`minimum/minum 55 pouces` 会保留 55 英寸以上候选，`television smart tv 75` 能识别无显式单位的电视尺寸。
- 价格解析补齐德语 `ab 300€` 和荷兰语 `onder de 500 euro`；DE 65–75 英寸、€300–€600 电视只返回 65/75 英寸且价格在区间内的两款，NL PS5 电视只保留 €500 以下三款。
- QLED/Mini LED 与 Android/Google TV 采用多条件交集；法语 55 英寸以上电视样本最终只返回同时满足 Mini LED、Google TV 和高刷新率的 TCL C735。
- iPhone 兼容手表收窄到工具字段明确说明苹果手机生态的 Apple Watch；露营便携风扇、户外空调等库内无对应子类型的需求安全空召回；落地扇和塔扇分别保留对应形态。
- 吸拖一体机器人过滤排除无拖地能力的 Roomba，且本地化标题明确显示 `aspirateur-laveur`，让模型仅从真实商卡字段即可判断匹配原因。
- 本地化标题补充与检索直接相关的子类型描述：白醋、黑酱油、甜酱油、低卡零食、牛肉干、速冻早餐、免打孔置物架和长保质期主食；同时限制描述词作用域，避免“弧形瓶”把香水错误显示成“弧形香水”。
- 质量门禁新增最终引用商品的价格和屏幕尺寸范围校验；即使模型自行放宽检索词，只要最终商卡越过用户原始范围，轨迹就会失败。
- 最新 600 条静态回放：61 条高精度非空召回、539 条安全空召回；未归一化非空仍为 3 条且均经人工确认相关。
- 四站点真实模型范围专项验证 4/4 通过，0 warning、0 issue：DE 65–75 英寸价格区间、FR 55 英寸以上 Mini LED/Google TV、NL €500 以下 PS5 电视、UK 免打孔置物架。
- 自动化测试：84/84 通过。
- 最新全量产物：`sft_data/mock_queries600_direct_replay_v8_20260817.json`；模型产物：`sft_data/mock_live_range4_20260817.jsonl`；质量报告：`sft_data/mock_live_range4_quality_20260817.json`。

## 第二十轮固定 100 条真实 Query 闭环

- 使用种子 `20260817` 从 600 条真实 Query 固定抽取四站点各 25 条，完整模型轨迹最终 100/100 执行成功。
- runner 默认启用 `--scenario auto`，两个带 `bundle` / `multi_category_bundle` 标签的样本自动进入 `bundle_purchase`。
- 修复 bundle 配件意图丢失、编号清单拆分、品牌/专门子类型宽泛替代、多语言误判、部分缺货不告知和异常长空搜索。
- 完整轨迹质量门禁 100/100 通过，0 warning、0 issue；商卡重复 0，最大 `sku_recall` 5 次，平均 1.8 次。
- 工具直放 21 条非空、79 条安全空；独立语义审计 15 pass、6 warning、0 fail，warning 仅保留契约无法确认的动态、主观或复杂技术属性。
- 自动化测试 95/95 通过。
- 详细报告：`sft_data/mock_queries100_loop_report_v11_20260817.md`。

## 第二十一轮 600 条全量语义复审

- 生成最新全量工具回放 `sft_data/mock_queries600_direct_replay_v11_20260817.json`：59 条高精度非空、541 条安全空召回；DE/FR/NL/UK 非空分别为 18/14/11/16。
- 单次工具直放不再把 TV + 支架 + 投屏器 bundle 错当成纯电视需求；正式 runner 仍通过 `bundle_purchase` 拆分并分别报告缺货。
- 本地化标题补齐 Smart/Google TV、120/144Hz、G-Sync、中国彩妆、中国零食品牌和 TP07 塔式风扇等真实可证实信息。
- 独立 LLM judge 最终结果为 42 pass、17 warning、0 fail；剩余 warning 仅涉及动态、主观或契约不可见属性，不通过伪造字段消除。
- 中国访客零食和塔式风扇两条真实模型定向复验 2/2 通过质量门禁，0 warning、0 issue。
- 语义审计器补齐 `socket.timeout` 重试并继续支持 checkpoint / resume。
- 自动化测试：96/96 通过。
- 详细报告：`sft_data/mock_queries600_loop_report_v11_20260817.md`。

## 第二十二轮完整最终回复独立语义审计

- 新增 `scripts/audit_mock_trajectory_semantics.py`，独立检查最终回复的商品相关性、硬约束、事实依据、语言、动态免责声明和 bundle 缺项表达。
- 审计器支持 JSONL、checkpoint、`--resume`、模型异常重试和 `socket.timeout` 重试；合理安全空召回不会被误判为 fail。
- 对固定 100 条完整轨迹进行独立语义审计，最终结果为 80 pass、20 warning、0 fail；自动质量门禁继续保持 100/100。
- 根据审计修复德语 `heute reduziert`、`neusten` 动态表达遗漏，以及 UK 歧义 Query 中默认 `¥` 币种错误。
- 三条定点重跑后质量门禁 100/100；独立重审确认原“缺免责声明/币种错误”问题已消失，warning 仅保留动态数据不可用和 Query 歧义本身。
- 自动化测试：100/100 通过。
- 使用文档：`docs/mock-trajectory-semantic-audit.md`；报告：`sft_data/mock_queries100_trajectory_semantic_report_v2_20260817.md`。
