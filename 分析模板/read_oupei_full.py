# 读取欧赔核心思维PDF - 完整版
from pypdf import PdfReader
import os

pdf_path = r"d:\work\workbuddy\足球预测\分析模板\欧赔核心思维\欧赔核心思维.pdf"

reader = PdfReader(pdf_path)
print(f"=== 欧赔核心思维.pdf 完整版 ===")
print(f"总页数: {len(reader.pages)}\n")

# 提取所有页内容
all_text = []
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    if text:
        all_text.append(text)

# 保存到文件
with open(r"d:\work\workbuddy\足球预测\分析模板\欧赔核心思维\完整内容.txt", "w", encoding="utf-8") as f:
    f.write("\n\n==========\n\n".join(all_text))

print("内容已保存到 完整内容.txt")
print(f"\n前5000字符预览:\n")
print("\n".join(all_text[:3])[:5000])
