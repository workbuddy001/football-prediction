# -*- coding: utf-8 -*-
import re

# 读取结果文件
with open('3.21_result.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('='*90)
print('[近况差>=4的比赛分析]')
print('='*90)

# 逐行解析
for i, line in enumerate(lines):
    if line.startswith('周六') or line.startswith('周日'):
        # 提取近况差
        diff_match = re.search(r'([+-]\d+)\s+\[', line)
        if diff_match:
            form_diff = int(diff_match.group(1))
            if abs(form_diff) >= 4:
                # 提取其他信息
                parts = line.split()
                match_id = parts[0]
                
                # 对阵
                idx = line.find('vs')
                match_name = line[line.find(match_id)+len(match_id)+1:idx-1]
                
                # 赔率
                odds_match = re.search(r'(\d+\.\d+/\d+\.\d+/\d+\.\d+)', line)
                odds = odds_match.group(1) if odds_match else ''
                
                # 置信度
                conf_match = re.search(r'(\d+\.\d+)%', line)
                conf = conf_match.group(1) if conf_match else ''
                
                # 澳门
                macao_match = re.search(r'(\S+)\s+贏', line)
                macao = macao_match.group(1) if macao_match else '和局'
                
                # 预测
                pred_match = re.search(r'(主胜|客胜|和局)', line)
                pred = pred_match.group(1) if pred_match else ''
                
                # 赔率变化
                h_chg_match = re.search(r'H([+-]?\d+\.?\d*)%', line)
                d_chg_match = re.search(r'D([+-]?\d+\.?\d*)%', line)
                a_chg_match = re.search(r'A([+-]?\d+\.?\d*)%', line)
                h_chg = h_chg_match.group(1) if h_chg_match else '0'
                d_chg = d_chg_match.group(1) if d_chg_match else '0'
                a_chg = a_chg_match.group(1) if a_chg_match else '0'
                
                # 分析
                analysis_match = re.search(r'\[(.*?)\]', line)
                analysis = analysis_match.group(1) if analysis_match else ''
                
                print('\n{} {}'.format(match_id, match_name))
                print('  竞彩: {}'.format(odds))
                print('  置信度: {}% | 澳门: {} | 预测: {}'.format(conf, macao, pred))
                print('  赔率变化: H{}% D{}% A{}%'.format(h_chg, d_chg, a_chg))
                print('  近况差: {:+d}'.format(form_diff))
                print('  分析: {}'.format(analysis))
