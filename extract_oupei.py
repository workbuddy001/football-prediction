# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = 'D:/work/足球/《欧赔核心思维》（全册）完整、重点标记版.pdf'

with pdfplumber.open(pdf_path) as pdf:
    print(f'总页数: {len(pdf.pages)}')
    print()

    # 提取前30页，查找重点内容
    keywords = ['赔率', '平局', '诱盘', '实盘', '冷门', '博彩', '公司', '开盘', '降水', '升水', '原理', '思维', '方法', '分散', '聚集', '任九', '特征']

    for i in range(min(30, len(pdf.pages))):
        text = pdf.pages[i].extract_text()
        if text:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 8 and len(line) < 120:
                    # 检查是否包含关键词
                    for kw in keywords:
                        if kw in line:
                            print(f'[P{i+1}] {line}')
                            break
