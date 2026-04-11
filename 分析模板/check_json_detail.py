import json

# 检查"数据分析"和"欧赔数据"字段
for d in ['03-12']:
    json_file = f"matches_full_2026-{d}.json"
    with open(json_file, encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"=== {d} ===")
    for match in data[:2]:
        print(f"\n编号: {match['编号']}")
        print(f"主队: {match['主队']} vs 客队: {match['客队']}")
        
        # 检查数据分析字段
        if '数据分析' in match:
            analysis = match['数据分析']
            print(f"数据分析字段: {type(analysis)}")
            if isinstance(analysis, dict):
                print(f"  键: {list(analysis.keys())[:10]}")
                for k in analysis.keys():
                    if '8' in str(k):
                        print(f"  8相关: {k} = {analysis[k]}")
        
        # 检查欧赔数据字段
        if '欧赔数据' in match:
            odds = match['欧赔数据']
            print(f"欧赔数据字段: {type(odds)}")
            if isinstance(odds, dict):
                print(f"  键: {list(odds.keys())[:10]}")
                for k in odds.keys():
                    if '8' in str(k):
                        print(f"  8相关: {k} = {odds[k]}")
