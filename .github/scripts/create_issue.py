"""GitHub Actions 用 - 读取数据生成周报 Issue"""
import json, os
from datetime import datetime
from collections import Counter

with open("henan_medical_full.json") as f:
    data = json.load(f)

items = data["items"]
cats = Counter(d.get("category","其他") for d in items)
now = datetime.now()

def top(cat, n=6):
    seen = set()
    r = []
    for d in sorted([x for x in items if x.get("category")==cat],
                    key=lambda x: x.get("pub_time",""), reverse=True):
        iid = d.get("info_id","")
        if iid and iid not in seen:
            seen.add(iid)
            r.append(d)
        if len(r) >= n:
            break
    return r

body = f"""## 河南省医疗设备招投标周报

**{now.strftime('%Y年%m月%d日')}** · 自动生成

---

| 招标 | 中标 | 终止 | 合计 |
|---|---|---|---|
| {cats['招标']} | {cats['中标']} | {cats['终止']} | {len(items)} |

---

### 最新招标公告

| 时间 | 城市 | 标题 |
|---|---|---|
"""
for d in top("招标"):
    body += f"| {d.get('pub_time','?')[:10]} | {d.get('city','')} | [{d['title'][:60]}]({d.get('detail_url','')}) |\n"

body += "\n### 最新中标公告\n\n| 时间 | 城市 | 标题 |\n|---|---|---|\n"
for d in top("中标"):
    body += f"| {d.get('pub_time','?')[:10]} | {d.get('city','')} | [{d['title'][:60]}]({d.get('detail_url','')}) |\n"

body += "\n### 最新终止/废标\n\n| 时间 | 城市 | 标题 |\n|---|---|---|\n"
for d in top("终止"):
    body += f"| {d.get('pub_time','?')[:10]} | {d.get('city','')} | [{d['title'][:60]}]({d.get('detail_url','')}) |\n"

body += f"\n---\n\n[打开完整看板](https://wtrade2026.github.io/henan-medical-procurement/) · 每周二/周五自动更新"

# 输出给 gh 命令
title = f"河南医疗设备招投标周报 - {now.strftime('%m/%d')}"
with open("/tmp/report_title.txt", "w") as f:
    f.write(title)
with open("/tmp/report_body.md", "w", encoding="utf-8") as f:
    f.write(body)

# 创建 Issue
repo = os.environ.get("GITHUB_REPOSITORY", "Wtrade2026/henan-medical-procurement")
os.system(f'gh issue create --title "{title}" --body-file /tmp/report_body.md --label "周报" --repo {repo}')
print("Done")
