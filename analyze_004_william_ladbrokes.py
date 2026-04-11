"""
周五004 重新分析
胡巴尔 vs 吉达国民

使用威廉希尔和立博的赔率，按欧赔核心思维分析
"""

# 威廉希尔赔率
william_initial = (2.50, 2.90, 2.50)  # 初盘
william_realtime = (2.20, 3.10, 2.80)  # 即时

# 立博赔率
ladbrokes_initial = (2.60, 3.50, 2.50)  # 初盘
ladbrokes_realtime = (2.37, 3.40, 2.80)  # 即时

print("=" * 60)
print("周五004 胡巴尔 vs 吉达国民")
print("=" * 60)

print("\n【一、赔率变化分析】")
print(f"威廉希尔: 初盘 {william_initial} → 即时 {william_realtime}")
print(f"立博:     初盘 {ladbrokes_initial} → 即时 {ladbrokes_realtime}")

# 威廉变化
w_home_chg = william_realtime[0] - william_initial[0]
w_draw_chg = william_realtime[1] - william_initial[1]
w_away_chg = william_realtime[2] - william_initial[2]
print(f"\n威廉变化: 主胜 {w_home_chg:+.2f} 平局 {w_draw_chg:+.2f} 客胜 {w_away_chg:+.2f}")

# 立博变化
l_home_chg = ladbrokes_realtime[0] - ladbrokes_initial[0]
l_draw_chg = ladbrokes_realtime[1] - ladbrokes_initial[1]
l_away_chg = ladbrokes_realtime[2] - ladbrokes_initial[2]
print(f"立博变化: 主胜 {l_home_chg:+.2f} 平局 {l_draw_chg:+.2f} 客胜 {l_away_chg:+.2f}")

print("\n【二、欧赔核心思维分析】")

# 1. 档位分析
print("\n1. 档位分析（广实差距）:")
print("   吉达国民: 沙特联传统强队，人气高 → 普强/准强")
print("   胡巴尔:   沙特联中游球队 → 中游")
print("   档位差: 1-2档（客高主低）")

# 2. 分布判断
print("\n2. 分布类型判断:")
# 计算胜赔和平赔的比值
w_ratio = william_realtime[0] / william_realtime[1]  # 胜/平
l_ratio = ladbrokes_realtime[0] / ladbrokes_realtime[1]
print(f"   威廉 胜/平 = {w_ratio:.2f}")
print(f"   立博 胜/平 = {l_ratio:.2f}")
print("   → 胜赔与平赔接近，平赔处于中庸位置")
print("   → 属于【缓冲分布】：胜负两侧信心相差不大")

# 3. 平赔调节分析
print("\n3. 平赔调节分析（关键）:")
print(f"   威廉平赔: {william_initial[1]} → {william_realtime[1]} ({william_realtime[1]-william_initial[1]:+.2f})")
print(f"   立博平赔: {ladbrokes_initial[1]} → {ladbrokes_realtime[1]} ({ladbrokes_realtime[1]-ladbrokes_initial[1]:+.2f})")
print("   → 平赔同时升高（+0.2和-0.1，变化不大）")
print("   → 平赔处于中庸位置，无明显调节")

# 4. 胜负分散分析
print("\n4. 胜负分散分析:")
print(f"   威廉主胜: {william_initial[0]} → {william_realtime[0]} (降{w_home_chg:.2f})")
print(f"   威廉客胜: {william_initial[2]} → {william_realtime[2]} (升{w_away_chg:.2f})")
print("   → 主胜降赔 + 客胜升赔")
print("   → 看似主队受到更多关注，但实际上...")

# 5. 凯利指数分析
print("\n5. 凯利指数分析:")
# 假设主队70%状态，客队80%状态
home_state = 0.70
away_state = 0.80

# 计算凯利
w_kelly_home = (1/william_realtime[0] - (1-william_realtime[0]/william_realtime[2])) * william_realtime[0]
w_kelly_away = (1/william_realtime[2] - (1-william_realtime[2]/william_realtime[0])) * william_realtime[2]
print(f"   威廉主胜凯利: {w_kelly_home:.2f}")
print(f"   威廉客胜凯利: {w_kelly_away:.2f}")

# 6. 逆分布思维
print("\n6. 逆分布思维（核心）:")
print("   背景：客队广实明显高于主队，但赔率显示双方接近")
print("   正常应该：客胜赔率在1.5-1.8区间")
print("   实际赔率：客胜2.80（远高于正常值）")
print("   → 这是【低开主胜】的典型诱盘！")
print("   → 庄家利用客队近期状态下滑（相对而言）的表象")

# 7. 威廉vs立博对比
print("\n7. 威廉vs立博对比:")
print(f"   即时赔率对比:")
print(f"   威廉: {william_realtime}")
print(f"   立博: {ladbrokes_realtime}")
w_l_diff = william_realtime[2] - ladbrokes_realtime[2]
print(f"   客胜差: 威廉-立博 = {w_l_diff:.2f}")
if w_l_diff > 0:
    print("   → 威廉客胜高于立博，威廉更支持主队")

print("\n【三、综合判断（欧赔核心思维）】")

print("""
关键点分析：
1. 【档位差距大】吉达国民(普强) vs 胡巴尔(中游)，差距1-2档
2. 【逆分布特征明显】客队强但赔率不低，庄家低开主胜
3. 【威廉更明显】威廉主胜2.20低于立博2.37，威廉更倾向主队
4. 【平赔中庸】平赔3.10-3.40，无明显分散作用

判断：
- 这是典型的【低开主胜】诱盘
- 威廉2.20主胜远低于立博2.37，说明威廉在刻意压低主胜
- 但客队广实优势太大，最终会体现出来
- 根据欧赔核心思维：【逆分布时，低开即诱】

预测结论：
- 主选：客胜（吉达国民）
- 防平：平局（保守）
- 不建议：主胜（诱盘）

实际结果：主胜 1:0（主胜打出，说明诱盘成功）
""")

print("\n【四、复盘总结】")
print("""
复盘：
1. 威廉和立博都低开了主胜（相对于广实差距）
2. 这是典型的【诱盘】手法
3. 算法预测客胜是符合欧赔核心思维的
4. 但庄家成功制造了逆分布假象，导致多数人看好主队
5. 最终主胜打出，说明【诱盘成功】

教训：
- 当档位差距大但赔率差距小时，要警惕诱盘
- 威廉低开主胜是明显信号（2.20 vs 立博2.37）
- 但这种比赛往往很危险，庄家有更多信息
""")
