import pandas as pd

# 读取预测数据
df = pd.read_excel('d:/work/workbuddy/足球预测/3.15_比赛预测汇总.xlsx')

# 转换概率列
def to_float(x):
    if isinstance(x, str):
        return float(x.replace('%', ''))
    return float(x)

df['主胜概率'] = df['主胜概率'].apply(to_float)
df['平局概率'] = df['平局概率'].apply(to_float)
df['客胜概率'] = df['客胜概率'].apply(to_float)

print("转换后列名:", df.columns.tolist())
print("\n主胜概率 dtype:", df['主胜概率'].dtype)
print("\n第一行:")
print(df.iloc[0])
print("\n主胜概率值:", df.iloc[0]['主胜概率'])
