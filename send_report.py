#!/usr/bin/env python3
"""发送医疗设备招投标周报邮件"""
import smtplib, json, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "henan_medical_full.json")
PASSWORD_FILE = os.path.join(SCRIPT_DIR, ".email_password")

# 配置
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
FROM_EMAIL = "wayne.wtrade@gmail.com"
TO_EMAIL = "wayne.wtrade@gmail.com"


def load_password():
    if not os.path.exists(PASSWORD_FILE):
        raise FileNotFoundError(f"请创建 {PASSWORD_FILE} 文件，内容为 Gmail App Password")
    with open(PASSWORD_FILE) as f:
        return f.read().strip()


def generate_report():
    with open(DATA_FILE) as f:
        data = json.load(f)

    items = data["items"]
    now = datetime.now()

    # 本周数据 (周一至今)
    today = now.strftime("%Y-%m-%d")
    cats = Counter(d.get("category", "其他") for d in items)
    cities = Counter(d.get("city", "未知") for d in items)
    types = Counter(d.get("announce_type", "未知") for d in items)

    # 最新10条招标
    zhaobiao = [d for d in items if d.get("category") == "招标"]
    zhaobiao.sort(key=lambda x: x.get("pub_time", ""), reverse=True)

    # 最新10条中标
    zhongbiao = [d for d in items if d.get("category") == "中标"]
    zhongbiao.sort(key=lambda x: x.get("pub_time", ""), reverse=True)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{{font-family:sans-serif;font-size:14px;color:#333;max-width:700px;margin:0 auto;}}
h2{{color:#1a73e8;border-bottom:2px solid #1a73e8;padding-bottom:8px;}}
.stats{{display:flex;gap:12px;margin:16px 0;}}
.stat{{flex:1;text-align:center;padding:12px;border-radius:8px;background:#f5f5f5;}}
.stat .n{{font-size:24px;font-weight:bold;}}
.stat .l{{font-size:12px;color:#888;}}
.zhaobiao .n{{color:#1a73e8;}}
.zhongbiao .n{{color:#0d904f;}}
.zhongzhi .n{{color:#d93025;}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin:8px 0;}}
th{{background:#f5f5f5;padding:6px 8px;text-align:left;}}
td{{padding:6px 8px;border-bottom:1px solid #eee;}}
td a{{color:#1a73e8;text-decoration:none;}}
.badge{{display:inline-block;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:bold;}}
.b.zhaobiao{{background:#e3f0ff;color:#1a73e8;}}
.b.zhongbiao{{background:#e6f4ea;color:#0d904f;}}
.b.zhongzhi{{background:#fce8e6;color:#d93025;}}
.footer{{color:#999;font-size:11px;margin-top:24px;border-top:1px solid #eee;padding-top:12px;}}
</style></head><body>
<h2>🏥 河南省医疗设备招投标周报</h2>
<p>{now.strftime("%Y年%m月%d日 %H:%M")} 更新 · 覆盖9个地级市</p>

<div class="stats">
<div class="stat zhaobiao"><div class="n">{cats["招标"]}</div><div class="l">🟢 招标</div></div>
<div class="stat zhongbiao"><div class="n">{cats["中标"]}</div><div class="l">🔵 中标</div></div>
<div class="stat zhongzhi"><div class="n">{cats["终止"]}</div><div class="l">🔴 终止</div></div>
<div class="stat"><div class="n">{len(items)}</div><div class="l">📊 合计</div></div>
</div>

<h3>📋 最新招标公告</h3>
<table>
<tr><th>时间</th><th>城市</th><th>标题</th></tr>
"""
    for d in zhaobiao[:10]:
        html += f'<tr><td style="white-space:nowrap">{d.get("pub_time","?")[:10]}</td><td>{d.get("city","")}</td><td><a href="{d.get("detail_url","")}">{d["title"][:70]}</a></td></tr>\n'

    html += """</table>

<h3>🏆 最新中标公告</h3>
<table>
<tr><th>时间</th><th>城市</th><th>标题</th></tr>
"""
    for d in zhongbiao[:10]:
        html += f'<tr><td style="white-space:nowrap">{d.get("pub_time","?")[:10]}</td><td>{d.get("city","")}</td><td><a href="{d.get("detail_url","")}">{d["title"][:70]}</a></td></tr>\n'

    html += f"""</table>

<div class="footer">
<p>📊 看板: <a href="https://wtrade2026.github.io/henan-medical-procurement/">https://wtrade2026.github.io/henan-medical-procurement/</a></p>
<p>自动生成 · 下次发送: 每周二/周五 13:00</p>
</div>
</body></html>"""
    return html


def main():
    password = load_password()

    # 1. 运行爬虫
    print("运行爬虫...")
    import subprocess
    subprocess.run(["python3", os.path.join(SCRIPT_DIR, "crawler_city.py"), "1"],
                   cwd=SCRIPT_DIR, timeout=600)

    # 2. 生成看板
    print("生成看板...")
    subprocess.run(["python3", os.path.join(SCRIPT_DIR, "build_dashboard.py")],
                   cwd=SCRIPT_DIR)

    # 3. 生成报告
    print("生成报告...")
    html = generate_report()

    # 4. 发送邮件
    print("发送邮件...")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🏥 河南医疗设备招投标周报 - {datetime.now().strftime('%m/%d')}"
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(FROM_EMAIL, password)
        server.sendmail(FROM_EMAIL, [TO_EMAIL], msg.as_string())

    # 5. 推送 GitHub
    print("推送 GitHub...")
    subprocess.run(["git", "add", "henan_medical_full.json", "docs/index.html"],
                   cwd=SCRIPT_DIR)
    subprocess.run(["git", "commit", "-m", f"周报自动更新 {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                   cwd=SCRIPT_DIR)
    subprocess.run(["git", "push"], cwd=SCRIPT_DIR)

    print("✅ 完成！")


if __name__ == "__main__":
    main()
