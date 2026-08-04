@echo off
chcp 65001 >nul
echo ========================================
echo   河南医疗设备招投标采集 — 安装依赖
echo ========================================
echo.
echo 正在安装 Python 依赖包，请稍候...
echo 如果卡住不动，按 Ctrl+C 取消后重试。
echo.

pip install -r requirements.txt

echo.
echo ========================================
echo 安装完成！现在可以进入你的文件夹
echo (person-a / person-b / person-c)
echo 双击 run.py 或输入 python run.py 运行。
echo ========================================
pause
