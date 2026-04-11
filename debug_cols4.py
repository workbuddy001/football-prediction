import pandas as pd

# 读取预测数据
df = pd.read_excel('d:/work/workbuddy/足球预测/3.15_比赛预测汇总.xlsx')

print("编号列前5个:")
for i, val in enumerate(df['编号'].head()):
    print(f"  {i}: {repr(val)}")
