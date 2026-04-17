# -*- coding: utf-8 -*-
import json

with open('分析模板/2026.04.17/matches_enhanced_2026-04-17.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 找到墨胜利的比赛
for m in data:
    if '墨胜利' in m.get('home', '') or '纽喷' in m.get('away', ''):
        print(f"{m['match_num']}: {m['home']} vs {m['away']}")
        odds = m.get('赔率', {})
        print(f"竞彩主: {odds.get('竞彩主', 'N/A')}")
        print(f"竞彩平: {odds.get('竞彩平', 'N/A')}")
        print(f"竞彩客: {odds.get('竞彩客', 'N/A')}")
        print(f"半全胜胜: {odds.get('半全_胜胜', 'N/A')}")
        print(f"进球_0: {odds.get('进球_0', 'N/A')}")
        print(f"比分_3_1: {odds.get('比分_3_1', 'N/A')}")
        print("---所有赔率字段---")
        for k in odds.keys():
            if '半全' in k or '进球' in k or '比分' in k or '竞彩' in k:
                print(f"  {k}: {odds[k]}")
