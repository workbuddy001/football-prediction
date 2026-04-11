"""
gen_source_md.py
从 matches_full_*.json 读取所有比赛，按照源数据模板.md格式
为每场生成一个独立的 md 文件，输出到指定目录。
"""

import json
import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def arrow(init_val, real_val):
    """赔率变动方向箭头"""
    try:
        i, r = float(init_val), float(real_val)
        if r < i:
            return "↓"
        elif r > i:
            return "↑"
        else:
            return "—"
    except Exception:
        return "—"


def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def build_odds_block(oz_list, label):
    """生成初盘/即时赔率 Python 代码块"""
    lines = []
    for idx, co in enumerate(oz_list):
        name = co.get("公司", f"公司{idx+1}")
        w = co.get(f"{label}胜", "")
        d = co.get(f"{label}平", "")
        l = co.get(f"{label}负", "")
        if not w:
            continue
        lines.append(f"    ({w}, {d}, {l}),  # {name}")
    return "\n".join(lines)


def build_change_table(oz_list):
    """生成赔率变动对比表"""
    header = "| 公司 | 初盘胜 | 即时胜 | 变动 | 初盘平 | 即时平 | 变动 | 初盘负 | 即时负 | 变动 |"
    sep    = "|------|--------|--------|------|--------|--------|------|--------|--------|------|"
    rows = [header, sep]
    for co in oz_list:
        name = co.get("公司", "")
        ih = co.get("初盘胜", ""); rh = co.get("即时胜", "")
        id_ = co.get("初盘平", ""); rd = co.get("即时平", "")
        ia = co.get("初盘负", ""); ra = co.get("即时负", "")
        rows.append(
            f"| {name} | {ih} | {rh} | {arrow(ih, rh)} | "
            f"{id_} | {rd} | {arrow(id_, rd)} | "
            f"{ia} | {ra} | {arrow(ia, ra)} |"
        )
    return "\n".join(rows)


def build_quick_copy(match):
    """生成第六节：快速复制到分析工具"""
    info  = match.get("数据分析", {})
    oz    = match.get("欧赔数据", {}).get("欧赔列表", [])
    home  = match.get("主队", "")
    away  = match.get("客队", "")
    date  = match.get("日期", "")
    time_ = match.get("时间", "")
    league= match.get("联赛", "")

    home_form = info.get("主队近况走势", "待补充")
    away_form = info.get("客队近况走势", "待补充")
    home_pan  = info.get("主队盘路走势", "待补充")
    away_pan  = info.get("客队盘路走势", "待补充")
    history   = info.get("交战历史摘要", info.get("历史交锋", "待补充"))
    macao_tip = info.get("澳门推荐", "待补充")

    init_lines = []
    real_lines = []
    for co in oz:
        name = co.get("公司", "")
        ih = co.get("初盘胜", ""); id_ = co.get("初盘平", ""); ia = co.get("初盘负", "")
        rh = co.get("即时胜", ""); rd = co.get("即时平", ""); ra = co.get("即时负", "")
        if ih:
            init_lines.append(f"        ({ih}, {id_}, {ia}),  # {name}")
        if rh:
            real_lines.append(f"        ({rh}, {rd}, {ra}),  # {name}")

    return f"""## 六、快速复制到分析工具

```python
if __name__ == "__main__":

    # 比赛信息
    home_team     = "{home}"
    away_team     = "{away}"
    match_time    = "{date} {time_}"
    league        = "{league}"
    home_form     = "{home_form}"
    away_form     = "{away_form}"
    home_handicap = "{home_pan}"
    away_handicap = "{away_pan}"
    history       = "{history}"
    macao_tip     = "{macao_tip}"

    initial_odds = [
{chr(10).join(init_lines)}
    ]

    realtime_odds = [
{chr(10).join(real_lines)}
    ]
```"""


def generate_md(match):
    """生成完整源数据 md"""
    info   = match.get("数据分析", {})
    oz_raw = match.get("欧赔数据", {}).get("欧赔列表", [])
    spf    = match.get("竞彩胜平负赔率", {})

    home   = match.get("主队", "")
    away   = match.get("客队", "")
    date_  = match.get("日期", "")
    time_  = match.get("时间", "")
    league = match.get("联赛", "")
    num    = match.get("编号", "")
    rangqiu= match.get("让球", "")

    home_form = info.get("主队近况走势", "待补充")
    away_form = info.get("客队近况走势", "待补充")
    home_pan  = info.get("主队盘路走势", "待补充")
    away_pan  = info.get("客队盘路走势", "待补充")
    history   = info.get("历史交锋", info.get("交战历史摘要", "待补充"))
    macao_tip = info.get("澳门推荐", "待补充")
    macao_ana = info.get("澳门分析", "")
    home_rec  = info.get("主队近况", "")
    away_rec  = info.get("客队近况", "")

    # 近期交战记录表格
    his_rows = info.get("近期交战记录", [])
    his_table = ""
    if his_rows:
        his_table = (
            "\n### 近期交战记录（析页）\n\n"
            "| 赛事 | 日期 | 主队 | 比分 | 客队 | 让球线 | 盘口 |\n"
            "|------|------|------|------|------|--------|------|\n"
        )
        for row in his_rows:
            cols = [c.strip() for c in row.split("|")]
            # 补齐到7列
            while len(cols) < 7:
                cols.append("")
            his_table += "| " + " | ".join(cols[:7]) + " |\n"

    n_companies = len(oz_raw)

    # ── 初盘 / 即时 赔率代码块 ──────────────────────────────────
    init_block = build_odds_block(oz_raw, "初盘")
    real_block = build_odds_block(oz_raw, "即时")

    # ── 赔率变动表 ────────────────────────────────────────────
    change_table = build_change_table(oz_raw)

    # ── 趋势总结 ──────────────────────────────────────────────
    if oz_raw:
        h_down = sum(1 for c in oz_raw if safe_float(c.get("即时胜","")) < safe_float(c.get("初盘胜","")))
        d_up   = sum(1 for c in oz_raw if safe_float(c.get("即时平","")) > safe_float(c.get("初盘平","")))
        a_up   = sum(1 for c in oz_raw if safe_float(c.get("即时负","")) > safe_float(c.get("初盘负","")))
        trend_note = (
            f"> **趋势总结**：{h_down}/{n_companies}家主胜降赔，"
            f"{d_up}/{n_companies}家平局升赔，"
            f"{a_up}/{n_companies}家客胜升赔。"
        )
    else:
        trend_note = "> **趋势总结**：暂无欧赔数据。"

    quick_copy = build_quick_copy(match)

    md = f"""# 赔率分析源数据

> 数据来源：500.com 竞彩足球 | 编号：{num} | 采集日期：{date_}

---

## 一、比赛基本信息

| 字段 | 内容 |
|------|------|
| 主队 | {home} |
| 客队 | {away} |
| 比赛时间 | {date_} {time_} |
| 赛事 | {league} |
| 让球 | {rangqiu} |
| 主队近况 | {home_rec} |
| 客队近况 | {away_rec} |
| 主队近况走势 | {home_form} |
| 主队盘路走势 | {home_pan} |
| 客队近况走势 | {away_form} |
| 客队盘路走势 | {away_pan} |
| 历史交锋 | {history} |
| 澳门推荐 | {macao_tip} |
| 澳门分析 | {macao_ana} |
{his_table}
---

## 二、初盘赔率（共{n_companies}家公司）

```python
initial_odds = [
    # 格式: (主胜, 平局, 客胜)  # 公司名
{init_block}
]
```

---

## 三、即时赔率（共{n_companies}家公司）

```python
realtime_odds = [
    # 格式: (主胜, 平局, 客胜)  # 公司名
{real_block}
]
```

---

## 四、竞彩胜平负赔率（500.com官方）

| 结果 | 赔率 |
|------|------|
| 主胜（{home}赢） | {spf.get("胜", "N/A")} |
| 平局 | {spf.get("平", "N/A")} |
| 客胜（{away}赢） | {spf.get("负", "N/A")} |

---

## 五、赔率变动对比（初盘 → 即时）

{change_table}

{trend_note}

---

{quick_copy}
"""
    return md


def main():
    # 参数：输入json路径，输出目录
    if len(sys.argv) >= 3:
        json_path  = sys.argv[1]
        output_dir = sys.argv[2]
    else:
        json_path  = os.path.join(BASE_DIR, "matches_full_2026-03-15.json")
        output_dir = os.path.join(BASE_DIR, "3.15")

    if not os.path.exists(json_path):
        print(f"[ERROR] 找不到数据文件: {json_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    with open(json_path, "r", encoding="utf-8") as f:
        matches = json.load(f)

    print(f"共 {len(matches)} 场比赛，输出到: {output_dir}")

    for match in matches:
        home = match.get("主队", "主队")
        away = match.get("客队", "客队")
        num  = match.get("编号", "000")
        # 文件名中去掉非法字符
        safe_name = re.sub(r'[\\/*?:"<>|]', '_', f"{num}_{home}vs{away}_源数据.md")
        out_path = os.path.join(output_dir, safe_name)

        md_content = generate_md(match)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"  [OK] {safe_name}")

    print(f"\n全部完成，共生成 {len(matches)} 个文件。")


if __name__ == "__main__":
    main()
