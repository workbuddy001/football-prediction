from pypdf import PdfReader

# 读取欧赔核心思维PDF
reader = PdfReader('分析模板/欧赔核心思维/欧赔核心思维.pdf')
print(f'总页数: {len(reader.pages)}')
print()

# 提取前30页内容（核心内容通常在前半部分）
text = ''
for i in range(min(30, len(reader.pages))):
    page = reader.pages[i]
    text += f'\n=== 第{i+1}页 ===\n'
    page_text = page.extract_text()
    if page_text:
        text += page_text[:3000]
    print(f'第{i+1}页提取完成')
    
# 保存文本
with open('d:/work/workbuddy/足球预测/oupei_core_temp.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print('\n文本已保存到 oupei_core_temp.txt')
