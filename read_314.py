# -*- coding: utf-8 -*-
import pandas as pd

df = pd.read_excel('3.14_比赛预测汇总.xlsx')
print('列名:', df.columns.tolist())
print()

# 显示编号和预测结果
for idx, row in df.iterrows():
    print(f"{row.get('编号', '')}: 预测={row.get('预测结果', '')}, 实际={row.get('实际结果', '')}")
