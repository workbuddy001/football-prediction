import json

# 检查JSON格式
for d in ['03-12', '03-13', '03-14', '03-15', '03-16']:
    json_file = f"matches_full_2026-{d}.json"
    try:
        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)
        print(f"\n=== {d} ===")
        print(f"类型: {type(data)}")
        if isinstance(data, list):
            print(f"数量: {len(data)}")
            if len(data) > 0:
                print(f"第一项字段: {list(data[0].keys())[:10]}")
                # 找包含8的字段
                for k in data[0].keys():
                    if '8' in k.lower():
                        print(f"  8相关字段: {k} = {data[0][k]}")
    except Exception as e:
        print(f"{d}: 错误 - {e}")
