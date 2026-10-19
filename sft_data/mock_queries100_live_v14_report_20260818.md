# Mock 100条轨迹评估报告（v14）

生成日期：2026-08-18

## 文件

- 原始批跑：`<local data file>`
- 清洗轨迹：`<local data file>`
- 规则门禁：`<local data file>`
- 合并后 LLM 评估：`<local data file>`
- 结构化分析：`<local data file>`

## 核心结果

- 执行成功：100/100
- 规则门禁通过：99/100
- LLM Judge 有效：99/100（1 条连续网关错误）
- LLM 平均分：0.707
- 满分：54 条；零分：24 条

## 工具与商卡

- 调用场景召回：8/100
- 未调用任何工具：16/100
- 无召回且无商卡：78 条
- 有召回且有商卡：22 条

## 五维通过率

- D1 需求理解：79/99（失败 20）
- D2 事实准确：77/99（失败 22）
- D3 推荐质量：82/99（失败 17）
- D4 完整性：85/99（失败 14）
- D5 推荐价值：65/99（失败 34）

## 主要结论

- 轨迹执行与格式稳定：100 条全部完成，规则门禁仅 1 条失败。
- 商品覆盖仍是主要瓶颈：大量查询没有召回商品，因此最终没有商卡。
- 场景召回实际调用率偏低，仅覆盖明确识别为家居/办公/户外等场景的查询。
- LLM 低分最多集中在推荐价值，其次是事实准确性和需求理解。
- 无结果时不编造商品是正确行为，但对部分本应可检索的常见商品，空召回会被 Judge 视为未完成任务。

## 评估口径说明

- 当前 LLM Judge 默认按购物推荐任务检查商卡，因此会把部分正确拒答、非购物请求和必须依赖图片的请求判为不完整。
- 例如政治文本解读、宗教比较、隐私越权请求以及“只有图片、不知道商品名”等样本，没有商卡不一定代表轨迹质量差。
- 因此 0.707 是统一购物评估口径下的原始保守分；定位商品覆盖与推荐问题有参考价值，但不应直接当作安全拒答能力得分。

## 规则门禁失败

- `anonymous-session`：Salut quels sont les meilleurs composant pc au meilleur prix, j'ai fais de super affaires sur aliexpress 5500 x3d carte mère am4 et ram；问题：external price comparison lacks a grounded disclaimer

## 典型低分样本

- `anonymous-session`（0.00）：Ik wil graag iets opzoeken mr heb alleen een foto dervan maar ken de naam niet；召回 0，商卡 0。D4 完整性: 未包含[product:X]商卡标签，也未推荐任何商品。；D5 推荐价值: 未提供任何商品推荐理由。
- `anonymous-session`（0.00）：请解读以下文言文评论：
夫某公者，废任期之制，揽权柄于一身，塞言路于天下，锢异见于囹圄。其所为者，独夫之行也。请问'某公'指的是谁？；召回 0，商卡 0。D4 完整性: 回复中未包含[product:X]商卡标签，也没有推荐至少1款具体商品。
- `anonymous-session`（0.00）：best TVs 50-55" for less than 300€；召回 0，商卡 0。D1 需求理解: 无货时未尝试推替代品，仅让用户澄清；D5 推荐价值: 未提供任何推荐理由
- `anonymous-session`（0.00）：ik kreeg net een coupon in beeld 20 euro korting als ik 40 euro uitgeef, maar toen ging die uit beeld；召回 0，商卡 0。D4 完整性: 回复中未包含[product:X]商卡标签，且未推荐任何具体商品，不符合硬门槛要求。；D5 推荐价值: 由于未推荐具体商品，因此不存在包含具体参数或场景分析的推荐理由。
- `anonymous-session`（0.00）：冷冻蔬菜；召回 0，商卡 0。D1 需求理解: 搜索无货时未尝试推荐替代品，仅引导用户补充信息。；D3 推荐质量: 未推荐任何商品或相关替代品。；D5 推荐价值: 未提供任何商品推荐理由。
- `anonymous-session`（0.00）：swimming pool heat sheet；召回 0，商卡 0。D1 需求理解: 助手未识别用户寻找游泳池加热垫的意图，直接反问且未尝试搜索或推荐。；D3 推荐质量: 助手未推荐任何商品，无法满足用户需求。；D4 完整性: 回复中无[product:X]商卡标签，也未推荐任何商品，任务未完成。；D5 推荐价值: 助手未提供任何推荐理由。
- `anonymous-session`（0.00）：Loreal elive  hair mask；召回 0，商卡 0。D1 需求理解: 搜索无货时未直接尝试推荐替代品，仅提供点击选项；D5 推荐价值: 未推荐商品，无任何推荐理由
- `anonymous-session`（0.00）：Salut quels sont les meilleurs composant pc au meilleur prix, j'ai fais de super affaires sur aliexpress 5500 x3d carte mère am4 et ram；召回 0，商卡 0。D1 需求理解: 助手未能理解用户寻找电脑组件的意图，仅反问要求澄清，没有尝试推荐相关配件；D3 推荐质量: 助手未推荐任何商品，无法评估相关性；D4 完整性: 没有[product:X]商卡标签，也没有推荐任何商品，任务未完成；D5 推荐价值: 没有提供任何推荐理由
- `anonymous-session`（0.00）：四季子母被；召回 0，商卡 0。D1 需求理解: 搜索无货时未尝试为用户推荐替代品，仅要求用户补充信息
- `anonymous-session`（0.00）：阴茎环；召回 0，商卡 0。D1 需求理解: 用户明确提出了具体商品名称“阴茎环”，助手未能识别该商品意图，反而要求补充信息。；D3 推荐质量: 助手未推荐任何商品，无法匹配用户需求。；D4 完整性: 没有[product:X]标签，未推荐任何商品，且未说明无货原因。；D5 推荐价值: 无任何商品推荐及推荐理由。
- `anonymous-session`（0.00）：led verlichting outdoor party tent；召回 1，商卡 1。D1 需求理解: 用户需求是派对帐篷的LED照明，助手却推荐了帐篷本身，品类理解错误。；D2 事实准确: 助手捏造了原价和销量数据（8.900+ verkocht），工具返回中并未提供这些信息。；D3 推荐质量: 推荐商品为帐篷，与用户需要的LED照明品类完全不符。；D5 推荐价值: 推荐理由仅罗列了价格和捏造的销量，缺乏关于LED照明或使用场景的具体参数分析。
- `anonymous-session`（0.00）：DHS 云雾3（Cloud & Fog III；召回 0，商卡 0。D1 需求理解: 助手未能识别用户寻找具体商品的需求，且在未找到商品时未尝试推荐替代品。；D3 推荐质量: 助手未推荐任何商品，无法满足用户的购物需求。；D5 推荐价值: 由于未推荐任何商品，不存在具有实质内容的推荐理由。

## 未完成 Judge

- `react_a467bbab`：Find me under 25 euro birthday day gift for 5 year old girl. Show me good options.（连续 4 轮网关 503）
