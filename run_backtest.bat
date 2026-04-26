@echo off
chcp 65001 > nul
cd /d "d:\work\workbuddy\足球预测"
python _backtest_combos.py > _backtest_results.txt 2>&1
echo 回测完成，结果已保存到 _backtest_results.txt
pause
