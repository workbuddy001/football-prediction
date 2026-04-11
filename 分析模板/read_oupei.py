# 读取欧赔核心思维PDF文件
from pypdf import PdfReader
import os

# 读取主要PDF文件
pdf_path = r"d:\work\workbuddy\足球预测\分析模板\欧赔核心思维\欧赔核心思维.pdf"

reader = PdfReader(pdf_path)
print(f"=== 欧赔核心思维.pdf ===")
print(f"总页数: {len(reader.pages)}\n")

# 提取前30页内容
for i, page in enumerate(reader.pages[:30]):
    text = page.extract_text()
    if text and len(text.strip()) > 50:
        print(f"--- 第{i+1}页 ---")
        print(text[:2000])
        print("\n")
