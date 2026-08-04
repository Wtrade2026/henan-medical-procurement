# 🏥 河南医疗设备招投标数据看板

从河南省政府采购网 + 公共资源交易中心采集全省 18 地市的医疗设备招投标信息，三人分工独立运行，自动过滤、分类、标注城市，通过 GitHub Pages 展示交互式看板。

## 看板 & 仓库

- **在线看板**: https://wtrade2026.github.io/henan-medical-procurement/
- **GitHub 仓库**: https://github.com/Wtrade2026/henan-medical-procurement

---

## 三人分工架构

| 人 | 负责范围 | 数据源类型 |
|------|----------|------------|
| **Person A** | 省级 | 省采购网 + 省公共资源交易中心 |
| **Person B** | 郑州、开封、洛阳、平顶山、安阳、鹤壁、新乡、焦作、濮阳 | 9市采购网 + 9市交易中心 |
| **Person C** | 许昌、漯河、三门峡、南阳、商丘、信阳、周口、驻马店、济源 | 9市采购网 + 9市交易中心 |

共 **38 个数据源**：19 政府采购网 + 19 公共资源交易中心。

## 项目结构

```
henan-procurement/
├── README.md                    # 本文件
├── SETUP.md                     # 安装指南（给不懂Python的同事）
├── requirements.txt             # pip install -r requirements.txt
├── install.bat                  # Windows 双击安装依赖
│
├── common/                      # 共享核心库
│   ├── captcha.py               # 政府采购网验证码识别（ddddocr）
│   ├── parser.py                # 列表页/详情页解析
│   ├── filter.py                # 医疗设备关键词过滤
│   ├── city.py                  # 城市归属五级反推
│   ├── classify.py              # 招标/中标/终止分类
│   ├── io.py                    # JSON读写合并
│   ├── trading_xinyuan.py       # 信源平台爬虫（开封/濮阳）
│   └── trading_epoint.py        # Epoint平台爬虫（省中心/周口/许昌/南阳）
│
├── person-a/                    # 同事A：省级
│   ├── config.json              # 配置文件（编辑即用）
│   ├── run.py                   # python run.py
│   └── output/                  # 输出目录
│
├── person-b/                    # 同事B：前9市
│   ├── config.json
│   ├── run.py
│   └── output/
│
├── person-c/                    # 同事C：后9市
│   ├── config.json
│   ├── run.py
│   └── output/
│
├── crawler_province.py          # [保留] 原主爬虫（省网单入口）
├── build_dashboard.py           # [保留] 生成合并看板
├── update.sh                    # [保留] 一键更新
├── docs/                        # [保留] GitHub Pages
└── .github/                     # [保留] CI/CD 定时任务
```

## 快速开始

### 初次使用（同事）

1. 下载仓库 ZIP 或 `git clone`
2. 双击 `install.bat` 安装依赖（或 `pip install -r requirements.txt`）
3. 进入你的文件夹（`person-a` / `person-b` / `person-c`）
4. 双击 `run.py` 或命令行 `python run.py`
5. 结果在 `output/` 目录

详细说明见 [SETUP.md](SETUP.md)。

### 原有主爬虫（保留可用）

```bash
# 日常增量（近1周）
bash update.sh

# 手动
python3 crawler_province.py 1    # 近1周
python3 crawler_province.py 2    # 近1月
```

### 本地预览看板

```bash
python3 build_dashboard.py
cd docs && python3 -m http.server 8080
```

## 数据源覆盖

### 政府采购网（19/19 ✅ 全部就绪）

统一平台 `{city}.zfcg.henan.gov.cn`，带验证码。

### 公共资源交易中心（5/19 ✅）

| 城市 | 平台 | 状态 |
|------|------|------|
| **省级** | Epoint | ✅ 已调通 |
| **开封** | 信源 | ✅ 已调通（4484条） |
| **周口** | Epoint | ✅ 已调通（3762条） |
| **许昌** | Epoint | ✅ 已调通（1540条） |
| **南阳** | Epoint | ✅ 已调通（858条） |
| 洛阳/安阳/焦作/三门峡/济源/郑州 | Epoint | ❌ WAF封锁 |
| 信阳/新乡 | Epoint | ⚠️ 待排查 |
| 鹤壁/平顶山/濮阳/漯河/商丘/驻马店 | 待确认 | ⚠️ 未确认平台 |

WAF 封锁的站点需浏览器环境（Selenium/Playwright），后续版本解决。

## 技术要点

- **采购网**: `zfcg.henan.gov.cn` 省网 ggcx → 验证码(ddddocr) → 翻页(间隔≥5s)
- **Epoint**: REST API `/EpointWebBuilder/rest/.../getPageInfoListNewYzm` → JSON → 免验证码(前5页)
- **信源**: `index_N.jhtml` 服务端渲染 → 无验证码 → 直接翻页
- **限流**: 命中"访问频繁"自动等待60-90秒

## 依赖

- Python 3.10+
- `requests`, `beautifulsoup4`, `ddddocr`

```bash
pip install requests beautifulsoup4 ddddocr
```

## 定时任务（原有看板）

| 任务 | 时间 | 方式 |
|------|------|------|
| 数据更新 | 周二/五 12:50 | crontab |
| 邮件+Issue | 周二/五 13:00 | GitHub Actions |

## 数据说明

- 覆盖 18 地市 + 省级，目前 468 条活跃数据
- 分类：招标 / 中标 / 终止 / 其他
