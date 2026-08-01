# 🏥 河南医疗设备招投标数据看板

从河南省政府采购网采集全省 18 地市的医疗设备招投标信息，自动过滤、分类、标注城市，通过 GitHub Pages 展示交互式看板，GitHub Actions 每周二/五自动发周报。

## 看板 & 仓库

- **在线看板**: https://wtrade2026.github.io/henan-medical-procurement/
- **GitHub 仓库**: https://github.com/Wtrade2026/henan-medical-procurement

## 核心功能

- **省网单入口爬全省**: `crawler_province.py` 一次抓取 18 地市全部公告（省网 ggcx 聚合全省）
- **智能城市标注**: `fix_city()` 四级反推（region → agency → content_url slug → channelCode），准确率 100%
- **交互看板**: 分类标签 / 设备类型 / 城市 / 日期(近1周·1月·3月) / 搜索词，可任意组合筛选
- **自动周报**: GitHub Actions 每周二/五 13:00 发送邮件 + 创建 Issue

## 项目结构

```
henan-procurement/
├── crawler_province.py      # 主爬虫（省网单入口，覆盖全省18市）
├── build_dashboard.py       # 生成 docs/index.html 看板
├── update.sh                # 一键更新（爬取→看板→推送）
├── henan_medical_full.json  # 全量数据
├── send_report.py           # 本地邮件发送（可选）
├── docs/
│   └── index.html           # 看板（GitHub Pages）
└── .github/
    ├── workflows/
    │   ├── weekly_report.yml  # 周二/五建Issue
    │   └── send_email.yml     # 周二/五发邮件
    └── scripts/
        └── create_issue.py    # Issue生成脚本
```

## 快速开始

### 一键更新数据

```bash
# 日常增量（近1周）
bash update.sh

# 仅今日
bash update.sh today

# 全量刷新（近1月）
bash update.sh month
```

### 手动爬取

```bash
# 近1周
python3 crawler_province.py 1

# 近1月
python3 crawler_province.py 2
```

### 本地预览看板

```bash
python3 build_dashboard.py   # 生成 docs/index.html
cd docs && python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
```

## 技术要点

- **数据源**: 河南省政府采购网 `zfcg.henan.gov.cn/henan/ggcx`（带验证码 ddddocr 识别）
- **翻页**: `GET ggcx?appCode=H60&pageSize=15&soCode={so}&pageNo={N}`，间隔≥5秒避限流
- **限流处理**: 命中"访问频繁"等 60-90 秒，连续 5 页失败自动停止
- **时间范围**: timeType 0=今日(省网常返回0条) 1=近1周 2=近1月

## 定时任务

| 任务 | 时间 | 方式 |
|------|------|------|
| 数据更新 | 周二/五 12:50 | crontab |
| 邮件+Issue | 周二/五 13:00 | GitHub Actions |

## 依赖

- Python 3.12+
- `requests`, `beautifulsoup4`, `ddddocr`

```bash
pip install requests beautifulsoup4 ddddocr
```

## 数据说明

- 覆盖: 郑州/开封/洛阳/平顶山/安阳/鹤壁/新乡/焦作/濮阳/许昌/漯河/三门峡/南阳/商丘/信阳/周口/驻马店/济源 + 省级
- 分类: 招标 / 中标 / 终止 / 其他
- 当前约 400+ 条活跃数据
