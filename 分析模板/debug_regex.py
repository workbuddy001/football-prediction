# 调试正则表达式
import re

# 读取第一行
with open('3.13_V10预测.txt', 'rb') as f:
    first_bytes = f.read(100)
    print("Bytes:", first_bytes)
    
# 用 utf-8 读取
with open('3.13_V10预测.txt', 'r', encoding='utf-8') as f:
    first_line = f.readline()
    print("First line:", repr(first_line))
    
    # 尝试不同的模式
    # 模式1: 周五001
    match1 = re.search(r'周(.?)(\d+)', first_line)
    print("Match1:", match1)
    
    # 模式2: 更通用的
    match2 = re.search(r'([周][一二三五六日零])(\d+)', first_line)
    print("Match2:", match2)
    
    # 模式3: 直接找数字编号
    match3 = re.search(r'(\d{3})', first_line)
    print("Match3:", match3)
