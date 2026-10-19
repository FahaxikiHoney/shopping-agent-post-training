"""
SFT 训练数据生成脚本 v1 - 本地生成 10 条高质量样本
不依赖任何 API，所有轨迹由强模型预先写好作为模板。

每条 trajectory 模拟京东 AI 购物 Agent 的真实执行轨迹：
  user_query → thinking → tool_call(s) → final_response

输出：sft_data/trajectories.jsonl
"""
import json
import os
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "trajectories.jsonl"

# ─────────────────────────────────────────────────────────────────────
# 10 条高质量轨迹，覆盖 6 类核心场景
# ─────────────────────────────────────────────────────────────────────
TRAJECTORIES = [
    # ─── 1. 电商搜索 - 老人按摩仪（带预算+人群约束）─────────────────────
    {
        "trajectory_id": "sft_ecom_001",
        "category": "电商搜索",
        "user_query": "帮我找一款适合60岁老人的颈部按摩仪，预算500元以内，操作要简单",
        "thinking": "用户三个核心约束：颈部按摩仪品类、500元预算、老人操作友好。调用 product_search 传完整关键词，筛选3-4款带一键操作的低强度款，按操作易用性排序推荐。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "product_search",
                "tool_input": {"query": "颈部按摩仪 老人 一键操作 简单", "max_price": 500, "is_jd_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_11223344", "title": "小米米家颈椎按摩仪 3档强度 一键启动 热敷功能", "price": 349.0, "is_jd_self": True, "rating": 4.8, "key_specs": "3档力度/15分钟自动断电/热敷功能", "sales": "月销3.2万件"},
                        {"product_id": "jd_55667788", "title": "飞利浦肩颈按摩仪 PR3092 老人款 双键操作", "price": 469.0, "is_jd_self": True, "rating": 4.7, "key_specs": "5档强度/40-50℃热敷/锂电池4小时续航", "sales": "月销1.8万件"},
                        {"product_id": "jd_99001122", "title": "倍轻松颈椎按摩器 智能感应 老年人专用款", "price": 299.0, "is_jd_self": True, "rating": 4.6, "key_specs": "贴合人体颈部/12分钟定时/极简一键设计", "sales": "月销1.5万件"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "为长辈选购按摩仪重点是操作简单、力度温和。我从京东自营筛选了3款，都在预算内：\n\n**1. 小米米家颈椎按摩仪（¥349）** ⭐ 综合推荐\n一键启动设计，按一下就用，3档力度老人完全够用。带热敷功能对颈椎酸痛尤其有效，月销3.2万件，口碑稳定。\n\n**2. 飞利浦肩颈按摩仪 PR3092（¥469）**\n双键控制，5档力度可选，预算充足可以考虑。锂电池续航4小时，外出也能用。品牌信赖度高，适合送礼。\n\n**3. 倍轻松颈椎按摩器（¥299）**\n最便宜，极简单键设计，专门面向老年用户。12分钟自动停机保证安全。如果只想试试用，可以选这款。\n\n**建议**：日常使用首选小米款，预算从容且更划算；送礼选飞利浦更体面。",
                "product_cards": [
                    {"card_id": "jd_11223344", "display_price": 349.0, "reason": "一键启动+3档力度+热敷功能，老人操作零门槛，京东自营月销3.2万"},
                    {"card_id": "jd_55667788", "display_price": 469.0, "reason": "飞利浦品牌5档力度，4小时长续航，送礼首选"},
                    {"card_id": "jd_99001122", "display_price": 299.0, "reason": "极简单键设计专为老年用户，12分钟定时安全无忧"}
                ]
            }
        ],
        "final_response": "为长辈选购按摩仪重点是操作简单、力度温和。我从京东自营筛选了3款，都在预算内：\n\n**1. 小米米家颈椎按摩仪（¥349）** ⭐ 综合推荐\n一键启动设计，按一下就用，3档力度老人完全够用。带热敷功能对颈椎酸痛尤其有效，月销3.2万件，口碑稳定。\n\n**2. 飞利浦肩颈按摩仪 PR3092（¥469）**\n双键控制，5档力度可选，预算充足可以考虑。锂电池续航4小时，外出也能用。品牌信赖度高，适合送礼。\n\n**3. 倍轻松颈椎按摩器（¥299）**\n最便宜，极简单键设计，专门面向老年用户。12分钟自动停机保证安全。如果只想试试用，可以选这款。\n\n**建议**：日常使用首选小米款，预算从容且更划算；送礼选飞利浦更体面。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ─── 2. 电商搜索 - 空气净化器（多约束+规格匹配）─────────────────────
    {
        "trajectory_id": "sft_ecom_002",
        "category": "电商搜索",
        "user_query": "推荐一款2000元以内的空气净化器，适合60平米客厅，要能除甲醛",
        "thinking": "三个约束：2000元预算、60平米适用面积、除甲醛功能。CADR值需要至少400m³/h覆盖60平米。筛选带HEPA+活性炭复合滤网的型号，CADR对齐房间面积。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "product_search",
                "tool_input": {"query": "空气净化器 除甲醛 60平米 CADR大", "max_price": 2000, "category": "净化器"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_42118801", "title": "小米米家空气净化器4 Pro 除甲醛CADR 500m³/h", "price": 1599.0, "is_jd_self": True, "rating": 4.8, "key_specs": "CADR 500m³/h(颗粒物)/300m³/h(甲醛)/适用60-80㎡/H13级HEPA", "sales": "月销4.1万件"},
                        {"product_id": "jd_42118802", "title": "352 X83C 大客厅空气净化器 除甲醛CADR 750m³/h", "price": 1999.0, "is_jd_self": True, "rating": 4.9, "key_specs": "CADR 750/400m³/h/适用90㎡/双侧进风/CCM顶级F4", "sales": "月销1.2万件"},
                        {"product_id": "jd_42118803", "title": "IAM KJ900F 全能除醛空气净化器 母婴款", "price": 1799.0, "is_jd_self": True, "rating": 4.7, "key_specs": "CADR 900/450m³/h/适用100㎡/醛霾双滤芯", "sales": "月销8500件"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "60平米客厅除甲醛，关键看 **甲醛 CADR 值**（建议至少 300m³/h）和滤网等级。3款都达标：\n\n**1. 小米米家4 Pro（¥1599）** ⭐ 性价比首选\n甲醛 CADR 300m³/h，颗粒物 500m³/h，标称适用 60-80㎡正好覆盖你的客厅。H13 级 HEPA 滤网，米家 App 联动，月销4万+，是这个价位最稳的选择。\n\n**2. 352 X83C（¥1999）** ⭐ 性能强者\n甲醛 CADR 400m³/h，颗粒物 750m³/h，标称90㎡，对你 60㎡ 客厅是降维打击。双侧进风净化更快，CCM 等级 F4 顶配，滤芯寿命更长。预算到顶推荐这款。\n\n**3. IAM KJ900F（¥1799）**\n甲醛 CADR 450m³/h 最强，醛霾双独立滤芯设计，母婴家庭友好。销量低于前两款，可能是品牌认知度问题。\n\n**建议**：日常用 352 X83C 最稳，预算紧或要联动米家选小米 4 Pro。",
                "product_cards": [
                    {"card_id": "jd_42118801", "display_price": 1599.0, "reason": "甲醛CADR 300+颗粒物500，60-80㎡覆盖你的客厅，米家联动月销4万+"},
                    {"card_id": "jd_42118802", "display_price": 1999.0, "reason": "甲醛CADR 400+颗粒物750，性能顶配CCM F4级，预算到顶最强选择"},
                    {"card_id": "jd_42118803", "display_price": 1799.0, "reason": "甲醛CADR 450最强，醛霾双滤芯独立设计，母婴家庭友好"}
                ]
            }
        ],
        "final_response": "60平米客厅除甲醛，关键看 **甲醛 CADR 值**（建议至少 300m³/h）和滤网等级。3款都达标：\n\n**1. 小米米家4 Pro（¥1599）** ⭐ 性价比首选\n甲醛 CADR 300m³/h，颗粒物 500m³/h，标称适用 60-80㎡正好覆盖你的客厅。H13 级 HEPA 滤网，米家 App 联动，月销4万+，是这个价位最稳的选择。\n\n**2. 352 X83C（¥1999）** ⭐ 性能强者\n甲醛 CADR 400m³/h，颗粒物 750m³/h，标称90㎡，对你 60㎡ 客厅是降维打击。双侧进风净化更快，CCM 等级 F4 顶配，滤芯寿命更长。预算到顶推荐这款。\n\n**3. IAM KJ900F（¥1799）**\n甲醛 CADR 450m³/h 最强，醛霾双独立滤芯设计，母婴家庭友好。销量低于前两款，可能是品牌认知度问题。\n\n**建议**：日常用 352 X83C 最稳，预算紧或要联动米家选小米 4 Pro。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ─── 3. 电商搜索 - 跑步鞋（专业场景）────────────────────────────────
    {
        "trajectory_id": "sft_ecom_003",
        "category": "电商搜索",
        "user_query": "找一双跑步鞋，男款42码，预算300元，要透气防滑专业跑步",
        "thinking": "运动鞋品类细分到跑步鞋（区别于休闲/篮球），需要男42码、300内预算、透气防滑专业跑步场景。query 必须含'跑步鞋+男+透气'，排除休闲鞋。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "product_search",
                "tool_input": {"query": "男士跑步鞋 透气防滑 专业", "max_price": 300, "size": "42"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_55001001", "title": "李宁䨻烁2 男款跑步鞋 透气网面 42码", "price": 269.0, "is_jd_self": True, "rating": 4.7, "key_specs": "䨻轻弹中底/全网面鞋面/橡胶大底", "sales": "月销2.8万双"},
                        {"product_id": "jd_55001002", "title": "安踏氢跑5代 男款减震跑步鞋 透气专业训练", "price": 249.0, "is_jd_self": True, "rating": 4.8, "key_specs": "氢科技中底缓震/4D工程网/异形橡胶颗粒防滑", "sales": "月销5.1万双"},
                        {"product_id": "jd_55001003", "title": "特步竞速160X 5代 男款竞速跑鞋 碳板减震", "price": 299.0, "is_jd_self": True, "rating": 4.6, "key_specs": "PEBA发泡中底/前掌碳板/单只218g超轻", "sales": "月销9800双"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "预算300内的国产跑鞋这两年进步很大，3款都是42码可选的主力专业款：\n\n**1. 安踏氢跑5代（¥249）** ⭐ 综合推荐\n氢科技中底缓震到位，4D 工程网鞋面透气性极好，异形橡胶颗粒大底防滑稳。月销 5.1 万双在这个价位是断档第一，日常 5-10km 跑量很合适。\n\n**2. 李宁䨻烁2（¥269）**\n李宁的招牌䨻中底，弹性比氢科技更突出一些，适合追求脚感的跑者。全网面鞋面夏天穿透气最爽，相对窄脚型友好。\n\n**3. 特步竞速160X 5代（¥299）**\nPEBA 发泡+前掌碳板的真竞速鞋，单只 218g 是这3款里最轻的。如果你跑半马以上或追求配速，闭眼选这双；纯日常慢跑反而显得偏硬。\n\n**建议**：日常通勤+轻量跑选氢跑5代，追配速选 160X 5代。",
                "product_cards": [
                    {"card_id": "jd_55001002", "display_price": 249.0, "reason": "氢科技中底缓震+4D工程网透气+异形颗粒防滑，月销5.1万双断档第一"},
                    {"card_id": "jd_55001001", "display_price": 269.0, "reason": "李宁䨻中底弹性突出，全网面夏季透气极佳，适合追求脚感"},
                    {"card_id": "jd_55001003", "display_price": 299.0, "reason": "PEBA+前掌碳板真竞速款，单只218g超轻，半马以上配速首选"}
                ]
            }
        ],
        "final_response": "预算300内的国产跑鞋这两年进步很大，3款都是42码可选的主力专业款：\n\n**1. 安踏氢跑5代（¥249）** ⭐ 综合推荐\n氢科技中底缓震到位，4D 工程网鞋面透气性极好，异形橡胶颗粒大底防滑稳。月销 5.1 万双在这个价位是断档第一，日常 5-10km 跑量很合适。\n\n**2. 李宁䨻烁2（¥269）**\n李宁的招牌䨻中底，弹性比氢科技更突出一些，适合追求脚感的跑者。全网面鞋面夏天穿透气最爽，相对窄脚型友好。\n\n**3. 特步竞速160X 5代（¥299）**\nPEBA 发泡+前掌碳板的真竞速鞋，单只 218g 是这3款里最轻的。如果你跑半马以上或追求配速，闭眼选这双；纯日常慢跑反而显得偏硬。\n\n**建议**：日常通勤+轻量跑选氢跑5代，追配速选 160X 5代。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ─── 4. 外卖搜索 ─────────────────────────────────────────────────
    {
        "trajectory_id": "sft_waimai_001",
        "category": "外卖搜索",
        "user_query": "帮我在附近找家好吃的黄焖鸡米饭，配送快，评分高",
        "thinking": "外卖场景三个约束：黄焖鸡米饭品类、配送时效、评分高。调用 waimai_search，按评分+配送时间复合排序，给出3家附近选择。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "waimai_search",
                "tool_input": {"query": "黄焖鸡米饭", "sort_by": "rating_desc", "max_delivery_minutes": 40},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "wm_88301201", "title": "杨明宇黄焖鸡米饭（中关村店）", "price": 28.0, "is_jd_self": False, "rating": 4.9, "key_specs": "距离1.2km/配送25分钟/月售6800单/招牌香菇鸡腿肉饭28元", "sales": "月销6800单"},
                        {"product_id": "wm_88301202", "title": "鼎香源黄焖鸡米饭（学院路总店）", "price": 25.0, "is_jd_self": False, "rating": 4.8, "key_specs": "距离0.8km/配送20分钟/月售1.2万单/经典招牌25元含饭", "sales": "月销1.2万单"},
                        {"product_id": "wm_88301203", "title": "老北京黄焖鸡（西二旗店）", "price": 32.0, "is_jd_self": False, "rating": 4.7, "key_specs": "距离1.8km/配送35分钟/微辣可调/腿肉量足32元", "sales": "月销4200单"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "附近评分4.7以上的黄焖鸡米饭，3家可选：\n\n**1. 鼎香源黄焖鸡米饭（¥25）** ⭐ 综合最优\n0.8km 最近，配送 20 分钟最快，月售 1.2 万单全区第一，4.8 高分。经典招牌饭 25 元最便宜，闭眼点不踩雷。\n\n**2. 杨明宇黄焖鸡米饭（¥28）**\n4.9 分最高，距离 1.2km 配送 25 分钟。招牌用的是带骨香菇鸡腿肉，料更足一些，比鼎香源贵 3 元。讲究口感选这家。\n\n**3. 老北京黄焖鸡（¥32）**\n稍远 1.8km，配送 35 分钟。优点是辣度可调（微辣/中辣），鸡腿肉量最足。如果喜欢吃辣选这家。\n\n**建议**：快+便宜选鼎香源，求口感选杨明宇。",
                "product_cards": [
                    {"card_id": "wm_88301202", "display_price": 25.0, "reason": "0.8km最近+20分钟最快+月销1.2万单第一，25元价格最优"},
                    {"card_id": "wm_88301201", "display_price": 28.0, "reason": "4.9分全场最高，带骨香菇鸡腿肉料足，配送25分钟"},
                    {"card_id": "wm_88301203", "display_price": 32.0, "reason": "辣度可调微辣中辣均可，鸡腿肉量最足，适合吃辣党"}
                ]
            }
        ],
        "final_response": "附近评分4.7以上的黄焖鸡米饭，3家可选：\n\n**1. 鼎香源黄焖鸡米饭（¥25）** ⭐ 综合最优\n0.8km 最近，配送 20 分钟最快，月售 1.2 万单全区第一，4.8 高分。经典招牌饭 25 元最便宜，闭眼点不踩雷。\n\n**2. 杨明宇黄焖鸡米饭（¥28）**\n4.9 分最高，距离 1.2km 配送 25 分钟。招牌用的是带骨香菇鸡腿肉，料更足一些，比鼎香源贵 3 元。讲究口感选这家。\n\n**3. 老北京黄焖鸡（¥32）**\n稍远 1.8km，配送 35 分钟。优点是辣度可调（微辣/中辣），鸡腿肉量最足。如果喜欢吃辣选这家。\n\n**建议**：快+便宜选鼎香源，求口感选杨明宇。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ─── 5. 一句话下单（关联前文推荐）─────────────────────────────────
    {
        "trajectory_id": "sft_order_001",
        "category": "一句话下单",
        "user_query": "帮我下单刚才推荐的小米颈部按摩仪，349元那款，发默认地址",
        "thinking": "明确的下单指令，目标商品已锁定（小米颈部按摩仪/349元/默认地址）。直接调用 order_create，无需重新搜索。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "order_create",
                "tool_input": {"product_id": "jd_11223344", "quantity": 1, "address": "DEFAULT", "payment_method": "default"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_11223344", "title": "小米米家颈椎按摩仪 3档强度 一键启动 热敷功能", "price": 349.0, "is_jd_self": True, "rating": 4.8, "key_specs": "订单号 [ORDER_ID]/预计明天 18:00 前送达", "sales": "京东自营"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "✅ 下单成功！\n\n**订单详情**\n- 商品：小米米家颈椎按摩仪（一键启动+热敷）\n- 单价：¥349.00 × 1\n- 收货地址：默认地址（CITY_DISTRICT...）\n- 支付方式：默认支付（已扣款）\n- 订单号：[ORDER_ID]\n- 预计送达：明天 18:00 前\n\n京东自营物流，可在「我的订单」实时跟踪。如需修改地址或取消订单，请在 30 分钟内操作。",
                "product_cards": [
                    {"card_id": "jd_11223344", "display_price": 349.0, "reason": "已下单成功，京东自营次日达，订单号 [ORDER_ID]"}
                ]
            }
        ],
        "final_response": "✅ 下单成功！\n\n**订单详情**\n- 商品：小米米家颈椎按摩仪（一键启动+热敷）\n- 单价：¥349.00 × 1\n- 收货地址：默认地址（CITY_DISTRICT...）\n- 支付方式：默认支付（已扣款）\n- 订单号：[ORDER_ID]\n- 预计送达：明天 18:00 前\n\n京东自营物流，可在「我的订单」实时跟踪。如需修改地址或取消订单，请在 30 分钟内操作。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ─── 6. 历史订单查询 ─────────────────────────────────────────────
    {
        "trajectory_id": "sft_history_001",
        "category": "历史订单查询",
        "user_query": "我之前买的净化器滤网该换了，帮我查一下当时买的是哪款",
        "thinking": "用户需要查历史订单中的空气净化器，以便匹配对应滤网。调用 order_query 按品类筛选历史订单，返回型号+型号兼容的滤网信息。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "order_query",
                "tool_input": {"category_keyword": "空气净化器", "time_range": "all", "status": "completed"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_42118801", "title": "小米米家空气净化器4 Pro 除甲醛CADR 500m³/h", "price": 1599.0, "is_jd_self": True, "rating": 4.8, "key_specs": "购买于2025-09-12/订单[ORDER_ID]/已使用约9个月", "sales": "原装滤芯型号 M16-FLP-T"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "product_search",
                "tool_input": {"query": "米家空气净化器4 Pro 滤芯 M16-FLP-T 原装", "is_jd_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_42118899", "title": "小米米家空气净化器4 Pro 原装滤芯 除甲醛增强版 M16-FLP-T", "price": 249.0, "is_jd_self": True, "rating": 4.9, "key_specs": "原装H13级HEPA+椰壳活性炭/适配4 Pro/CCM甲醛F4级", "sales": "月销1.8万件"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "final_response",
                "content": "查到了！\n\n**你的购买记录**\n- 商品：小米米家空气净化器4 Pro\n- 购买时间：2025-09-12（已使用约 9 个月）\n- 订单号：[ORDER_ID]\n- 原装滤芯型号：**M16-FLP-T**\n\n按官方建议，4 Pro 滤芯每 6-12 个月更换一次，你的使用时长正好到了，确实该换了。\n\n**推荐配件**\n小米官方原装滤芯（除甲醛增强版 M16-FLP-T），¥249，京东自营月销 1.8 万件，H13 级 HEPA + 椰壳活性炭，CCM 甲醛 F4 级，比普通版除醛能力更强。建议直接买原装，第三方兼容款 CADR 衰减明显。",
                "product_cards": [
                    {"card_id": "jd_42118899", "display_price": 249.0, "reason": "原装M16-FLP-T滤芯，H13 HEPA+椰壳活性炭，CCM甲醛F4级，月销1.8万"}
                ]
            }
        ],
        "final_response": "查到了！\n\n**你的购买记录**\n- 商品：小米米家空气净化器4 Pro\n- 购买时间：2025-09-12（已使用约 9 个月）\n- 订单号：[ORDER_ID]\n- 原装滤芯型号：**M16-FLP-T**\n\n按官方建议，4 Pro 滤芯每 6-12 个月更换一次，你的使用时长正好到了，确实该换了。\n\n**推荐配件**\n小米官方原装滤芯（除甲醛增强版 M16-FLP-T），¥249，京东自营月销 1.8 万件，H13 级 HEPA + 椰壳活性炭，CCM 甲醛 F4 级，比普通版除醛能力更强。建议直接买原装，第三方兼容款 CADR 衰减明显。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ─── 7. 找优惠（带计算）───────────────────────────────────────────
    {
        "trajectory_id": "sft_discount_001",
        "category": "找优惠",
        "user_query": "618期间洗衣机有什么满减优惠，帮我算算最划算的方案",
        "thinking": "618 大促场景：先搜洗衣机+查满减规则，再用 python_calculator 算具体方案。推荐时给出对比每种叠加组合后的实付价。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "product_search",
                "tool_input": {"query": "洗衣机 618 满减 大促", "category": "洗衣机", "promotion": "618"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_77001001", "title": "海尔EG100MATE3S 10kg滚筒洗衣机 直驱变频", "price": 2999.0, "is_jd_self": True, "rating": 4.8, "key_specs": "原价3499/618立减500/满3000减200/PLUS再减100", "sales": "月销1.5万件"},
                        {"product_id": "jd_77001002", "title": "小天鹅TG100V88WMUIADY5 10kg水魔方洗烘一体机", "price": 4299.0, "is_jd_self": True, "rating": 4.9, "key_specs": "原价4999/618立减700/满4000减300/赠延保2年", "sales": "月销9800件"},
                        {"product_id": "jd_77001003", "title": "美的MD100VT717WDY5 10kg洗烘一体 智能投放", "price": 3699.0, "is_jd_self": True, "rating": 4.7, "key_specs": "原价4299/618立减500/满3500减200/可领100元品类券", "sales": "月销1.1万件"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "python_calculator",
                "tool_input": {"code": "haier = 2999 - 200 - 100\nlittleswan = 4299 - 300\nmidea = 3699 - 200 - 100\nprint(f'海尔实付: {haier}')\nprint(f'小天鹅实付: {littleswan} (含赠延保2年≈300元)')\nprint(f'美的实付: {midea}')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_001", "title": "计算结果", "price": 0.0, "is_jd_self": False, "rating": 5.0, "key_specs": "海尔实付:2699 / 小天鹅实付:3999(含延保) / 美的实付:3399", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "final_response",
                "content": "618 洗衣机满减规则一团乱，我帮你算清楚了，**所有叠加后的最终实付价**：\n\n| 商品 | 标价 | 满减叠加 | **实付** |\n|---|---|---|---|\n| 海尔 EG100MATE3S（直驱10kg） | ¥2999 | -200(满3000减200) -100(PLUS) | **¥2699** ⭐最便宜 |\n| 美的 MD100VT717（洗烘一体10kg） | ¥3699 | -200(满3500减200) -100(品类券) | **¥3399** |\n| 小天鹅 TG100V88（水魔方洗烘） | ¥4299 | -300(满4000减300) +赠2年延保 | **¥3999**（≈¥3700价值）|\n\n**建议**\n- **预算紧、只需洗** → 海尔 ¥2699，直驱变频静音省电，月销 1.5 万件最稳。\n- **要洗烘一体** → 美的 ¥3399，智能投放方便，洗烘一体里最便宜。\n- **预算充足** → 小天鹅 ¥3999 含延保，水魔方专利洗护+免熨平烫衣模式，体验最好。\n\n**注意**：PLUS 券和品类券都要先在商品页手动领取后再下单才能叠加。",
                "product_cards": [
                    {"card_id": "jd_77001001", "display_price": 2999.0, "reason": "618满减后实付2699元最便宜，直驱变频10kg滚筒月销1.5万"},
                    {"card_id": "jd_77001003", "display_price": 3699.0, "reason": "洗烘一体实付3399元，智能投放+品类券叠加最划算"},
                    {"card_id": "jd_77001002", "display_price": 4299.0, "reason": "水魔方专利实付3999含2年延保，体验最佳预算选择"}
                ]
            }
        ],
        "final_response": "618 洗衣机满减规则一团乱，我帮你算清楚了，**所有叠加后的最终实付价**：\n\n| 商品 | 标价 | 满减叠加 | **实付** |\n|---|---|---|---|\n| 海尔 EG100MATE3S（直驱10kg） | ¥2999 | -200(满3000减200) -100(PLUS) | **¥2699** ⭐最便宜 |\n| 美的 MD100VT717（洗烘一体10kg） | ¥3699 | -200(满3500减200) -100(品类券) | **¥3399** |\n| 小天鹅 TG100V88（水魔方洗烘） | ¥4299 | -300(满4000减300) +赠2年延保 | **¥3999**（≈¥3700价值）|\n\n**建议**\n- **预算紧、只需洗** → 海尔 ¥2699，直驱变频静音省电，月销 1.5 万件最稳。\n- **要洗烘一体** → 美的 ¥3399，智能投放方便，洗烘一体里最便宜。\n- **预算充足** → 小天鹅 ¥3999 含延保，水魔方专利洗护+免熨平烫衣模式，体验最好。\n\n**注意**：PLUS 券和品类券都要先在商品页手动领取后再下单才能叠加。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ─── 8. 咨询搜索（开放性建议）─────────────────────────────────────
    {
        "trajectory_id": "sft_consult_001",
        "category": "咨询搜索",
        "user_query": "我妈有高血压，送什么礼物比较合适，预算500以内",
        "thinking": "咨询类需求：高血压人群+送礼+500预算。重点是健康监测/缓解类商品，不能是禁忌品（高盐高糖食品）。推荐方向：血压计、足浴盆、按摩仪。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "product_search",
                "tool_input": {"query": "高血压老人 健康礼物 血压计 足浴盆", "max_price": 500, "is_jd_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_99880011", "title": "欧姆龙U10L 上臂式电子血压计 智能语音播报", "price": 269.0, "is_jd_self": True, "rating": 4.9, "key_specs": "上臂式更精准/语音播报/双人记忆模式90组/医用级认证", "sales": "月销4.2万件"},
                        {"product_id": "jd_99880012", "title": "泰昌足浴盆 全自动按摩加热 老人专用款", "price": 399.0, "is_jd_self": True, "rating": 4.7, "key_specs": "深桶过小腿/恒温45℃/自动按摩滚轮/防干烧安全", "sales": "月销1.6万件"},
                        {"product_id": "jd_99880013", "title": "鱼跃YE680A 上臂式血压计 大屏家用 老人款", "price": 199.0, "is_jd_self": True, "rating": 4.8, "key_specs": "国产医用级/超大屏数字/双人120组记忆/3.5寸液晶", "sales": "月销2.3万件"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "高血压老人送礼，**实用比颜值重要**。重点推荐这个方向（避开高盐零食、烟酒补品）：\n\n**1. 欧姆龙 U10L 血压计（¥269）** ⭐ 首选送礼\n上臂式比腕式更准（医生通用标准），语音播报省得老人自己看屏幕。双人记忆 90 组阿姨叔叔都能用。月销 4.2 万件，欧姆龙是血压计行业第一品牌，送出去体面又实用。\n\n**2. 鱼跃 YE680A 血压计（¥199）**\n如果只买血压计，国产鱼跃也是医用级，超大屏对老花眼更友好。比欧姆龙便宜 70 元，性能差距不大。\n\n**3. 泰昌足浴盆（¥399）** 搭配推荐\n高血压人群泡脚能促进末梢循环、辅助降压（要避开过烫水温），恒温 45℃ 正好。如果想送一个「组合礼物」，建议预算分配：欧姆龙血压计 ¥269 + 一个 ¥200 内的足浴盆，总 ¥469 在你预算内。\n\n**重要提醒**\n- 不要送：保健品（很多虚假宣传）、酒（升压）、含盐零食。\n- 体面 + 实用首选血压计，长辈每天都会用到。",
                "product_cards": [
                    {"card_id": "jd_99880011", "display_price": 269.0, "reason": "欧姆龙行业第一品牌，上臂式医用级精准，语音播报+90组记忆"},
                    {"card_id": "jd_99880013", "display_price": 199.0, "reason": "鱼跃国产医用级超大屏，老花眼友好，性价比首选"},
                    {"card_id": "jd_99880012", "display_price": 399.0, "reason": "深桶恒温45℃+自动按摩，促进末梢循环辅助降压"}
                ]
            }
        ],
        "final_response": "高血压老人送礼，**实用比颜值重要**。重点推荐这个方向（避开高盐零食、烟酒补品）：\n\n**1. 欧姆龙 U10L 血压计（¥269）** ⭐ 首选送礼\n上臂式比腕式更准（医生通用标准），语音播报省得老人自己看屏幕。双人记忆 90 组阿姨叔叔都能用。月销 4.2 万件，欧姆龙是血压计行业第一品牌，送出去体面又实用。\n\n**2. 鱼跃 YE680A 血压计（¥199）**\n如果只买血压计，国产鱼跃也是医用级，超大屏对老花眼更友好。比欧姆龙便宜 70 元，性能差距不大。\n\n**3. 泰昌足浴盆（¥399）** 搭配推荐\n高血压人群泡脚能促进末梢循环、辅助降压（要避开过烫水温），恒温 45℃ 正好。如果想送一个「组合礼物」，建议预算分配：欧姆龙血压计 ¥269 + 一个 ¥200 内的足浴盆，总 ¥469 在你预算内。\n\n**重要提醒**\n- 不要送：保健品（很多虚假宣传）、酒（升压）、含盐零食。\n- 体面 + 实用首选血压计，长辈每天都会用到。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ─── 9. 机票酒店 ─────────────────────────────────────────────────
    {
        "trajectory_id": "sft_travel_001",
        "category": "机票酒店",
        "user_query": "帮我查明天北京到上海的高铁，下午出发，最快几班",
        "thinking": "明确出行需求：北京→上海+明天+下午+高铁+最快。调用 flight_search 工具（含火车票），筛选 12-18 点出发，按运行时长升序。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "flight_search",
                "tool_input": {"from": "北京", "to": "上海", "date": "2026-06-23", "transport_type": "train", "depart_time_range": "12:00-18:00", "sort_by": "duration_asc"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "tr_G1_2026062314", "title": "G1次 复兴号 北京南→上海虹桥", "price": 933.0, "is_jd_self": False, "rating": 5.0, "key_specs": "14:00开/18:28到/历时4h28m/全程不停靠/商务座5060/二等933", "sales": "实时余票:商务座8/一等52/二等大量"},
                        {"product_id": "tr_G3_2026062315", "title": "G3次 复兴号智能动车 北京南→上海虹桥", "price": 933.0, "is_jd_self": False, "rating": 5.0, "key_specs": "15:00开/19:28到/历时4h28m/直达/CR400AF-B型车", "sales": "实时余票:商务座3/一等21/二等大量"},
                        {"product_id": "tr_G5_2026062313", "title": "G5次 复兴号 北京南→上海虹桥", "price": 662.5, "is_jd_self": False, "rating": 4.9, "key_specs": "13:00开/18:09到/历时5h09m/中途停南京1站/二等662.5", "sales": "实时余票:商务座15/一等88/二等大量"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "明天（6/23）下午北京→上海高铁，按最快排序：\n\n| 车次 | 出发 | 到达 | 用时 | 二等座 | 余票 |\n|---|---|---|---|---|---|\n| **G1** ⭐ | 北京南 14:00 | 上海虹桥 18:28 | **4h28m** | ¥933 | 充足 |\n| **G3** | 北京南 15:00 | 上海虹桥 19:28 | **4h28m** | ¥933 | 充足 |\n| G5 | 北京南 13:00 | 上海虹桥 18:09 | 5h09m | ¥662.5 | 充足 |\n\n**推荐**\n- **追最快** → **G1 次**，14:00 开 18:28 到，全程不停靠 4h28m 是京沪最快档；商务座余 8 张，要的话尽快定。\n- **想便宜** → **G5 次**，二等座 662.5，比 G1 便宜 270，只多 41 分钟（中途停南京 1 站）。我会选这个。\n- **晚一点出发** → G3 次和 G1 同等用时但晚 1 小时开。\n\n京东 APP 直接预订，可累计京豆。",
                "product_cards": [
                    {"card_id": "tr_G1_2026062314", "display_price": 933.0, "reason": "14:00开4h28m最快直达，京沪最快档次车，下午行程首选"},
                    {"card_id": "tr_G5_2026062313", "display_price": 662.5, "reason": "二等座662.5最便宜，只多41分钟性价比最高"},
                    {"card_id": "tr_G3_2026062315", "display_price": 933.0, "reason": "15:00出发同等4h28m用时，适合需要晚1小时出门的行程"}
                ]
            }
        ],
        "final_response": "明天（6/23）下午北京→上海高铁，按最快排序：\n\n| 车次 | 出发 | 到达 | 用时 | 二等座 | 余票 |\n|---|---|---|---|---|---|\n| **G1** ⭐ | 北京南 14:00 | 上海虹桥 18:28 | **4h28m** | ¥933 | 充足 |\n| **G3** | 北京南 15:00 | 上海虹桥 19:28 | **4h28m** | ¥933 | 充足 |\n| G5 | 北京南 13:00 | 上海虹桥 18:09 | 5h09m | ¥662.5 | 充足 |\n\n**推荐**\n- **追最快** → **G1 次**，14:00 开 18:28 到，全程不停靠 4h28m 是京沪最快档；商务座余 8 张，要的话尽快定。\n- **想便宜** → **G5 次**，二等座 662.5，比 G1 便宜 270，只多 41 分钟（中途停南京 1 站）。我会选这个。\n- **晚一点出发** → G3 次和 G1 同等用时但晚 1 小时开。\n\n京东 APP 直接预订，可累计京豆。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ─── 10. 预算类需求（组合规划+计算）───────────────────────────────
    {
        "trajectory_id": "sft_budget_001",
        "category": "预算类需求",
        "user_query": "3000元以内给孩子配一套学习装备，平板+键盘+耳机",
        "thinking": "组合采购：3000总预算分3类。先搜各品类，再用 calculator 算最优配置。优先考虑学习适配（护眼平板/教育资源、办公键盘、降噪耳机）。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "product_search",
                "tool_input": {"query": "学生平板 10寸 护眼 学习", "max_price": 2200, "is_jd_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_pad_001", "title": "华为MatePad 11.5英寸 学生学习平板 128GB", "price": 1899.0, "is_jd_self": True, "rating": 4.8, "key_specs": "120Hz护眼屏/8+128GB/麒麟9000WL/学习中心+学而思", "sales": "月销2.3万件"},
                        {"product_id": "jd_pad_002", "title": "小米Pad 6S Pro 11英寸 学生平板 144Hz", "price": 1999.0, "is_jd_self": True, "rating": 4.7, "key_specs": "144Hz LCD/8+128GB/骁龙8 Gen2/小米HyperOS学习模式", "sales": "月销1.5万件"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "product_search",
                "tool_input": {"query": "平板键盘 蓝牙 学生 轻薄", "max_price": 400, "is_jd_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_kb_001", "title": "华为MatePad 11.5原装磁吸键盘", "price": 399.0, "is_jd_self": True, "rating": 4.8, "key_specs": "磁吸即用免配对/全尺寸键位/触控板支持", "sales": "适配MatePad 11.5"},
                        {"product_id": "jd_kb_002", "title": "罗技K580 静音蓝牙键盘 多设备切换", "price": 269.0, "is_jd_self": True, "rating": 4.9, "key_specs": "3设备切换/静音键帽/2节AAA电池24个月", "sales": "月销1.8万件"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "tool_call",
                "tool_name": "product_search",
                "tool_input": {"query": "学生耳机 降噪 网课 有线", "max_price": 400, "is_jd_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "jd_hp_001", "title": "西伯利亚S21 学生网课耳机 头戴降噪带麦", "price": 169.0, "is_jd_self": True, "rating": 4.7, "key_specs": "头戴式/降噪麦克风/3.5mm+USB双接口/护耳棉", "sales": "月销3.5万件"},
                        {"product_id": "jd_hp_002", "title": "声阔Q20i 头戴蓝牙降噪耳机 学生款", "price": 349.0, "is_jd_self": True, "rating": 4.8, "key_specs": "主动降噪/40h续航/Hi-Res认证/蓝牙5.3", "sales": "月销1.2万件"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 4,
                "step_type": "tool_call",
                "tool_name": "python_calculator",
                "tool_input": {"code": "# 方案A: 华为生态 (适合在线网课多)\na = 1899 + 399 + 169\n# 方案B: 性能党 (小米平板+罗技+声阔)\nb = 1999 + 269 + 349\nprint(f'方案A(华为生态): 平板1899+原装键盘399+网课耳机169 = ¥{a}, 余¥{3000-a}')\nprint(f'方案B(性能党): 小米平板1999+罗技键盘269+声阔降噪349 = ¥{b}, 余¥{3000-b}')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_002", "title": "计算结果", "price": 0.0, "is_jd_self": False, "rating": 5.0, "key_specs": "方案A:2467元,余533/方案B:2617元,余383", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 5,
                "step_type": "step_id",
                "step_type_": "final_response",
                "content": "",
                "product_cards": []
            }
        ],
        # 重写最后一步避免上面手抖错误
        "final_response": "3000 预算给孩子配一套学习装备，我做了两个方案的对比：\n\n**方案 A（华为生态·网课学习党） ¥2467（余 ¥533）** ⭐ 推荐\n- 平板：华为 MatePad 11.5（¥1899）— 120Hz 护眼屏，自带学习中心+学而思网校资源，对小学/初中娃最友好。\n- 键盘：华为原装磁吸键盘（¥399）— 磁吸即用免配对，触控板支持，体验最丝滑。\n- 耳机：西伯利亚 S21 头戴网课耳机（¥169）— 带麦支持网课，月销 3.5 万，闭眼买。\n\n**方案 B（性能党·硬件优先） ¥2617（余 ¥383）**\n- 平板：小米 Pad 6S Pro（¥1999）— 144Hz LCD+骁龙 8 Gen2，性能更强但生态偏娱乐。\n- 键盘：罗技 K580 蓝牙键盘（¥269）— 三设备切换，孩子以后买电脑可继续用。\n- 耳机：声阔 Q20i 主动降噪（¥349）— 真降噪+40h 续航，自习室神器。\n\n**建议**\n- **小学/初中孩子优先方案 A**：华为学习中心 + 学而思自带学习资源，家长控制更省心。\n- **高中以上/动手能力强选方案 B**：性能更强、配件可跨设备复用。\n\n剩余预算可加一个 ¥100 内的平板支架或耐用的钢化膜，体验更完整。",
        "product_cards_final": [
            {"card_id": "jd_pad_001", "display_price": 1899.0, "reason": "华为MatePad 11.5自带学习中心+学而思网校，120Hz护眼屏，方案A核心"},
            {"card_id": "jd_kb_001", "display_price": 399.0, "reason": "原装磁吸键盘免配对，体验最丝滑，配MatePad无缝衔接"},
            {"card_id": "jd_hp_001", "display_price": 169.0, "reason": "头戴+麦克风网课首选，月销3.5万性价比断档"},
            {"card_id": "jd_pad_002", "display_price": 1999.0, "reason": "144Hz+骁龙8 Gen2性能强，适合高中以上孩子"},
            {"card_id": "jd_kb_002", "display_price": 269.0, "reason": "罗技K580三设备切换，未来买电脑可继续用，跨设备首选"},
            {"card_id": "jd_hp_002", "display_price": 349.0, "reason": "声阔Q20i主动降噪40h续航，自习室专注神器"}
        ],
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },
]

# ─────────────────────────────────────────────────────────────────────
# 修正第10条（最后一步）的结构
# ─────────────────────────────────────────────────────────────────────
def fix_last_trajectory(traj):
    """把第10条的最后一步修正成正常的 final_response 格式"""
    # 删除占位错误的 step_id_=5
    traj["steps"] = [s for s in traj["steps"] if s.get("step_type") == "tool_call"]
    # 追加正确的 final_response 步骤
    traj["steps"].append({
        "step_id": len(traj["steps"]) + 1,
        "step_type": "final_response",
        "content": traj["final_response"],
        "product_cards": traj.pop("product_cards_final"),
    })
    return traj

TRAJECTORIES[-1] = fix_last_trajectory(TRAJECTORIES[-1])


# ─────────────────────────────────────────────────────────────────────
# 校验函数
# ─────────────────────────────────────────────────────────────────────
def validate(traj: dict) -> tuple[bool, list[str]]:
    """检查 card_id 是否都来自工具返回，是否符合基本约束。"""
    errors = []
    returned_ids = set()
    for step in traj["steps"]:
        if step.get("tool_output") and step["tool_output"].get("products"):
            for p in step["tool_output"]["products"]:
                returned_ids.add(p["product_id"])

    card_ids = set()
    for step in traj["steps"]:
        for card in step.get("product_cards", []) or []:
            card_ids.add(card["card_id"])

    hallucinated = card_ids - returned_ids
    if hallucinated:
        errors.append(f"幻觉card_id: {hallucinated}")

    if len(traj["final_response"]) < 50:
        errors.append(f"final_response过短: {len(traj['final_response'])}字")

    return (len(errors) == 0, errors)


# ─────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────
def main():
    print(f"准备写入 {len(TRAJECTORIES)} 条 SFT 训练数据...")

    valid_trajs = []
    for i, traj in enumerate(TRAJECTORIES):
        ok, errs = validate(traj)
        status = "✅" if ok else "⚠️"
        print(f"  [{status}] {traj['trajectory_id']:<25} {traj['category']:<10} | {traj['user_query'][:30]}...")
        if not ok:
            for e in errs:
                print(f"        └─ {e}")
        valid_trajs.append(traj)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for traj in valid_trajs:
            f.write(json.dumps(traj, ensure_ascii=False) + "\n")

    # 统计
    by_cat = {}
    for t in valid_trajs:
        by_cat[t["category"]] = by_cat.get(t["category"], 0) + 1

    print(f"\n✅ 已写入：{OUTPUT_PATH}")
    print(f"   总条数：{len(valid_trajs)}")
    print(f"   分类分布：")
    for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"     {cat:<12} : {n} 条")


if __name__ == "__main__":
    main()
