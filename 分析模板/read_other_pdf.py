# 读取其他欧赔PDF文件
from pypdf import PdfReader
import os

# 读取"对欧赔核心思维分布地一些理解"
pdf_path2 = r"d:\work\workbuddy\足球预测\分析模板\欧赔核心思维\对欧赔核心思维分布地一些理解.pdf"

try:
    reader2 = PdfReader(pdf_path2)
    print(f"=== 对欧赔核心思维分布地一些理解.pdf ===")
    print(f"总页数: {len(reader2.pages)}\n")
    
    all_text2 = []
    for i, page in enumerate(reader2.pages):
        text = page.extract_text()
        if text and len(text.strip()) > 20:
            all_text2.append(f"--- 第{i+1}页 ---\n{text}")
    
    with open(r"d:\work\workbuddy\足球预测\分析模板\欧赔核心思维\分布理解.txt", "w", encoding="utf-8") as f:
        f.write("\n\n==========\n\n".join(all_text2))
    
    print("内容已保存到 分布理解.txt")
    print("\n前3000字符预览:\n")
    print("\n".join(all_text2[:3])[:3000])
except Exception as e:
    print(f"Error: {e}")
