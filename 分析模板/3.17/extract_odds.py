# -*- coding: utf-8 -*-
"""批量提取3.17比赛赔率数据"""

import re
import os
import glob

BASE_DIR = r"D:\work\workbuddy\足球预测\分析模板\3.17"

def extract_field(text, field_name):
    pattern = rf'\|\s*{re.escape(field_name)}\s*\|\s*(.*?)\s*\|'
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""

def parse_odds_list(text, section_keyword):
    section_pattern = rf'## {re.escape(section_keyword)}.*?```python(.*?)```'
    m = re.search(section_pattern, text, re.DOTALL)
    if not m:
        return []
    code_block = m.group(1)
    results = []
    line_pattern = r'\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)\s*,\s*#(.*)'
    for lm in re.finditer(line_pattern, code_block):
        h, d, a = float(lm.group(1)), float(lm.group(2)), float(lm.group(3))
        name = lm.group(4).strip()
        results.append((h, d, a, name))
    return results

def get_jingcai(odds_list):
    if not odds_list:
        return None
    for item in odds_list:
        if '官' in item[3]:
            return (item[0], item[1], item[2])
    return (odds_list[0][0], odds_list[0][1], odds_list[0][2])

def get_macao(odds_list):
    if not odds_list:
        return None
    for item in odds_list:
        name = item[3].strip()
        if re.search(r'^\*{1,2}门$', name):
            return (item[0], item[1], item[2])
    if len(odds_list) > 2:
        return (odds_list[2][0], odds_list[2][1], odds_list[2][2])
    return None

def parse_macao_dir(text, home, away):
    tip = extract_field(text, "澳门推荐")
    if not tip or tip in ("待补充", ""):
        return "未知"
    
    if "平" in tip and "贏" not in tip and "赢" not in tip:
        return "平"
    
    team = tip.replace("赢", "").replace("贏", "").strip()
    if not team:
        return "未知"
    
    # Try to match home or away
    for h_alias in [home, home[:2], home[:3]]:
        if h_alias and h_alias in team and len(h_alias) >= 2:
            return "主"
    for a_alias in [away, away[:2], away[:3]]:
        if a_alias and a_alias in team and len(a_alias) >= 2:
            return "客"
    
    # Special mappings for common variants
    mapping = {
        "悉尼FC": ["悉尼"],
        "中国女": ["中国"],
        "澳大利女": ["澳洲", "澳大利亚"],
        "金泉尚武": ["金泉"],
        "光州FC": ["光州"],
        "阿森纳": ["阿仙奴", "枪手"],
        "切尔西": ["车路士"],
        "曼城": ["曼城"],
        "热刺": ["托特纳姆", "热刺"],
        "马竞": ["马德里竞技", "马体会"],
        "巴萨": ["巴塞罗那", "巴塞隆拿"],
        "拜仁": ["拜仁慕尼黑", "拜仁"],
        "利物浦": ["利物浦"],
        "韩国女": ["韩国"],
        "日本女": ["日本"],
        "大阪樱花": ["大阪樱花"],
        "名古屋鲸": ["名古屋"],
        "浦项制铁": ["浦项"],
        "全北现代": ["全北"],
        "纽卡斯尔": ["纽卡素"],
        "亚特兰大": ["亚特兰大"],
        "加拉塔萨": ["加拉塔萨雷"],
        "勒沃库森": ["利华古逊"],
        "巴黎圣曼": ["巴黎圣日耳曼", "巴黎"],
        "皇马": ["皇家马德里"],
        "博德闪耀": ["博德"],
        "里斯本": ["里斯本竞技", "宾菲加", "里斯本"],
        "沃特福德": ["窝特福德"],
        "雷克斯": ["雷克斯"],
    }
    
    for key, aliases in mapping.items():
        if key == home:
            for a in aliases:
                if a in team or team in a:
                    return "主"
        if key == away:
            for a in aliases:
                if a in team or team in a:
                    return "客"
    
    return "未知"

def calc_pct(init, real):
    if init == 0:
        return 0.0
    return (real - init) / init * 100

def fmt_pct(val):
    if abs(val) < 0.05:
        return "—"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}%"

def classify_pattern(init, real):
    changes = []
    if real[0] < init[0]: changes.append("H")
    if real[1] < init[1]: changes.append("D")
    if real[2] < init[2]: changes.append("A")
    
    if real[0] == init[0] and real[1] == init[1] and real[2] == init[2]:
        return "全不动"
    if len(changes) == 0:
        return "全升赔"
    if len(changes) == 1:
        return f"单出口({changes[0]})"
    if len(changes) == 2:
        return f"双出口({'+'.join(changes)})"
    return "三降赔"

def classify_interaction(jc_i, jc_r, mc_i, mc_r):
    if any(v is None for v in [jc_i, jc_r, mc_i, mc_r]):
        return "—"
    
    def d(i, r):
        if r < i: return "↓"
        if r > i: return "↑"
        return "—"
    
    patterns = []
    for label, ji, jr, mi, mr in [("H", jc_i[0], jc_r[0], mc_i[0], mc_r[0]),
                                     ("D", jc_i[1], jc_r[1], mc_i[1], mc_r[1]),
                                     ("A", jc_i[2], jc_r[2], mc_i[2], mc_r[2])]:
        jd, md = d(ji, jr), d(mi, mr)
        if jd == md and jd != "—":
            patterns.append(f"{label}同{jd}")
        elif jd != md:
            patterns.append(f"{label}异({jd}/{md})")
    
    if not patterns:
        return "双方全不动"
    return "，".join(patterns)

# Find all source data files
files_tue = sorted(glob.glob(os.path.join(BASE_DIR, "周二*源数据.md")))
files_wed = sorted(glob.glob(os.path.join(BASE_DIR, "周三*源数据.md")))
all_files = files_tue + files_wed

print(f"找到 {len(all_files)} 个源数据文件")

results = []
for fp in all_files:
    with open(fp, "r", encoding="utf-8") as f:
        text = f.read()
    
    fname = os.path.basename(fp)
    mid = re.search(r'(周二\d+|周三\d+)', fname)
    mid = mid.group(1) if mid else "?"
    
    league = extract_field(text, "赛事")
    home = extract_field(text, "主队")
    away = extract_field(text, "客队")
    home_form = extract_field(text, "主队近况走势") or "—"
    away_form = extract_field(text, "客队近况走势") or "—"
    macao_tip = extract_field(text, "澳门推荐")
    macao_dir = parse_macao_dir(text, home, away)
    
    init_list = parse_odds_list(text, "二、初盘赔率")
    real_list = parse_odds_list(text, "三、即时赔率")
    
    jc_i = get_jingcai(init_list)
    jc_r = get_jingcai(real_list)
    mc_i = get_macao(init_list)
    mc_r = get_macao(real_list)
    
    r = {"mid": mid, "league": league, "home": home, "away": away,
         "home_form": home_form, "away_form": away_form,
         "macao_tip": macao_tip, "macao_dir": macao_dir}
    
    if jc_i and jc_r:
        r["jc_init"] = jc_i
        r["jc_real"] = jc_r
        r["jc_hp"] = calc_pct(jc_i[0], jc_r[0])
        r["jc_dp"] = calc_pct(jc_i[1], jc_r[1])
        r["jc_ap"] = calc_pct(jc_i[2], jc_r[2])
        r["jc_pattern"] = classify_pattern(jc_i, jc_r)
    else:
        for k in ["jc_init", "jc_real", "jc_hp", "jc_dp", "jc_ap", "jc_pattern"]:
            r[k] = None
    
    if mc_i and mc_r:
        r["mc_init"] = mc_i
        r["mc_real"] = mc_r
        r["mc_hp"] = calc_pct(mc_i[0], mc_r[0])
        r["mc_dp"] = calc_pct(mc_i[1], mc_r[1])
        r["mc_ap"] = calc_pct(mc_i[2], mc_r[2])
    else:
        for k in ["mc_init", "mc_real", "mc_hp", "mc_dp", "mc_ap"]:
            r[k] = None
    
    if jc_i and jc_r and mc_i and mc_r:
        r["interaction"] = classify_interaction(jc_i, jc_r, mc_i, mc_r)
    else:
        r["interaction"] = "—"
    
    # Heart odds
    if macao_dir == "主" and jc_r:
        r["heart_odds"] = jc_r[0]
    elif macao_dir == "平" and jc_r:
        r["heart_odds"] = jc_r[1]
    elif macao_dir == "客" and jc_r:
        r["heart_odds"] = jc_r[2]
    else:
        r["heart_odds"] = None
    
    results.append(r)
    print(f"  OK {mid} {home} vs {away} | {league} | heart:{macao_dir}")

# Output
out = os.path.join(BASE_DIR, "赔率汇总.md")
lines = []
lines.append("# 3.17 赔率数据汇总\n")
lines.append(f"> 共 {len(results)} 场比赛（周二{len(files_tue)}场 + 周三{len(files_wed)}场）\n")

lines.append("## 一、基本信息\n")
lines.append("| 编号 | 赛事 | 主队 | 客队 | 主走势 | 客走势 | 澳门推荐 | 心水 | 心水竞彩即时赔 |")
lines.append("|------|------|------|------|--------|--------|----------|------|--------------|")
for r in results:
    ho = f"{r['heart_odds']:.2f}" if r['heart_odds'] else "—"
    lines.append(f"| {r['mid']} | {r['league']} | {r['home']} | {r['away']} | "
                 f"{r['home_form']} | {r['away_form']} | {r['macao_tip']} | "
                 f"{r['macao_dir']} | {ho} |")

lines.append("\n## 二、竞彩赔率变化\n")
lines.append("| 编号 | 对阵 | 初盘 | 即时 | 主% | 平% | 客% | 格局 |")
lines.append("|------|------|------|------|-----|-----|-----|------|")
for r in results:
    if r.get("jc_init") and r.get("jc_real"):
        ji = r["jc_init"]
        jr = r["jc_real"]
        lines.append(f"| {r['mid']} | {r['home']}vs{r['away']} | "
                     f"{ji[0]:.2f}/{ji[1]:.2f}/{ji[2]:.2f} | "
                     f"{jr[0]:.2f}/{jr[1]:.2f}/{jr[2]:.2f} | "
                     f"{fmt_pct(r['jc_hp'])} | {fmt_pct(r['jc_dp'])} | {fmt_pct(r['jc_ap'])} | "
                     f"{r['jc_pattern']} |")
    else:
        lines.append(f"| {r['mid']} | {r['home']}vs{r['away']} | — | — | — | — | — | — |")

lines.append("\n## 三、澳门赔率变化\n")
lines.append("| 编号 | 对阵 | 初盘 | 即时 | 主% | 平% | 客% |")
lines.append("|------|------|------|------|-----|-----|-----|")
for r in results:
    if r.get("mc_init") and r.get("mc_real"):
        mi = r["mc_init"]
        mr = r["mc_real"]
        lines.append(f"| {r['mid']} | {r['home']}vs{r['away']} | "
                     f"{mi[0]:.2f}/{mi[1]:.2f}/{mi[2]:.2f} | "
                     f"{mr[0]:.2f}/{mr[1]:.2f}/{mr[2]:.2f} | "
                     f"{fmt_pct(r['mc_hp'])} | {fmt_pct(r['mc_dp'])} | {fmt_pct(r['mc_ap'])} |")
    else:
        lines.append(f"| {r['mid']} | {r['home']}vs{r['away']} | — | — | — | — | — |")

lines.append("\n## 四、竞彩×澳门互动\n")
lines.append("| 编号 | 对阵 | 心水 | 心水赔率 | 竞彩格局 | 互动模式 |")
lines.append("|------|------|------|---------|---------|---------|")
for r in results:
    ho = f"{r['heart_odds']:.2f}" if r['heart_odds'] else "—"
    lines.append(f"| {r['mid']} | {r['home']}vs{r['away']} | "
                 f"{r['macao_dir']} | {ho} | "
                 f"{r.get('jc_pattern', '—')} | {r['interaction']} |")

with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\nDone! Output: {out}")
