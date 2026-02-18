@echo off
echo 正在等待MemU安装完成...
echo 请确保之前的pip安装命令已完成后再运行此脚本
echo.

echo 运行MemU + OpenClaw全面集成...
python "C:\Users\16663\Desktop\openclaw\memU\manager.py" setup
echo.

echo 集成完成！
pause