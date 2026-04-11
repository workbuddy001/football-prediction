import pandas as pd
import json

# 读取V3预测数据
df = pd.read_excel('3.13_V3预测.xlsx')
row = df[df['编号'] == '周五004'].iloc[0]

print("V3预测文件中的数据:")
print(f"编号: {row['编号']}")
print(f"对阵: {row['对阵']}")
print(f"主胜: {row['主胜']}")
print(f"平局: {row['平局']}")
print(f"客胜: {row['客胜']}")

print("\n---")
print("源数据中的赔率对比:")

# 竞彩官方赔率（来自源数据md文件）
print("竞彩官方: 主胜5.05 平局4.30 客胜1.43")

# 主流欧赔平均值（即时）
print("主流欧赔(即时平均): 主胜约2.30 平局约3.35 客胜约2.80")

# 检查V3用的是竞彩还是欧赔
v3_home = row['主胜']
v3_draw = row['平局']
v3_away = row['客胜']

print(f"\nV3实际使用: 主胜{v3_home} 平局{v3_draw} 客胜{v3_away}")

if v3_home > 3:
    print("\n→ V3使用的是竞彩官方赔率！")
elif v3_home < 3:
    print("\n→ V3使用的是欧赔（非竞彩）！")
