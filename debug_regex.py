# 调试正则
import re

test_str = "(1.08, 8.50, 21.00)"
# 需要匹配 1.08 这种格式 - .需要转义
odds = re.findall(r'\((\d+\.\d+),(\d+\.\d+),(\d+\.\d+)\)', test_str)
print(f"测试: {odds}")

# 测试多行
test_str2 = """
(1.08, 8.50, 21.00),  # 威**尔
(1.08, 7.00, 9.40),  # *门
"""
odds2 = re.findall(r'\((\d+\.\d+),(\d+\.\d+),(\d+\.\d+)\)', test_str2)
print(f"测试2: {odds2}")

# 修复版
odds3 = re.findall(r'\(\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*,\s*(\d+\.\d+)\s*\)', test_str2)
print(f"测试3: {odds3}")
