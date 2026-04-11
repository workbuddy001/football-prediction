from pypdf import PdfReader
import os

pdfs = [
    '分析模板/欧赔核心思维/2020年所谓欧赔核心(真正核心思维).pdf',
    '分析模板/欧赔核心思维/对欧赔核心思维分布地一些理解.pdf'
]

for pdf_path in pdfs:
    print(f"\n{'='*60}")
    print(f"读取: {pdf_path}")
    print('='*60)
    
    try:
        reader = PdfReader(pdf_path)
        print(f"总页数: {len(reader.pages)}")
        
        # 提取前25页
        text = ""
        for i in range(min(25, len(reader.pages))):
            page = reader.pages[i]
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- 第{i+1}页 ---\n"
                text += page_text[:2500]
        
        # 保存
        filename = os.path.basename(pdf_path).replace('.pdf', '.txt')
        with open(f'd:/work/workbuddy/足球预测/{filename}', 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"已保存到 {filename}")
        
    except Exception as e:
        print(f"错误: {e}")
