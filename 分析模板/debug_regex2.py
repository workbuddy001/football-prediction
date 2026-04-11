# 调试正则表达式
import re

# 用 utf-8 读取
with open('3.13_V10预测.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
for line in lines[1:10]:  # 跳过标题
    print("Line:", repr(line))
    
    # 尝试不同的模式
    # 模式1: 周五001
    match1 = re.search(r'周五(\d+)', line)
    print("  Match1 (周五):", match1)
    
    # 模式2: 周六
    match2 = re.search(r'周六(\d+)', line)
    print("  Match2 (周六):", match2)
    
    # 模式3: 直接找数字编号
    match3 = re.search(r'(\d{3})', line)
    print("  Match3 (3位数字):", match3)
