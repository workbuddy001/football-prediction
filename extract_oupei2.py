# -*- coding: utf-8 -*-
import pdfplumber

pdf_path = 'D:/work/足球/《欧赔核心思维》（全册）完整、重点标记版.pdf'

with pdfplumber.open(pdf_path) as pdf:
    # 提取更详细的内容，特别关注实盘、诱盘、平局判断
    print("=" * 80)
    print("提取欧赔核心思维的核心方法")
    print("=" * 80)

    for i in range(30, 62):  # 提取后面30页
        text = pdf.pages[i].extract_text()
        if text:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                # 提取包含关键方法的内容
                keywords = ['实盘', '诱盘', '分散', '拉低', '抬', '降水', '升水', '平赔', '胜赔', '负赔',
                           '做盘', '开盘', '思维', '信心', '分布', '区间', '位置', '中庸', '利诱', '分散力']
                if len(line) > 10 and len(line) < 100:
                    for kw in keywords:
                        if kw in line:
                            print(f'[P{i+1}] {line}')
                            break
