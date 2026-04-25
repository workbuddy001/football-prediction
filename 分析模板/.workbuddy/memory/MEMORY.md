# 长期记忆

## 爬取工具
- 高质量爬取脚本：`d:\work\workbuddy\足球预测\分析模板\fetch_325.py`（基于fetch_full_318.py改造）
- 使用方法：修改脚本顶部的 TARGET_DATE / OUT_DIR 后直接运行 `python fetch_325.py`
- 技术细节：用 data-fixtureid 属性提取比赛ID；欧赔用 klfc 属性精确提取初盘/即时；析页用 recommend 区块提取澳门推荐+走势
- 500.com页面编码：gbk（用 errors='replace' 解码）
- 比赛列表URL：https://trade.500.com/jczq/?playid=312&g=2&date=YYYY-MM-DD
- 欧赔URL：https://odds.500.com/fenxi/ouzhi-{fixture_id}.shtml
- 析页URL：https://odds.500.com/fenxi/shuju-{fixture_id}.shtml
- 生成目录格式：3.X/（如3.25/），文件名：周X00X_主队vs客队_源数据.md

## 数据格式
- 源数据md模板参考：3.24/周二001_埃门vs坎布尔_源数据.md
- 包含：基本信息、初盘赔率、即时赔率、竞彩官方赔率、变动对比、快速复制代码块
- 30家博彩公司，第3家为澳门(*门)

## 项目规律
- 每日比赛放在以日期命名的文件夹（3.08, 3.09...）
- 分析工具：赔率分析工具.py
- 有football-analysis技能可做预测分析

## 分析算法（V5 冷门联动版，已整合入football-analysis skill）
- skill路径：`C:\Users\lyx88\.workbuddy\skills\football-analysis\scripts\analyze_football.py`
- 重要：football_web.py 使用独立的 R8/R8-B 冷门检测系统，不是 skill 的 10 种冷门信号积分系统
- R8-B 检测（2026-04-12新增）：澳门推荐和局+和局赔率升/平+其他方向降赔 → 反向冷门预警
- 分析脚本：`d:\work\workbuddy\足球预测\分析模板\analyze_v5_cold.py`
- 核心改进：**冷门预警与投注建议联动**，不再脱节
- 冷门信号（共10种，积分制）：
  ① 澳门推荐和局+主队赔率升+客胜概率高 → +3分
  ② 澳门推荐和局+三项均衡 → +2分
  ③ 主队近况极差(W<=L, W<=1) → +2分
  ④ 客队近况极差(W<=L, W<=1) → +2分
  ⑤ 主队热度骤降(升赔公司>50%且均值>10%+客队受保护) → +3分
  ⑥ 客队赔率下降但近况极差无法支撑 → +2分
  ⑦ 市场剧烈分歧(主升>60%+客升>30%) → +2分
  ⑧ 主客同时被大额资金 → +4分
  ⑨ 澳门客胜从初盘大幅上升 → +2分
  ⑩ 澳门推荐和局+主客近况接近 → +2分
- 冷门分级：0分=无，1-3=低，4-6=中，7+=高
- 联动规则：
  - 冷门>=6分(高危)：降1星，强制给出双选建议
  - 冷门3-5分(中危)：降1星，给出双选建议
  - 冷门1-2分(低危)：维持星级，附加注意提示
- 使用：`python analyze_v5_cold.py <文件夹路径>`
- PowerShell需设置编码：`$env:PYTHONIOENCODING="utf-8"; python analyze_v5_cold.py ...`
