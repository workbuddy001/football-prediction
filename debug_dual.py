import pandas as pd

df = pd.read_excel('d:/work/workbuddy/足球预测/3.15_比赛预测汇总.xlsx')

def to_float(x):
    if isinstance(x, str):
        return float(x.replace('%', ''))
    return float(x)

df['主胜概率'] = df['主胜概率'].apply(to_float)
df['平局概率'] = df['平局概率'].apply(to_float)
df['客胜概率'] = df['客胜概率'].apply(to_float)

for idx, row in df.iterrows():
    match_id = row['编号'].split('_')[0]
    if match_id in ['周日004', '周日007', '周日012', '周日013', '周日015']:
        first_choice = str(row['首选']).strip()
        probs = {'主胜': row['主胜概率'], '平局': row['平局概率'], '客胜': row['客胜概率']}
        max_option = max(probs, key=probs.get)
        max_prob = probs[max_option]
        
        prob_list = [('主胜', row['主胜概率']), ('平局', row['平局概率']), ('客胜', row['客胜概率'])]
        prob_sorted = sorted(prob_list, key=lambda x: x[1], reverse=True)
        
        print(f"\n{match_id}:")
        print(f"  首选: {first_choice}")
        print(f"  概率: 主胜{row['主胜概率']}%, 平局{row['平局概率']}%, 客胜{row['客胜概率']}%")
        print(f"  最高: {max_option}={max_prob}%")
        print(f"  排序: {prob_sorted}")
