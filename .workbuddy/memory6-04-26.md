
    
## 让球新规律添加（2026-04-26 上午）
### 新规律1：让胜<1.7 + 让平>=3.7 + 客队近况好 → 让胜
- 置信度：84.6% (11/13)
- 代码位置：sporttery_web.py _analyze_hhad_low_draw() Step 1.5

### 新规律2：让胜1.7-2.0 + 让平3.3-3.7 + 客远好 → 让胜
- 置信度：77.8% (7/9)
- 代码位置：sporttery_web.py _analyze_hhad_low_draw() Step 1.5

### 代码修改
- 添加触发条件：is_law1, is_law2
- 添加判断逻辑：Step 1.5
- 返回值添加：is_law1, is_law2
- 前端显示：通过hints列表显示（待优化为醒目显示）
- Git commit: 8d8d156
