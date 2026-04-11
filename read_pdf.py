import pdfplumber

# 读取第一个PDF文件
pdf_path = r'D:\work\足球\《欧赔核心思维》（全册）完整、重点标记版.pdf'
try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"总页数: {len(pdf.pages)}\n")
        text = ''
        for i, page in enumerate(pdf.pages[:40]):
            page_text = page.extract_text()
            if page_text:
                text += f'\n--- 第{i+1}页 ---\n{page_text}\n'
        print(text[:15000])
except Exception as e:
    print(f'错误: {e}')
