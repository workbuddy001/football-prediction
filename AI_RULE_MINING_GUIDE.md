# 足球竞彩规则挖掘系统 — AI执行手册

## 一、项目概况

700+场足球比赛数据，每场有赔率、近况、V3.6推理结果、实际比分。目标：从数据中自动发现投注规则，像现有14条规则一样严密可验证。

---

## 二、源数据结构

### 2.1 文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 比赛数据 | `sporttery_data/{match_id}.json` | 每场一个JSON，共700+场 |
| 实际比分 | `分析模板/_scores.json` | key为match_id，value含home_score/away_score |

### 2.2 JSON结构（单场）

```json
{
  "match_id": "2040087",
  "match_info": {
    "home_team": "威尔士", "away_team": "加纳",
    "match_date": "2026-06-03", "match_num": "周二203"
  },
  "total_goals": {       // 总进球赔率
    "0球": 9.50, "1球": 3.90, "2球": 3.30,
    "3球": 3.30, "4球": 6.40, "5球": 13.50,
    "6球": 30.0, "7球": 45.0
  },
  "had": {               // 胜平负
    "胜": 2.09, "平": 2.86, "负": 3.32
  },
  "hhad": {              // 让球胜平负
    "让球": "-1",         // 负值=主让，正值=主受让
    "让胜": 4.65, "让平": 3.71, "让负": 1.55
  },
  "score_odds": {        // 比分赔率，key格式 "00:00"～"05:05"
    "01:00": 7.00, "00:01": 8.50, "01:01": 6.25, "02:03": 35.0
  },
  "ttg_change": {        // 总进球赔率变化
    "0球": {"count": 0, "change_pct": 0},
    "2球": {"count": 3, "change_pct": -10.8}
  },
  "had_change": {        // 胜平负变化
    "胜": {"count": 2, "change_pct": 3.2}
  },
  "hafu_change": {       // 半全场变化
    "平平": {"count": 4, "change_pct": -16.4},
    "胜胜": {"count": 2, "change_pct": 6.8}
  },
  "preview": {
    "recent": {
      "home": {          // 主队近况
        "matchList": [
          {"homeTeamFullCourtGoalCnt": 2, "awayTeamFullCourtGoalCnt": 1,
           "homeTeamShortName": "威尔士", "awayTeamShortName": "对手"}
        ]
      },
      "away": { "matchList": [...] }  // 客队近况，同上结构
    }
  }
}
```

### 2.3 实际比分 `_scores.json`

```json
{
  "周三001": {
    "match_id": "2040087",
    "home_score": 1, "away_score": 1
  }
}
```

**⚠️ key有两种**：`"周三001"` 或 `"2040087"`——遍历时检查 `v.get('match_id')` 匹配即可。

### 2.4 近况计算

```python
# 主队近5场平均总进球（双方合计）
preview = data.get('preview', {})
recent = preview.get('recent', {})
home_ml = recent.get('home', {}).get('matchList', [])  # 是list
away_ml = recent.get('away', {}).get('matchList', [])

h_form = sum(float(x['homeTeamFullCourtGoalCnt'] or 0) +
             float(x['awayTeamFullCourtGoalCnt'] or 0)
             for x in home_ml) / len(home_ml)  # 主队比赛场均总进球

a_form = sum(float(x['homeTeamFullCourtGoalCnt'] or 0) +
             float(x['awayTeamFullCourtGoalCnt'] or 0)
             for x in away_ml) / len(away_ml)  # 客队比赛场均总进球

combined_form = (h_form + a_form) / 2  # 双方平均场均总进球
```

**⚠️ critical**：近况用的是每场比赛的**双方总进球**（homeTeamFullCourtGoalCnt + awayTeamFullCourtGoalCnt），不是单队进球。这是前期踩过多次坑的定论。

---

## 三、数据过滤

```python
# 加载时过滤
import json, os

scores_map = {}
with open('分析模板/_scores.json', encoding='utf-8') as f:
    for k, v in json.load(f).items():
        if not isinstance(v, dict): continue
        mid = v.get('match_id', '')
        hs = v.get('home_score')
        aws = v.get('away_score')
        if not mid or mid == 'test' or hs is None or aws is None:
            continue
        scores_map[str(mid)] = {'total': int(hs) + int(aws),
                                'hs': int(hs), 'aws': int(aws)}

# 遍历比赛
for fname in os.listdir('sporttery_data'):
    if not fname.endswith('.json'): continue
    mid = fname.replace('.json', '')
    if not mid.isdigit(): continue     # 跳过非纯数字ID
    if mid not in scores_map: continue  # 必须有比分
    data = json.load(open(f'sporttery_data/{fname}', encoding='utf-8'))
    # 处理...
```

---

## 四、现有规则清单（避免重复）

### 4.1 R系列（历史高分比分驱动）
| 规则 | 条件 | 投注 | 全量 |
|------|------|------|------|
| **R0** | 0:0在历史高分Top2 + g0[9.5-10.5] + 平≤3.0 + 主攻<2.0 | 0球20元 | 9场3/9 ROI+238% |
| **R1** | 历史高分Top1=3:0 + 让胜<1.80 + sim3球<1 | 3:0比分20元 | 6场3/6 ROI+350% |

### 4.2 G系列（总进球赔率驱动）
| 规则 | 条件 | 投注 | 全量 |
|------|------|------|------|
| **G2** | g0=10+g2[2.9-3.1]+近况和≤3.0+平≤3.4 | 0球10元+2球20元 | 11场9/11 ROI+125% |
| **G6** | 三维排除6球=保留+g0≥18+6球≤12 | 6球20元 | 1场1/1 ROI+819% |

### 4.3 H系列（平局/闷平信号）
| 规则 | 条件 | 投注 | 全量 |
|------|------|------|------|
| **H2** | g0[11-13]+平<3.5+Top1=1:1+1:1赔尾数.25+2球大热 | 1:1比分20元 | 4场2/4 ROI+235% |
| **H3** | 三维排除独留2球+平<3.5+双方铁壁>1.0 | 1:1比分30元 | 1场1/1 ROI+570% |

### 4.4 S系列（特殊赔率模式）
| 规则 | 条件 | 投注 | 全量 |
|------|------|------|------|
| **S2** | 三维排除5球保留+s2_alert+近况≥2.5 | 5球20元 | 1场1/1 ROI+593% |
| **S3** | 三维排除6球保留+s3_alert+近况≥2.5 | 6球20元 | 4场3/4 ROI+994% |
| **S7** | g0=23+2球[4.0-4.3]+近况和≤3.0 | 2球20元 | 6场6/6 ROI+341% |
| **S8** | g0<10+平平降>17%+1:0/0:1候选 | 0:1比分30元 | 6场5/6 ROI+231% |

### 4.5 P系列（多维交叉信号）
| 规则 | 条件 | 投注 | 全量 |
|------|------|------|------|
| **P1** | g1[3.0-4.0]+g0<10+主让-1+让负[1.5-1.7]+平平降=0 | 1球30元+0:1 10元 | 10场8/10 ROI+205% |

### 4.6 X系列（三维排除残留信号）
| 规则 | 条件 | 投注 | 全量 |
|------|------|------|------|
| **X4** | 三维排除仅剩3球+4球+g0[25-35] | 4球20元 | 2场2/2 ROI+227% |
| **X6** | 客让+2:3候选+客攻>主防 | 2:3比分20元 | 2场2/2 ROI+1870% |

### 4.7 C系列（冷推博冷）
| 规则 | 条件 | 投注 | 全量 |
|------|------|------|------|
| **C1** | V3.6博冷比分+g0匹配+赔≤100+排除15-30区间 | 比分20元 | 27场10/37% ROI+597% |

---

## 五、规则设计要求

### 5.1 严密性标准
1. **条件必须可验证**：每个条件都来自明确的数据字段，不含主观判断
2. **逻辑自洽**：条件之间不矛盾，有因果关系支撑（如"警惕造热→反向投注"）
3. **阈值有依据**：每个数值阈值需标注来源（如"16场中>3.4仅1中20%"）
4. **样本量足够**：触发≥3场才考虑落地

### 5.2 投注设计
规则必须同时给出两种投注（至少一种）：

**进球数投注**：如 `bet_goals = [0, 2]`、`goal_stake = 30`

**比分投注（可选）**：如 `score_bets = [{'score': '1:1', 'stake': 20}]`

单场总投入建议控制在20-50元。

### 5.3 回测要求
每条候选规则必须附带回测结果：
```
规则名: XX
条件: [列出所有条件]
触发场次: N场
命中: M/N=XX%
总投入: XXX元
盈亏: ±XXX元
ROI: ±XX%
明细: 表格列出每场比赛的mid/日期/对阵/g0/实际比分/盈亏
```

---

## 六、执行流程

### Step 1：特征提取
为700+场每场输出结构化特征表（JSON或CSV），包含：

**赔率层**：g0~g7、HAD胜平负、让球/让胜/让平/让负  
**变化层**：总进球各球变化率、胜平负变化率、半全场平平变化率  
**近况层**：主队均总球、客队均总球、双方平均  
**推理层**：从V3.6分析获取三维排除结论（哪些球被排除/保留/警惕）、推荐进球  
**比分层**：历史高分Top3比分及赔率  
**结果层**：实际总球数、实际比分

### Step 2：网格搜索
- 对连续特征离散化（g0分区间桶、近况分区间桶等）
- 穷举2-4个特征的组合
- 筛条件：命中率>50% + 样本≥3 + ROI>0
- 按 `ROI × log(样本量)` 排序
- 去掉嵌套条件（A条件的结果子集包含B条件→保留B）

### Step 3：人工复核
- 输出Top 30候选规则
- 检查逻辑严密性、是否与现有规则冲突
- 落在代码 `ai_reasoning.py` 的 `compute_betting()` 函数中
- 优先放在G2之前（高频规则），X系列之后（低频）

---

## 七、代码集成要点

新规则添加到 `ai_reasoning.py` 中的 `compute_betting(data, analysis)` 函数里，格式：

```python
elif [触发条件]:
    rule = 'XX'  # 规则名，如 'N2'
    bet_goals = [进球数列表]  # 如 [3]
    bet_type = 'single'  # single/double
    goal_stake = 20  # 进球投注金额
    score_bets = [{'score': '2:1', 'odds': odds_val, 'stake': 10}]
```

规则名不要与现有规则重复。添加到DISABLED检查和各个豁免列表中（参考现有代码）。

---

## 八、关键注意事项

1. **所有赔率字段取值**：`float(tg.get('0球', 99))` 而不是 `float(tg.get('0球', 99) or 99)`——后者会把0当成falsy
2. **近况数据可能缺失**：始终加 `if home_ml and away_ml:` 保护
3. **让球方向**：`-1`=主让1球，`+1`=主受让1球
4. **比分key格式**：`"01:01"`（两位数:两位数），但C1规则里是 `"1:1"` 或 `"1-1"`
5. **数据文件过滤**：跳过 `full_*` 前缀的文件（用 `mid.isdigit()`）
6. **回溯测试必须包含所有700+场**，不是只跑4-5月
