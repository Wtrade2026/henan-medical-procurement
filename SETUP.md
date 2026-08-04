# 河南医疗设备招投标采集 — 分发与安装指南

## 如何分发给同事（Wayne 操作）

```bash
cd ~/projects/henan-procurement
python3 pack.py
```

`dist/` 目录下生成三个 ZIP：
- `person-a.zip` → 发给负责省级的同事
- `person-b.zip` → 发给负责北9市的同事  
- `person-c.zip` → 发给负责南9市的同事

> 每次更新代码后重新打一次包即可。

---

## 同事安装与使用

### 第一次使用

1. 解压收到的 ZIP 文件到任意位置（如桌面）
2. 进入你的文件夹（`person-a` / `person-b` / `person-c`）
3. 双击 **`一键运行.bat`**
4. 第一次会提示安装依赖（需联网，约 2 分钟），之后每次直接跑
5. 等待 15-30 分钟（具体看数据量）
6. 完成后进入 `output/` 文件夹，双击 `index.html` 查看结果

### 之后每次使用

双击 **`一键运行.bat`** 即可。

---

## 常见问题

### 提示 "python 不是内部命令"
Python 没装或者没勾选 "Add Python to PATH"。
→ 去 https://www.python.org/downloads/ 下载安装，**务必勾选 Add Python to PATH**

### 提示 "pip 不是内部命令"
同上，重新安装 Python 并勾选 PATH。

### "访问频繁" 或等待很久
正常现象，程序会自动等待，不要手动关闭。

### 运行到一半断了
重新双击 `一键运行.bat` 即可，之前的数据会保留。

### 需要代理吗？
如果在公司内网，可能需要代理。联系 Wayne。

---

## 文件结构（了解即可）

```
你的文件夹/
├── 一键运行.bat      ← 双击运行
├── 使用说明.txt
├── run.py             ← 主程序
├── config.json        ← 配置文件（一般不用改）
└── output/
    ├── person-x.json   ← 原始数据
    └── index.html      ← 看板（双击查看）
```
