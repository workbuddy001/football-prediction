# 检查JSON数据
import json

dates = ['03-12', '03-13', '03-14', '03-15', '03-16']

for d in dates:
    json_file = f"d:/work/workbuddy/足球预测/分析模板/matches_full_2026-{d}.json"
    try:
        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)
        print(f"{d}: {len(data)} 场比赛")
        
        # 打印第一个比赛的键名
        first_key = list(data.keys())[0]
        print(f"  键: {first_key}")
        print(f"  字段: {list(data[first_key].keys())}")
        
        # 找包含8的键
        for k in data[first_key].keys():
            if '8' in k.lower():
                print(f"  8相关: {k} = {data[first_key][k]}")
        break
    except Exception as e:
        print(f"{d}: 错误 - {e}")
