@echo off
cd /d "e:\13.兰理工读研\02.比赛文件\03.畅玩AI\02.做一个项目\06.文献检索智能体\scholar-agent\backend"
D:\Python\python312\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1
pause
