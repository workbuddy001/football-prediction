# 反向排除深度挖掘 — 需求文档

> 版本: v1.0 | 目标: 从"前2排除准确率81%"出发，挖掘精确比分投注规律

## 一、数据源

`a.score_candidates` 是 `v36_analyzer.analyze_match(data)` 的产出，每个元素对应一个总进球数：

```python
a['score_candidates'] = [
    {
        'total_goals': 3,
        'scores': [
            {'score': '1-2', 'tag': '🔥'},  # 最优客胜
            {'score': '0-3', 'tag': '🔥'},  
        ]
    },
    {
        'total_goals': 4,
        'scores': [
            {'score': '2-2', 'tag': '🔥'},
            {'score': '1-3', 'tag': '🔥'},
            {'score': '0-4', 'tag': '🔥'},
        ]
    },
    ...
]
```

前端显示逻辑：
- 按 `total_goals` 排序（先推荐的进球数在前）
- 每个进球数组内按 `tag` 优先（🔥 > ✅ > 其他）
- 拍平后取前2个为"排除"，第3-5个为"备选"
- 硬编码统计："回测355场:首选命中7%,前2排除准确率81%"

## 二、挖掘方向

### 方向A：特定场景下排除准确率更高

81%是全局均值。在哪些子场景下排除率显著偏离？

**可测试的子场景**：

| 场景 | 逻辑 | 预期排除率 |
|------|------|------------|
| Step0方向=大球 + 排除的2个都是大球比分 | 系统推了大球但排除大球比分 → 庄家陷阱 | ? |
| Step0方向=小球 + 排除的2个都是小球比分 | 反向 | ? |
| 0球赔率极高(≥20) + 前2排除 | 深盘冷门更不可靠 | ? |
| 近况均球<2.0 + Step0=大球 | 基本面不支持大球 | ? |
| 排除的第1个和第2个属于不同进球数 | 跨球数排除 → 信号更分散 → 排除率可能降低 | ? |
| 前2排除都是🔥标签 | vs 含✅标签 | 热度分级影响排除率？ |
| 备选比分个数≥3 | vs <3 | 备选越少排除越可靠？ |
| 联赛维度 | 日职/韩职 vs 英超/德甲 | 小球联赛里排除大球=更可靠？ |

**执行**：对每个子场景，统计 `(实际比分 NOT IN 前2排除) / 总场次`，找显著高于81%的场景。

### 方向B：备选比分的独立命中率

当前只排除了前2个，但备选（第3-5个）的独立命中率是多少？

**计算**：
- 备选比分中至少1个命中的概率
- 备选比分精确命中的概率
- 按进球数/标签/tag分层
- 备选比分作为"安全网"的ROI（投所有备选各20元）

### 方向C：排除+备选 → 精确投注规则

如果某个子场景满足：
- 前2排除率 ≥ 85%
- 备选≥2个
- 备选赔率均值在可接受范围

则可以制定规则：**投前2排除不要 + 单选备选中赔率最低的比分**。

### 方向D：比分排序机制逆向工程

`score_candidates` 内部的排序已经过 v36_analyzer 的智能处理（按让球盘过滤、攻防分析等）。前2个之所以被选为"推荐"，是因为它们通过了系统的层层筛选。但81%的概率它们不对——

**这是"系统偏见"还是"真信号"？**

- 如果是系统偏见（always picks wrong → 有系统性漏洞）
- 如果只是高分比分天然低命中（赔率高自然不中 → 无挖掘价值）

区分方法：对比"前2排除"的赔率 vs 备选的赔率。如果前2赔率显著高于备选（30x vs 10x），那81%只是高赔的天然低命中率，不是偏见。

## 三、执行脚本框架

### Step 1: 全量扫描 (`_rev_phase1_scan.py`)

```python
# 遍历所有 _scores.json 中有比分的比赛
# 对每场：加载 sporttery_data/{mid}.json + 注入 hitrate → analyze_match
# 提取 a['score_candidates']
# 拍平 allScores（前端同样逻辑）
# 记录：前2排除比分、备选比分、实际比分、是否命中(实际 NOT IN 前2)
# 同时记录场景特征：step0方向、0球赔率、近况、联赛、前2标签类型
# 输出 _rev_output/_rev_scan.csv
```

### Step 2: 特征分析 (`_rev_phase2_feature.py`)

```python
# 读 _rev_scan.csv
# 按各维度分组统计排除准确率
# 输出显著偏离全局81%的场景
# 计算备选命中率
```

### Step 3: 规则发现 (`_rev_phase3_rules.py`)

```python
# 对高区分度场景，设计投注规则
# 回测 ROI
# 输出候选规则
```

## 四、输出规范

`REVERSE_EXCLUSION_REPORT.md`

```
# 反向排除深度挖掘报告

## 1. 全局统计
- 扫描N场，前2排除准确率X%，备选命中率Y%

## 2. 子场景分析
| 场景 | 场次 | 排除率 | vs全局 | 显著性 |
|------|------|--------|--------|--------|
| ...  | ...  | ...    | +Xpp   | p=0.03 |

## 3. 候选规则
### R1: {规则名}
- 条件: {特征组合}
- 策略: 排除前2 + 投备选 {具体比分}
- 回测: N场 H命中 RI+M%
- Wilson CI: [...]

## 4. 实现建议
# 在 v36_analyzer 或 ai_reasoning 中新增规则
```

## 五、关键约束

- 不要修改任何现有 .py 文件
- 所有产出放 `_rev_output/` 目录
- 命中率期望：精确比分命中率天然<10%，不应期望>20%
- 样本>=10场才有统计讨论价值
- 比分格式注意：score_candidates 用 `1-2`（短线），`_scores.json` 用 `1:2`（冒号）
- 编码用 utf-8
- 需要 mock flask + 注入 hitrate

## 六、命中率数据注入模板

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

import sporttery_web as _sw
_sw._odds_hitrate_cache=_sw._change_hitrate_cache=None
from sporttery_web import _build_odds_hitrate, _build_change_hitrate
oh,ch=_build_odds_hitrate(),_build_change_hitrate()

# 对每场比赛
data=json.load(open(f'sporttery_data/{mid}.json'))
data['_odds_hitrate']=oh; data['_change_hitrate']=ch
a=v36_analyzer.analyze_match(data)  # 产出 score_candidates
```
