@echo off
chcp 65001 >nul
cd /d "C:\Users\user\Desktop\football_analytics_bot\football_analytics_bot"
python main.py --mode analyze --bankroll 1000
pause