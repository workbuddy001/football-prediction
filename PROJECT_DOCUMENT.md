# 竞彩足球AI预测系统 — 项目文档

> 给其他大模型的完整项目说明书。包含核心代码、规则体系、回测结果。

---

## 一、项目概况

**目标**：基于竞彩赔率数据，通过多维度排除法和信号规则，进行足球比赛投注预测。

**数据源**：中国竞彩网实时API（sporttery.cn）

**技术栈**：Python 3 + Flask（零第三方依赖，仅标准库）

**核心文件**（按重要性排序）：

| 文件 | 作用 | 
|------|------|
| `ai_reasoning.py` | 核心投注引擎，19条信号规则 |
| `v36_analyzer.py` | V3.6多维分析（3D排除+近况+防守+画像） |
| `sporttery_web.py` | Flask Web服务 + 赔率命中率统计 |
| `predict.py` | 独立预测脚本（不受缓存影响） |
| `分析模板/_scores.json` | 历史比分结果（回测数据源） |
| `sporttery_data/*.json` | 竞彩API缓存（每match_id一个文件） |

---

## 二、快速使用

```bash
git clone https://github.com/workbuddy001/football-prediction.git
cd football-prediction
python predict.py              # 抓取+分析今天所有比赛
python predict.py 2039856      # 单场分析
python predict.py --all        # 所有历史未赛
```

---

## 三、核心推理流程

```
Step0  方向判断（0球赔率+线位+水位+HAD+防守多维投票）
Step2.5 造热检查（三步法：系统推荐5信号/最低赔造热/0球反向）
Step4  三维排除矩阵（赔率命中率 × 变化命中率 × 7类排除规则）
Step7.8 比分反推（攻击力×防守力交叉推理）
Step7.9 进球数推荐（终审+反审+建议/慎重标签）
→ compute_betting（19条规则优先级链匹配投注）
→ 比分保护（+10元买V3.6首选比分）
```

---

## 四、核心代码：ai_reasoning.py

### 4.1 compute_betting 函数签名

```python
def compute_betting(data, analysis):
    """
    输入: data(竞彩API原始数据), analysis(V3.6分析结果)
    输出: {'action':'bet'/'skip', 'rule':'R0', 'goal_bet':{...}, 
            'score_bets':[...], 'total_stake':金额}
    """
```

### 4.2 规则优先级链（从高到低）

```python
if h5_11:       rule='H5'     # 平平↓信号
elif h4_11:     rule='H4'     # (已停用)
elif x3_123:    rule='X3'     # 三维排除1+2+3球
elif x4_34:     rule='X4'     # 三维排除3+4球
elif x5_45:     rule='X5'     # 建议+4+5球
elif x6_23:     rule='X6'     # 客让+2:3
elif x2_35:     rule='X2'     # 三维排除3+5球
elif R0检查:    rule='R0'     # 0球信号
elif R1检查:    rule='R1'     # 3:0信号
elif S7检查:    rule='S7'     # 2球信号
elif F检查:     rule='F'      # 7球铁桶
elif G7检查:    rule='G7'     # 7球排除
elif S3检查:    rule='S3'     # 6球近况小
elif G6检查:    rule='G6'     # 6球排除
elif S2检查:    rule='S2'     # 5球近况小
elif H3检查:    rule='H3'     # 1:1信号
elif H2检查:    rule='H2'     # 1:1宽松
elif H1检查:    rule='H1'     # 1:1最宽松
elif G5检查:    rule='G5'     # 5球排除
elif S1检查:    rule='S1'     # 1球信号
```

### 4.3 R0规则详解（最典型示例）

```python
# R0触发条件（必须同时满足）：
# 1. 0球赔率在[9.5, 10.5]甜区
# 2. 平赔 <= 3.0（市场预期胶着）
# 3. V3.6推荐 ≠ [1, 2]球
# 4. 联赛过滤：排除西甲/欧联/瑞典超/日职/韩职
# 5. g0≥10.5+平平下降 → 陷阱信号，排除

if not (9.5 <= g0 <= 10.5):
    return {'action': 'skip'}
if draw and draw > 3.0:
    return {'action': 'skip'}
if rec_goals and rec_goals[:2] == [1, 2]:
    return {'action': 'skip'}

rule = 'R0'; bet_goals = [0]; goal_stake = 20
```

### 4.4 X3规则详解（三维排除信号）

```python
# X3: 三维排除后恰好只剩1+2+3球 + 2球3球警惕 + 推荐含5球
# 预计算阶段:
if kept_goals == {'1球', '2球', '3球'}:
    if '警惕' in 2球状态 and '警惕' in 3球状态:
        rec_goals = analysis['recommended']['goals']
        if 5 in rec_goals[:2]:  # 推荐含5球
            x3_123 = True

# 投注: 3球20元
rule = 'X3'; bet_goals = [3]; goal_stake = 20
```

### 4.5 X5规则详解（V3.6建议投注信号）

```python
# X5: 建议投注 + 推荐4+5球 + 无其他规则冲突
fgp = analysis.get('final_goal_pick', {})
skip_reason = fgp.get('skip_reason', [])
rec_goals = analysis['recommended']['goals']

if (not skip_reason) and rec_goals[:2] == [4, 5]:
    x5_45 = True

rule = 'X5'; bet_goals = [4]; goal_stake = 20
```

### 4.6 X6规则详解（客让2:3信号）

```python
# X6: 让胜>让负(客队让球) + 2-3在候选 + 客攻-主防≥1.0
if rs_val > rl_val:  # 客让
    if a_att - h_def >= 1.0:  # 客队攻击力碾压
        if '2-3' in filtered_scores:
            x6_23 = True

rule = 'X6'; bet_goals = []  # 纯比分投注
score_bets.append({'score': '2:3', 'stake': 20})
```

### 4.7 比分保护逻辑

```python
# 所有进球投注自动附带：
# +10元买V3.6首选比分（filtered_scores中同进球数的第一个比分）
if bet_goals and goal_stake > 0:
    rec = analysis.get('recommended', {})
    fs = rec.get('filtered_scores', [])
    so = data.get('score_odds', {})
    for g in bet_goals:
        for f in fs:
            if f.get('goals') == g:
                sc = f.get('score', '')  # '3-0' → '3:0'
                odds = so.get(odds_key)
                score_bets.append({'score': sc, 'odds': odds, 
                                   'stake': 10, 'tag': '比分保护'})
                break
```

---

## 五、核心代码：v36_analyzer.py 关键输出字段

### 5.1 analysis 字典结构

```python
{
  'step0': {
    'direction': '大球/小球',     # Step0方向判断
    'odd_type': '强(防守一致)',   # 置信度
  },
  'recent_summary': {
    'combined_avg': 3.4,         # 近况均球
    'h_att': 2.0,               # 主队攻击力
    'h_def': 1.2,               # 主队失球
    'a_att': 2.8,               # 客队攻击力
    'a_def': 0.8,               # 客队失球
  },
  'exclusion': {
    'kept': [                   # 保留的进球选项
      {'goal': '2球', 'status': '⭐变高共振'},
      {'goal': '3球', 'status': '⚠️警惕造热'},
      {'goal': '4球', 'status': '✅观察保留'},
    ],
  },
  'recommended': {
    'goals': [3, 4, 5],         # 候选总进球(排序)
    'filtered_scores': [        # 候选比分
      {'goals': 3, 'score': '2-1', 'tag': '主胜'},
      {'goals': 4, 'score': '2-2', 'tag': '平局'},
    ],
    'top_score': '2-1',
  },
  'final_goal_pick': {
    'single': 4,                # 单选进球数
    'double': [4, 3],            # 双选
    'skip_reason': [],           # 空=建议投注, 非空=慎重投注
    'conflict': False,           # 方向冲突标志
  },
}
```

### 5.2 三维排除标签含义

| 标签 | 含义 | 处理 |
|------|------|------|
| ⭐变高共振 | 赔率命中率≥25%+变化命中率≥25% | 保留(双高) |
| ⚠️警惕造热 | 仅一方高或中等 | 保留但警惕 |
| ✅观察保留 | 命中率中低但排除规则未触发 | 保留 |
| 🚫双低 | 双方都<10% | 强排除 |
| ⛔1率0% | 任一方为0%(样本≥5) | 绝对排除 |
| ⚡矛盾 | 赔率高+变化低 | 排除 |

---

## 六、全部信号规则速查表

### 进球数信号

| 规则 | 条件摘要 | 投注 | 4-5月 | 命中率 | ROI |
|------|----------|------|-------|--------|-----|
| R0 | 0球[9.5-10.5]+平赔≤3.0+推荐≠1+2 | 0球20元 | 4场 | 100% | +895% |
| X3 | 三维仅剩1+2+3警惕+推荐含5 | 3球20元 | 6场 | 67% | +129% |
| X5 | 建议+推荐4+5球+无规则 | 4球20元 | 10场 | 70% | +201% |
| X4 | 三维仅剩3警惕+4保留 | 4球20元 | 3场 | 67% | +240% |
| X2 | 三维仅剩3+5球 | 2球20元 | 2场 | 100% | +225% |
| S7 | 0球=23+2球[4.0-4.3] | 2球20-40元 | 5场 | 100% | +328% |
| S3 | 近况<2.5+6球保留 | 6球20元 | 5场 | 80% | +1190% |
| S2 | 近况<2.5+5球保留 | 5球20元 | 3场 | 100% | +837% |
| S1 | 近况>2.5+1球变高共振 | 1球20元 | 5场 | 40% | +218% |
| G7 | 三维7球保留/警惕+o0≥12 | 7球20元 | 11场 | 27% | +491% |
| G6 | 三维6球保留 | 6球20元 | 4场 | 75% | +478% |
| G5 | 三维5球警惕 | 5球20元 | 2场 | 50% | +200% |
| F | 近况>4+铁桶+0球25-35 | 7球20元 | 5场 | 40% | +260% |

### 比分信号

| 规则 | 条件摘要 | 投注 | 4-5月 | 命中率 | ROI |
|------|----------|------|-------|--------|-----|
| H5 | 平平↓≥10%+count≥3+draw∈[2.85,3.05] | 1:1 20元 | 7场 | 57% | +224% |
| H3 | 平平↓2-3次+2球≥3.05+平<3.2+Top1=1:1 | 1:1 30元 | 7场 | 71% | +329% |
| H2 | 平平3次↓>10%+Top1≠1:1 | 1:1 10元 | 6场 | 67% | +313% |
| H1 | 平平↓次≥2+0球<10.5+Top1=1:1 | 1:1 10元 | 4场 | 50% | +260% |
| R1 | 推荐3:0+让胜<1.80 | 3:0 20元 | 6场 | 33% | +200% |
| X6 | 客让+2:3候选+客攻>主防 | 2:3 20元 | 3场 | 100% | +2100% |

### 比分保护

所有进球投注自动+10元买V3.6首选比分（19%命中率，ROI+585%）

### 回测总览

| 指标 | 值 |
|------|-----|
| 数据范围 | 2026年4-5月 |
| 有效比赛 | 1162场 |
| 触发投注 | 100场 |
| 命中 | 60场 |
| 命中率 | 60% |
| 总投入 | 2050元 |
| 总回报 | 9364元 |
| **ROI** | **+357%** |

---

## 七、predict.py 核心逻辑

```python
# 每次运行都是全新进程，零缓存
# 步骤1: 清空所有缓存模块
for m in list(sys.modules):
    if m in ('v36_analyzer', 'ai_reasoning', 'sporttery_web'):
        del sys.modules[m]

# 步骤2: 强制刷新命中率统计（从_scores.json重建）
_sw._odds_hitrate_cache = None
_sw._change_hitrate_cache = None
_sw._score_hitrate_cache = None

# 步骤3: 从竞彩API实时抓取数据
api = SportteryAPI()
api.fetch_and_save(mid)  # 覆盖sporttery_data/*.json

# 步骤4: 执行分析+投注决策
analysis = analyze_match(data)
bet = compute_betting(data, analysis)

# 输出: rule, bet_goals, score_bets, total_stake
```

---

## 八、数据格式

### sporttery_data/{match_id}.json

```json
{
  "match_info": {"match_num_str": "周三001", "home_team": "弗拉门戈", ...},
  "had": {"胜": "1.32", "平": "4.00", "负": "8.20"},
  "total_goals": {"0球": "10.00", "1球": "4.20", "2球": "3.10", ...},
  "score_odds": {"01:00": "6.0", "02:00": "8.0", ...},
  "hhad": {"让胜": "2.73", "让平": "3.15", "让负": "2.30"},
  "hafu_change": {"平平": {"pct": -5.2, "count": 3}, ...},
  "_odds_hitrate": {...},    # 注入的赔率命中率统计
  "_change_hitrate": {...}   # 注入的变化命中率统计
}
```

### 分析模板/_scores.json

```json
{
  "2039856": {
    "match_id": "2039856",
    "home_team": "弗拉门戈",
    "away_team": "拉普拉塔大学生",
    "home_score": 1, "away_score": 0,
    "record_time": "2026-05-21 10:42:00"
  }
}
```

---

## 九、技术要点

1. **无第三方依赖**：Python标准库 + Flask
2. **缓存管理**：Flask端每次请求执行 `importlib.reload` 确保代码更新无需重启
3. **命中率实时重建**：从 `_scores.json` 每次重建，保证与最新比分同步
4. **独立预测脚本**：`predict.py` 不依赖Flask，每次新进程零缓存
5. **规则优先级**：按ROI和信号强度从高到低排列，避免信号冲突

---

## 十、已知局限和改进方向

1. **方向判断**：V3.6在总进球上准确率高（71%），但胜平负方向易翻车（73%翻车率）
2. **低频信号**：X6(3场)、X2(2场)等信号触发太少，统计显著性有限
3. **极端值依赖**：部分高ROI信号（G7, S3）依赖高赔率极端值，小样本波动大
4. **近况数据**：仅用近几场比赛的攻防数据，样本量有限

---

*文档生成时间：2026-05-22 | 项目版本：V3.9*
