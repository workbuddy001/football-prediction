# 低频高赔规则深挖 — 需求与设计文档

> 版本: v1.0 | 目标: 发现类似C1的低频高ROI比分投注规律

---

## 一、背景

C1规则的成功模式：
- 触发频率极低（35/870 = 4%）
- 冷推比分赔率高（均值21x，上限100x）
- 命中率不低（31%，11/35）
- ROI极高（+561%）
- 价值来源：高赔率覆盖低命中，单场回报足以抵消多场亏损

现有系统已覆盖常规进球数投注（0-7球），但比分投注（精确比分）的规律挖掘不充分。本任务目标是系统性地扫描所有比分赔率数据，发现类似C1的低频高赔比分规律。

---

## 二、数据环境

### 2.1 项目路径
```
d:\work\workbuddy\足球预测
```

### 2.2 关键数据文件

| 文件 | 说明 |
|------|------|
| `sporttery_data/{match_id}.json` | 每场比赛的完整赔率数据 |
| `分析模板/_scores.json` | 实际比分结果 |
| `v36_analyzer.py` | V3.6推理引擎（产出score_bet等） |
| `ai_reasoning.py` | 投注策略（含C1规则，行927-957参考） |

### 2.3 比分赔率数据结构

每场 `sporttery_data/{match_id}.json` 中的 `score_odds` 字段：

```json
{
  "score_odds": {
    "01:00": 14.0,  // 1:0 赔14倍
    "00:01": 8.0,   // 0:1 赔8倍
    "02:02": 9.5,   // 2:2 赔9.5倍
    ...31种可能的比分...
  }
}
```

比分key格式：`MM:SS`（两位数，不足补零），如 `03:01` = 3:1。

### 2.4 其他可用的匹配特征

| 特征 | 数据来源 | 说明 |
|------|----------|------|
| g0~g7 | `total_goals` | 总进球赔率（0球~7+球） |
| had_w/d/l | `had` | 胜平负赔率 |
| hhad_ball | `hhad` | 让球数（正=主受让，负=主让） |
| g0变化率 | `ttg_change` | 0球赔率变化百分比 |
| had变化率 | `had_change` | 胜平负赔率变化 |
| form_avg | v36_analyzer | 两队近况均值 |
| league | `match_info` / `_scores.json` | 联赛名 |

### 2.5 运行环境

所有脚本需要在 `d:\work\workbuddy\足球预测` 目录下运行。因为 `ai_reasoning.py` 和 `sporttery_web.py` 依赖 Flask，独立脚本需要 mock flask：

```python
import types, sys
class _MockBP:
    def route(self,*a,**kw): return lambda f:f
class _MockApp:
    def route(self,*a,**kw): return lambda f:f
    def register_blueprint(self,*a,**kw): pass
_mock = types.ModuleType('flask')
_mock.Flask=lambda *a,**kw:_MockApp()
_mock.Blueprint=lambda *a,**kw:_MockBP()
_mock.jsonify=lambda *a,**kw:{}
_mock.request=types.SimpleNamespace(method='GET',is_json=False)
_mock.render_template_string=lambda *a,**kw:''
sys.modules['flask']=_mock

# 必须加载命中率数据（否则v36_analyzer输出不完整）
import sporttery_web as _sw
_sw._odds_hitrate_cache=_sw._change_hitrate_cache=None
from sporttery_web import _build_odds_hitrate, _build_change_hitrate
oh=_build_odds_hitrate()
ch=_build_change_hitrate()

# 读取比赛数据时注入命中率
data=json.load(open(fp))
data['_odds_hitrate']=oh
data['_change_hitrate']=ch
```

---

## 三、挖掘策略

### 3.1 核心思路

C1的发现路径：
```
v36_analyzer → score_bet (比分推荐) → C1过滤(g0/goals/odds) → 投注
```

但 `score_bet` 覆盖面有限（仅无推荐博冷策略）。本任务需要绕过 v36_analyzer，直接从原始 `score_odds` 构建候选比分集，然后用 C1 式的过滤框架筛选。

### 3.2 三步挖掘流程

```
Step 1: 构建候选比分池
        每场比赛：取所有赔率 >= 某个阈值(如15x)的比分 → 候选集

Step 2: 网格搜索过滤条件
        对每个候选比分组合，尝试 g0/goals/had/hhad 等维度的过滤阈值
        目标：命中率 >= 15% AND ROI >= 100%

Step 3: 统计验证 + 逻辑审查
        Wilson CI下界 >= 10%, 样本 >= 15, 逻辑可解释
```

### 3.3 C1式过滤框架

C1的核心过滤逻辑（参考 `ai_reasoning.py` 行927-957）：

```python
# 输入: score(比分), odds(赔率), goals(进球数), g0(0球赔率)
# 输出: 是否通过过滤

def c1_filter(score, odds, goals, g0):
    # 基础: 赔率上限
    if odds > 100: return False      # 超100倍不赌
    
    # 精确定位区间
    if 15 < odds <= 30: return False # 15-30x是模糊区间
    
    # 进球数 + g0 + 赔率 三维过滤
    if goals >= 5 and g0 < 25 and odds <= 20: return False  # 5球低赔假信号
    if goals == 4 and 10 < g0 < 30 and odds <= 20: return False  # 4球中g0低赔不可靠
    if goals <= 2 and g0 >= 15 and odds <= 20: return False  # 小球高g0低赔矛盾
    
    return True
```

**设计思路**：三重维度交叉验证：进球数（goals）定基调、g0（0球赔率）定预期进球水平、赔率（odds）定信号强度。三者矛盾时过滤。

### 3.4 可探索的维度

除了C1已有的 goals/g0/odds 三维，下面维度可能产生新规律：

| 维度 | 示例过滤 | 逻辑 |
|------|----------|------|
| had（胜平负赔率） | `had_w < 1.5 AND goals <= 2 AND odds > 30` → 跳过 | 强队低赔但推大比分冷推=矛盾 |
| hhad（让球） | `hhad主让-1 AND goals >= 4 AND odds > 50` → 保留 | 让1球深盘推大比分=庄家看好进球 |
| g0变化率 | `g0_pct_down > 10 AND odds > 40` → 警惕 | g0急降=诱导大球，冷推可能是陷阱 |
| form_avg（近况） | `form_avg < 2.0 AND goals >= 4 AND odds > 30` → 跳过 | 进攻弱的队推大比分=不靠谱 |
| 联赛 | `league in ['日职','韩职'] AND goals >= 4` → 跳过 | 小球联赛推大比分=低概率 |
| g0/odds比 | `g0/odds < 0.3` → 保留 | g0很低但冷推赔率很高=庄家看好这个比分 |

---

## 四、执行计划

### Phase 1: 基础扫描（必做）

**目标**：找出所有"高赔比分 + 合理过滤后命中率 >= 15%"的组合。

**脚本**：`_lf_phase1_scan.py`

**步骤**：
1. 加载所有 `_scores.json` 中有比分的比赛（约870场）
2. 对每场，读取 `sporttery_data/{mid}.json` 的 `score_odds`
3. 提取所有赔率 > 5x 的比分（排除常规比分如1-0、1-1等）
4. 对每个高赔比分，记录：score, odds, goals(球数), g0, had_w/d/l, hhad_ball, league, form_avg, g0变化率
5. 输出 `_lf_candidate_scores.csv`

**输出格式**：
```csv
match_id,score,odds,goals,g0,had_w,had_d,had_l,hhad_ball,league,form_avg,g0_change_pct,actual_score,hit
2039052,0-4,60.0,4,9,2.10,3.50,3.20,-1,法甲,2.8,-5.3,0:4,1
2038872,2-2,12.0,4,14,2.50,3.10,2.80,0,英冠,3.1,2.1,2:2,1
```

### Phase 2: 网格搜索（核心）

**目标**：在候选比分集上，穷举过滤条件组合，找最佳ROI规则。

**脚本**：`_lf_phase2_gridsearch.py`

**搜索空间**：
```python
FILTER_DIMS = {
    'goals': [1, 2, 3, 4, 5],          # 进球数（可组合如[4,5]）
    'odds_min': [5, 10, 15, 20, 30, 50, 80],  # 最低赔率
    'odds_max': [20, 30, 50, 80, 100, 999],   # 最高赔率
    'g0_range': [  # 0球赔率区间
        (0, 10), (10, 15), (15, 20), (20, 30), (30, 99),
    ],
    'had_w_range': [(1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 99)],
    'hhad': ['主让', '主受让', '平手'],
    'league_group': ['五大联赛', '北欧', '亚洲', '其他'],
}
```

**搜索策略**：
1. 单维度搜索：对每个维度单独过滤，记录触发次数和命中率
2. 二维组合：对有区分度的维度进行两两组合
3. 三维组合：对二维中 ROI >= 100% 且样本 >= 10 的组合，加第三维度
4. 每个组合计算：触发次数、命中率、Wilson CI下界、平均赔率、ROI

**筛选标准**：
- 命中率 >= 10%（高赔比分天然低命中）
- ROI >= 100%
- 样本 >= 10场
- Wilson CI下界 >= 5%

### Phase 3: C1式定制过滤（高级）

**目标**：模仿C1的"矛盾检测"逻辑，设计智能过滤。

**脚本**：`_lf_phase3_smart_filter.py`

**核心思想**：C1的成功在于发现了赔率与基本面之间的"矛盾"信号。
- goals=4 + g0适中(10-30) + odds低(<=20) = 矛盾 → 过滤
- goals>=5 + g0低(<25) + odds低(<=20) = 假信号 → 过滤

对每个候选规则，类似地检查是否存在"赔率 vs 基本面"的矛盾：

```
如果 进球数大(>=4) AND g0高(>=25) AND 赔率高(>=40) → 庄家不给面子=可能不会出 → 过滤
如果 进球数小(<=2) AND g0低(<10) AND 赔率高(>=20) → 反常信号 → 保留
```

### Phase 4: 特定比分挖掘（探索性）

**目标**：不按进球数分组，直接按具体比分挖掘规律。

**思路**：某些比分（如2-2、3-2、4-1）可能有独立于进球数的规律。对每个高频比分，独立挖掘触发条件。

**示例**：
```
比分=2-2: 在所有比赛中的命中率约5%，但在 g0=10-14 + had_d<3.5 时命中率显著提升
比分=3-2: 在 hhad主让-1 + g0=15-25 时命中率提升
```

---

## 五、输出规范

### 5.1 最终报告

`LOW_FREQ_HIGH_ODDS_REPORT.md`

```
# 低频高赔比分规律挖掘报告

## 执行摘要
- 扫描比赛: N场
- 发现候选规则: M条
- 通过统计验证: K条

## 规则详情

### H1: {规则名}
- 触发条件: {具体条件}
- 投注: {比分} {金额}元
- 回测: {N}场触发, {H}命中({H/N*100}%), 平均赔率{O}x, ROI{+R}%
- Wilson CI: [{L}%, {U}%]
- 逻辑: {为什么这个规律可能存在}
- 风险: {局限性}

### H2: ...

## 与现有规则冲突检测
- [ ] H1与G2冲突？...
- [ ] H2与S3重叠？...

## 实现建议
```python
# 在 ai_reasoning.py 的 compute_betting() 中添加:
# H1: {规则名}
if {触发条件}:
    rule = 'H1'
    score_bets = [{'score': '{比分}', 'odds': {赔率}, 'stake': 20, 'tag': '{标签}'}]
```

## 附录
- 候选规则全量表
- 统计检验详情
```

### 5.2 统计要求

每条规则必须附带：
- 二项检验 p 值（拒绝 H0: 命中率 = 全量平均水平）
- 95% Wilson 置信区间
- Cohen's h 效应量（vs 全量该比分命中率）
- 过拟合风险评分（样本量/特征维度比）

---

## 六、关键注意事项

1. **不要改现有代码**：所有脚本以 `_lf_*.py` 前缀命名，输出到 `_lf_output/` 目录。

2. **命中率数据必须注入**：不注入 `_odds_hitrate` 和 `_change_hitrate` 会导致分析不完整。

3. **高赔比分天然稀疏**：赔率 > 30x 的比分每场可能只有 3-5 个候选，全量命中率 < 5%。不要用常规 30%+ 命中率标准，15% 已经很好。

4. **样本量是硬约束**：规则触发 >= 10场才有统计讨论价值。低于此数只报告不推荐。

5. **逻辑优先于数据**：一条规则即使回测好，如果没有合理的足球逻辑解释，标记为"数据挖掘嫌疑，待观察"。

6. **比分key格式注意**：`score_odds` 用 `01:02` 格式，实际比分用 `1:2` 格式。比较时需要统一。

7. **C1已占用的区间避免重复**：如果新规则和C1高度重叠，只保留更优的。

---

## 附录A：现有规则速查

| 规则 | 类型 | 简要 | 全量ROI |
|------|------|------|---------|
| C1 | 比分 | 无推荐博冷比分20元 | +561% |
| G2 | 进球 | g0=10+g2≈3.0→0/2球 | +132% |
| S8 | 进球 | 特定1球模式 | +141% |
| H2 | 比分 | 1:1特定赔率 | +275% |
| H3 | 比分 | 特定比分模式→0:2 | +405% |
| P1 | 混合 | 黄金1球+通用3球 | +60% |
| N1 | 进球 | g4<5.0+平跌→6球 | +405% |
| X6 | 进球 | 排除法→6球 | +250% |

## 附录B：Wilson置信区间公式

```python
import math
def wilson_ci(hits, n, z=1.96):
    if n == 0: return (0, 1)
    p = hits / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    m = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n) / d
    return (max(0, c-m), min(1, c+m))
```
