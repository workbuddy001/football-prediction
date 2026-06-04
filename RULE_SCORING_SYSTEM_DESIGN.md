# 竞彩规则评分系统 — 设计需求文档

> **目标读者**: AI实现者（零项目背景）  
> **系统名称**: Rule Scoring & Optimization Engine (RSOE)  
> **输出**: `_rule_scoring_report.md` 每次运行生成完整评估报告  
> **依赖**: Python 3.10+, 项目现有数据文件  
> **参考**: 同项目的 `AI_RULE_MINING_GUIDE.md` 含详细的源数据结构说明

---

## 〇、项目背景（必读）

### 0.1 这是什么项目

这是一个**中国竞彩（体彩）足球投注策略系统**。系统从700+场历史比赛中提取特征，通过硬编码的if-elif规则链决定每场比赛的投注方案。每条规则像这样工作：

```
如果比赛满足条件A+B+C → 投注X球/Y比分/Z元
```

当前有15条活跃规则（R0/R1/G2/G6/H2/H3/S2/S3/S7/S8/P1/X4/X6/C1/N1）。

### 0.2 核心数据文件

| 文件 | 路径 | 内容 |
|------|------|------|
| 比赛数据 | `sporttery_data/{match_id}.json` | 每场一个JSON，含赔率/变化/近况 |
| 实际比分 | `分析模板/_scores.json` | key含match_id，value有home_score/away_score |
| 规则代码 | `ai_reasoning.py` | `compute_betting(data, analysis)` 函数，所有规则逻辑 |
| 推理引擎 | `predict.py` | `analyze_match(data)` 生成V3.6分析结果 |
| 数据加载 | `sporttery_web.py` | 赔率命中率统计、比分推荐等辅助函数 |

完整的数据JSON结构说明见 `AI_RULE_MINING_GUIDE.md` 第二章。

### 0.3 如何运行回测

```python
import json, os, sys, types

# 1. Mock flask (项目依赖flask但回测时不需要)
_m = types.ModuleType('flask')
_m.Flask = type('F', (), {'__init__': lambda *a, **k: None, ...})
sys.modules['flask'] = _m

# 2. 加载命中率缓存
from sporttery_web import _build_change_hitrate, _build_odds_hitrate
_oh = _build_odds_hitrate()
_ch = _build_change_hitrate()

# 3. 加载比分
with open('分析模板/_scores.json', encoding='utf-8') as f:
    scores = json.load(f)
scores_map = {}
for k, v in scores.items():
    if isinstance(v, dict) and v.get('match_id'):
        mid = str(v['match_id'])
        if v.get('home_score') is not None:
            scores_map[mid] = {'total': v['home_score']+v['away_score'], 
                               'hs': v['home_score'], 'aws': v['away_score']}

# 4. 对每场比赛跑规则
for fname in os.listdir('sporttery_data'):
    if not fname.endswith('.json'): continue
    mid = fname.replace('.json', '')
    if mid not in scores_map: continue
    data = json.load(open(f'sporttery_data/{fname}', encoding='utf-8'))
    data['_odds_hitrate'] = _oh
    data['_change_hitrate'] = _ch
    from predict import analyze_match
    from ai_reasoning import compute_betting
    analysis = analyze_match(data)
    bet = compute_betting(data, analysis)
    if bet.get('action') == 'bet':
        # 记录触发和结果
        ...
```

### 0.4 规则代码结构说明

所有规则在 `ai_reasoning.py` 的 `compute_betting(data, analysis)` 函数中，结构是：

```python
def compute_betting(data, analysis):
    # 前置：加载比分推荐、V3.6方向、赔率变化等
    # ...
    
    # 规则链（if-elif瀑布）
    if [条件]:           # 如 H5
        rule = 'H5'
        bet_goals = [进球列表]
        goal_stake = 金额
    elif [条件]:         # 如 X3
        rule = 'X3'
        ...
    # ... 15条规则 ...
    
    if not rule:
        return {'action': 'skip', ...}
    
    # 后置处理：风控减半、甜区翻倍、相似过热跳过等
    # ...
    
    return {'action': 'bet', 'rule': rule, 'goal_bet': {...}, 'score_bets': [...], 'total_stake': ...}
```

**关键字段**：
- `bet['rule']` → 规则名（如'G2'、'S7(甜区翻倍)'——提取时用 `split('+')[0].split('(')[0]`）
- `bet['goal_bet']['goals']` → 投注的总进球数（如[0,2]）
- `bet['goal_bet']['stake']` → 进球投注金额
- `bet['score_bets']` → 比分投注列表，每项含 `{score, stake, odds, tag}`
- `bet['total_stake']` → 该场总投入

### 0.5 盈利计算

```python
actual = scores_map[mid]['total']  # 实际总进球

# 进球投注盈亏
profit = -goal_stake
for g in bet_goals:
    if actual == g or (g == 7 and actual >= 7):  # 竞彩7球+=≥7球
        odds = goal_bet['odds'][str(g)]
        per_stake = goal_stake / len(bet_goals)
        profit += per_stake * odds

# 比分投注盈亏
for sb in score_bets:
    profit -= sb['stake']
    sh, sa = map(int, sb['score'].replace('-', ':').split(':'))
    if sh == actual_hs and sa == actual_aws:
        profit += sb['stake'] * sb['odds']
```

### 0.6 现有规则清单（评分对象）

| 规则 | 类别 | 简要条件 | 投注目标 |
|------|------|---------|---------|
| R0 | 历史高分 | 0:0在历史Top2+g0甜区+平≤3.0 | 0球 |
| R1 | 历史高分 | 历史Top1=3:0+让胜<1.80 | 3:0比分 |
| G2 | 赔率驱动 | g0=10+g2≈3.0+近况≤3.0+平≤3.4 | 0球+2球 |
| G6 | 三维排除 | 6球保留+g0≥18+6球<12 | 6球 |
| H2 | 平局信号 | g0[11-13]+平<3.5+Top1=1:1+.25尾数 | 1:1比分 |
| H3 | 三维排除 | 独留2球+平<3.5+铁壁 | 1:1比分 |
| S2 | 特殊赔率 | 5球保留+s2_alert+近况≥2.5 | 5球 |
| S3 | 特殊赔率 | 6球保留+s3_alert+近况≥2.5 | 6球 |
| S7 | 赔率驱动 | g0=23+2球[4.0-4.3]+近况≤3.0 | 2球 |
| S8 | 赔率变化 | g0<10+平平降>17% | 0:1比分 |
| P1 | 多维交叉 | 黄金1球+通用3球+平平降=0 | 1球+0:1 |
| X4 | 三维残留 | 仅剩3+4球+g0[25-35] | 4球 |
| X6 | 三维残留 | 客让+2:3候选+客攻>主防 | 2:3比分 |
| C1 | 冷推博冷 | V3.6博冷+g0匹配+赔≤100+排15-30 | 比分20元 |
| N1 | 新规则 | g4<5.0+平跌10-20% | 6球 |

### 0.7 需要特殊处理的规则

- **C1**: 完全依赖外部 `v36_analyzer.py` 生成博冷推荐，不适用"条件数量"的过拟合判断
- **G2**: 双选投注（0球和2球各不同金额），盈利模型不同
- **H2**: 精确比分投注，命中率必然低但靠高赔率
- **停用规则**（DISABLED = {'S6','H4','G4','R3','R4','X2','X5','G5','H5'}）不参与评分

---

## 一、系统目标

为现有15条活跃规则逐条建立量化评分档案，自动诊断每条规则的强弱项，给出改进/停用/优化的可执行建议。

---

## 二、评分维度（10维，满分50分）

每条规则在以下10个维度上各得1-5分：

### 2.1 盈利能力（权重最高，共4维20分）

| # | 维度 | 评分标准 | 数据来源 |
|---|------|---------|---------|
| 1 | **ROI** | ≥300%=5, ≥200%=4, ≥100%=3, ≥50%=2, ≥0%=1, <0%=0 | 全量回测盈亏/投入 |
| 2 | **命中率** | ≥75%=5, ≥60%=4, ≥50%=3, ≥40%=2, ≥30%=1, <30%=0 | 命中场次/触发场次 |
| 3 | **净利绝对值** | ≥2000=5, ≥1000=4, ≥500=3, ≥200=2, ≥0=1, <0=0 | 盈亏总额（元） |
| 4 | **ROI稳定性(标准差)** | 按月分组ROI的标准差<10%=5, <30%=4, <50%=3, <100%=2, ≥100%=1 | 月度ROI分组的波动性 |

### 2.2 统计可信度（3维15分）

| # | 维度 | 评分标准 | 数据来源 |
|---|------|---------|---------|
| 5 | **样本量** | ≥30场=5, ≥20=4, ≥10=3, ≥5=2, <5=1 | 触发场次 |
| 6 | **回测一致性** | 前50%数据命中率 vs 后50%命中率差异<10%=5, <20%=4, <30%=3, <50%=2, ≥50%=1 | 时序分割对比 |
| 7 | **过拟合风险** | 条件数≤2且样本≥10=5, 条件数≤3且样本≥8=4, 条件数≤4且样本≥5=3, 条件数≤5=2, 条件数>5=1 | 规则触发条件数量 |

### 2.3 实战可行性（2维10分）

| # | 维度 | 评分标准 | 数据来源 |
|---|------|---------|---------|
| 8 | **触发频率** | 月均≥4场=5, ≥2=4, ≥1=3, ≥0.5=2, 更低=1 | 月均触发场次 |
| 9 | **赔率可得性** | 目标赔率从不>50且均赔>3=5, 均赔>2=4, 均赔>1.5=3, 均赔≤1.5=2 | 目标投注的平均赔率 |

### 2.4 互补性（1维5分）

| # | 维度 | 评分标准 | 数据来源 |
|---|------|---------|---------|
| 10 | **规则独特性** | 无任何相似规则=5, 目标球数相同但条件不同=4, 重叠度<20%=3, 重叠度<50%=2, 重叠度≥50%=1 | 与其他规则共同触发场次占比 |

---

## 三、诊断标签体系

每条规则自动生成2-4个诊断标签：

| 标签 | 触发条件 | 含义 |
|------|---------|------|
| `🔴 停用建议` | ROI<0% 且 样本≥5 | 统计上亏损 |
| `🟡 样本不足` | 样本<5场 | 无法做出统计推断 |
| `🟡 过拟合风险` | 条件数>4 且 样本<10 | 可能过度拟合历史 |
| `🟠 频次过低` | 月均触发<1场 | 实战几乎不会遇到 |
| `🟠 ROI衰减` | 后50%ROI比前50%低>30% | 效果在变差 |
| `🔵 主力规则` | 样本≥10 且 ROI≥100% 且 月均≥2 | 系统支柱 |
| `🟢 健康运行` | 上述标签均不触发 | 一切正常 |
| `⚪ 待观察` | 样本<10 但 ROI>0 | 趋势正向但需更多数据 |
| `🟣 优化候选` | 命中率>50% 但 有2+场"差1球"的比赛 | 窄条件可微调 |

---

## 四、优化建议引擎

### 4.1 投注策略优化

对每条规则的投注金额和组合进行穷举搜索：

**搜索空间**:
- 单球投注: 10/20/30/40/50元
- 双球组合: 不同分配比例（如G2的0球:2球=1:2）
- 比分加注: 0/10/20元（仅在"差1球"占比>30%时建议）

**优化目标**: Max(ROI × log(样本量) + 净利 × 0.3)

**输出示例**:
```
[G2] 当前: 0球10+2球20=30元 | ROI+138%
     → 建议: 0球10+2球30=40元 | ROI+156% ↑18% | 原因: 2球命中次数是0球的3倍
```

### 4.2 条件微调建议

对每个数值条件进行边界敏感性分析：

**方法**: 将当前条件边界左右移动±10%/±20%，观察命中率和触发量的变化：

```
[N1] g4<5.0 → 测试 g4<4.5 / g4<5.5 / g4<6.0
     当前: g4<5.0 | 10场 4/10 ROI+405%
     g4<4.5:  6场 3/6 ROI+380% 样本骤降不建议
     g4<5.5: 15场 5/15 ROI+210% 命中率稀释不建议
     → 当前阈值最优，无需调整
```

### 4.3 规则删除/合并建议

检测完全可被其他规则替代的规则：

```
替代规则: 如果A规则的触发集是B规则触发集的真子集 → 建议删除A
合并规则: 如果A和B的触发条件可以合并为一个更简洁的条件 → 建议合并
```

---

## 五、输出报告结构

```markdown
# 竞彩规则评分报告 — 2026-06-03
## 总览
| 规则 | 总分 | ROI | 命中率 | 样本 | 标签 | 建议 |
|------|------|-----|--------|------|------|------|

## 各规则详细评估

### G2 (总分: 42/50) 🔵主力规则
| 维度 | 得分 | 说明 |
|------|------|------|
| ROI | 4 | +138%, 优秀 |
| ... | ... | ... |

#### 诊断: 🟢 健康运行
#### 投注优化:
- 当前: 0球10+2球20=30元 ROI+138%
- 建议: 保持当前
#### 条件敏感性:
- g0=10: 最优 ✓
- g2[2.9-3.1]: 最优 ✓
- draw≤3.4: 过滤效果良好，draw>3.4仅20%命中 ✓

...

## 全局建议
### 停用候选: X2(ROI-100%), ...
### 合并候选: 无
### 参数待调: N1(g4<5.0→建议验证g4<4.5)
```

---

## 六、技术实现要求

### 6.1 数据加载（完整可运行示例）

⚠️ 项目依赖Flask但在回测中不需要。以下是最小化mock模板：

```python
"""完整的最小化回测框架"""
import json, os, sys, types
from collections import defaultdict

# === Mock Flask (必须，否则import ai_reasoning会失败) ===
_m = types.ModuleType('flask')
class FakeFlask:
    def __init__(self, *a, **k): pass
    def register_blueprint(self, *a, **k): pass
    def route(self, *a, **k): return lambda f: f
_m.Flask = FakeFlask
_m.Blueprint = type('FB', (), {
    '__init__': lambda s, *a, **k: None,
    'route': lambda s, *a, **k: lambda f: f
})
_m.jsonify = lambda x: x
_m.render_template_string = lambda x, **k: x
_m.request = types.SimpleNamespace()
_m.redirect = lambda x: x
_m.url_for = lambda x, **k: x
_m.session = {}
sys.modules['flask'] = _m

# === 加载数据 ===
from sporttery_web import _build_change_hitrate, _build_odds_hitrate, _build_score_hitrate_stats
_oh = _build_odds_hitrate()
_ch = _build_change_hitrate()
_build_score_hitrate_stats()

SCORES_FILE = '分析模板/_scores.json'
DATA_DIR = 'sporttery_data'

with open(SCORES_FILE, encoding='utf-8') as f:
    scores_raw = json.load(f)

scores_map = {}
for k, v in scores_raw.items():
    if not isinstance(v, dict): continue
    mid = v.get('match_id', '')
    hs = v.get('home_score')
    aws = v.get('away_score')
    if not mid or mid == 'test' or hs is None or aws is None: continue
    scores_map[str(mid)] = {'total': int(hs)+int(aws), 'hs': int(hs), 'aws': int(aws)}

# === 逐场回测 ===
from predict import analyze_match
from ai_reasoning import compute_betting

all_bets = []
for fname in sorted(os.listdir(DATA_DIR)):
    if not fname.endswith('.json'): continue
    mid = fname.replace('.json', '')
    if not mid.isdigit(): continue           # 跳过非纯数字ID
    if mid not in scores_map: continue       # 必须有比分
    data = json.load(open(os.path.join(DATA_DIR, fname), encoding='utf-8'))
    data['_odds_hitrate'] = _oh
    data['_change_hitrate'] = _ch
    try:
        analysis = analyze_match(data)
        bet = compute_betting(data, analysis)
    except:
        continue
    if bet.get('action') != 'bet': continue
    
    rule = bet.get('rule', '')
    base_rule = rule.split('+')[0].split('(')[0]  # 'S7(甜区翻倍)' → 'S7'
    actual = scores_map[mid]
    info = data.get('match_info', {})
    d = info.get('match_date', '?') if isinstance(info, dict) else '?'
    
    # 盈利计算（见0.5节）
    profit = _calc_profit(bet, actual)
    
    all_bets.append({
        'rule': base_rule, 'full_rule': rule,
        'date': d, 'profit': profit,
        'stake': bet.get('total_stake', 0),
        'hit': profit > 0,
        'goals': bet.get('goal_bet', {}).get('goals', []),
        'match_id': mid,
    })
```

### 6.2 回测接口

每条规则的触发条件从 `ai_reasoning.py` 的 `compute_betting()` 中提取，或者维护一个独立的规则条件字典：

```python
RULES = {
    'G2': {
        'conditions': {
            'g0': lambda x: x == 10,
            'g2': lambda x: 2.9 <= x <= 3.1,
            'draw': lambda x: x <= 3.4,
            'form': lambda h, a: h + a <= 3.0,
        },
        'bet': {'goals': [0, 2], 'stakes': {0: 10, 2: 20}},
        'category': 'G',
    },
    # ... 14 more rules
}
```

### 6.3 月度分组

```python
# 按月分组计算ROI用于稳定性评分
from collections import defaultdict
monthly = defaultdict(list)
for match in triggered_matches:
    month = match['date'][:7]  # '2026-05'
    monthly[month].append(match['profit'])
monthly_rois = [sum(profits)/len(profits) for profits in monthly.values()]
```

### 6.4 时序分割

```python
# 前50% vs 后50% 一致性检查
sorted_matches = sorted(triggered_matches, key=lambda m: m['date'])
half = len(sorted_matches) // 2
first_half_hitrate = sum(1 for m in sorted_matches[:half] if m['hit']) / half
second_half_hitrate = sum(1 for m in sorted_matches[half:] if m['hit']) / (len(sorted_matches) - half)
consistency = abs(first_half_hitrate - second_half_hitrate)
```

### 6.5 "差1球"检测

```python
# 对于未命中的比赛，检查是否接近命中
near_miss_count = 0
for miss in misses:
    actual = miss['total_goals']
    for target in bet_goals:
        if abs(actual - target) == 1:
            near_miss_count += 1
            break
```

---

## 七、输出文件

| 文件 | 用途 |
|------|------|
| `_rule_scoring_report.md` | 完整评估报告（Markdown） |
| `_rule_scoring_data.json` | 结构化数据（供后续自动化） |

---

## 八、关键注意事项

1. **规则条件标准化**：每条规则的触发条件应该能从代码中自动解析，而不是手动维护
2. **评分阈值可配置**：所有阈值应集中定义，方便A/B测试
3. **增量运行**：如果数据没变化，不重复计算
4. **与现有回测兼容**：复用 `_scores.json` 和 `sporttery_data/`，不要重复造轮子
5. **忽略C1的特殊性**：C1是外部博冷推荐，不适用"条件数量"的过拟合判断
6. **月度分组注意数据量**：个别月份样本<2场时不参与稳定性计算
