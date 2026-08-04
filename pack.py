#!/usr/bin/env python3
"""打包脚本 — 为每人生成独立安装包（ZIP）"""
import os, shutil, zipfile, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(SCRIPT_DIR, "dist")
PERSONS = ["person-a", "person-b", "person-c"]

# 每人需要的公共文件
COMMON_FILES = [
    "common/__init__.py",
    "common/city.py",
    "common/filter.py",
    "common/captcha.py",
    "common/parser.py",
    "common/classify.py",
    "common/io.py",
    "common/trading_xinyuan.py",
    "common/trading_epoint.py",
    "common/dashboard.py",
    "requirements.txt",
]

def pack(person):
    os.makedirs(DIST_DIR, exist_ok=True)
    person_dir = os.path.join(SCRIPT_DIR, person)
    tmp = os.path.join(DIST_DIR, f"{person}_tmp")

    # 清理临时目录
    if os.path.exists(tmp):
        shutil.rmtree(tmp)

    # 复制 common/
    common_dst = os.path.join(tmp, "common")
    os.makedirs(common_dst)
    for f in COMMON_FILES:
        src = os.path.join(SCRIPT_DIR, f)
        dst = os.path.join(tmp, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    # 复制 person 目录（保留 output 目录但不保留旧数据）
    person_dst = os.path.join(tmp, person)
    shutil.copytree(person_dir, person_dst)

    # 写一个简单的安装+运行脚本
    bat_path = os.path.join(tmp, person, "一键运行.bat")
    with open(bat_path, "w", encoding="gbk") as f:
        f.write(f'''@echo off
chcp 65001 >nul
title 河南医疗招投标采集 - {person}
cd /d "%~dp0..\\.."
echo ========================================
echo   河南医疗设备招投标采集 - {person}
echo ========================================
echo.
echo [1/2] 检查并安装依赖...
pip install -r requirements.txt --quiet
echo.
echo [2/2] 开始采集数据...
cd /d "%~dp0"
python run.py
echo.
pause
''')

    # 写一个简短说明
    readme_path = os.path.join(tmp, person, "使用说明.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"""河南医疗设备招投标采集 - {person}
====================================

首次使用：
  1. 双击 "一键运行.bat"
  2. 第一次会自动安装依赖（需联网，约2分钟）
  3. 之后每次双击即可运行

采集时间：
  运行约需 15-30 分钟，请耐心等待

查看结果：
  output/ 文件夹 → index.html 双击查看看板

问题联系：Wayne
""")

    # 打包 ZIP
    zip_name = f"{person}.zip"
    zip_path = os.path.join(DIST_DIR, zip_name)
    if os.path.exists(zip_path):
        os.remove(zip_path)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(tmp):
            for file in files:
                full = os.path.join(root, file)
                arcname = os.path.relpath(full, tmp)
                zf.write(full, arcname)

    # 清理临时目录
    shutil.rmtree(tmp)

    size_mb = os.path.getsize(zip_path) / 1024 / 1024
    print(f"  {zip_name}: {size_mb:.1f} MB")
    return zip_path


def main():
    print("打包中...\n")
    os.makedirs(DIST_DIR, exist_ok=True)
    for person in PERSONS:
        pack(person)
    print(f"\n✅ 完成 → {DIST_DIR}/")

if __name__ == "__main__":
    main()
