#!/usr/bin/env python3
"""生成医疗设备招投标数据看板 HTML - 修复编码 + script注入"""

import json, re, base64
from datetime import datetime

import os, sys

DATA_FILE = "/home/wayne/projects/henan-procurement/henan_medical_full.json"

# 尝试合并旧数据
old_items = []
if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 1000:
    with open(DATA_FILE) as f:
        old = json.load(f)
        old_items = old.get("items", [])
        print(f"  已有数据: {len(old_items)} 条")

with open(DATA_FILE) as f:
    raw = json.load(f)

items = raw.get("items", [])
print(f"  本次采集: {len(items)} 条")

# 合并去重
if old_items and old_items != items:
    seen = set()
    merged = []
    # 先加旧的，再加新的(新数据优先)
    for d in old_items + items:
        iid = d.get("info_id", "")
        if iid and iid not in seen:
            seen.add(iid)
            merged.append(d)
        elif not iid:
            merged.append(d)
    # 去重的旧数据也合并
    old_ids = {d.get("info_id") for d in old_items if d.get("info_id")}
    for d in items:
        iid = d.get("info_id")
        if iid and iid not in old_ids:
            merged.append(d)

    if len(merged) > len(items):
        print(f"  合并后: {len(merged)} 条 (新增 {len(merged) - len(old_items)} 条)")
        items = merged
        # 更新 JSON 文件
        with open(DATA_FILE, "w") as f:
            json.dump({"summary": raw.get("summary", {}), "items": merged}, f, ensure_ascii=False)
else:
    print(f"  最终: {len(items)} 条")

def classify(at):
    if at in ("采购公告", "采购意向"): return "招标"
    if at in ("结果公告", "合同公告"): return "中标"
    if at in ("废标公告", "变更公告"): return "终止"
    return "其他"

for d in items:
    d["category"] = classify(d.get("announce_type", ""))
    d["title_short"] = re.sub(r'^【[^】]+】', '', d["title"])
    d["title_short"] = re.sub(r'^ZFCG[^号]*号', '', d["title_short"]).strip()
    if not d.get("pub_time"):
        d["pub_time"] = d.get("pub_time_list", "")

# 去重
seen = set()
unique = []
for d in items:
    iid = d.get("info_id", "")
    if iid and iid not in seen:
        seen.add(iid)
        unique.append(d)
    elif not iid:
        unique.append(d)
items = unique

# 准备安全数据 (不含 body_html，避免 script 标签冲突)
safe_items = []
for d in items:
    sd = {k: v for k, v in d.items() if k not in ("body_html", "attachments", "content_url", "matched_inst")}
    sd["has_body"] = bool(d.get("body_html"))
    safe_items.append(sd)

# JSON → Base64 (彻底避免编码和注入问题)
json_str = json.dumps(safe_items, ensure_ascii=False, separators=(',', ':'))
data_b64 = base64.b64encode(json_str.encode('utf-8')).decode('ascii')

# 统计
cats = {"招标": 0, "中标": 0, "终止": 0, "其他": 0}
for d in items: cats[d["category"]] = cats.get(d["category"], 0) + 1

# 计算数据截止时间
pub_times = sorted([d.get("pub_time","") for d in items if d.get("pub_time")], reverse=True)
data_latest = pub_times[0] if pub_times else "未知"
data_earliest = pub_times[-1] if pub_times else "未知"
gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")

# 生成 HTML
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>河南省医疗设备招投标数据看板</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; background:#f0f2f5; color:#333; }}
.header {{ background:linear-gradient(135deg,#1a73e8,#0d47a1); color:#fff; padding:24px 32px; }}
.header h1 {{ font-size:22px; font-weight:600; }}
.header p {{ font-size:13px; opacity:.85; margin-top:4px; }}
.stats {{ display:flex; gap:16px; padding:20px 32px; background:#fff; border-bottom:1px solid #e8e8e8; flex-wrap:wrap; }}
.stat-card {{ flex:1; min-width:110px; text-align:center; padding:16px; border-radius:8px; background:#f8f9fa; }}
.stat-card .num {{ font-size:28px; font-weight:700; }}
.stat-card .label {{ font-size:12px; color:#888; margin-top:4px; }}
.stat-card.zhaobiao .num {{ color:#1a73e8; }}
.stat-card.zhongbiao .num {{ color:#0d904f; }}
.stat-card.zhongzhi .num {{ color:#d93025; }}
.controls {{ padding:12px 32px; background:#fff; display:flex; gap:12px; align-items:center; flex-wrap:wrap; border-bottom:1px solid #e8e8e8; }}
.controls input,.controls select {{ padding:8px 12px; border:1px solid #d0d0d0; border-radius:6px; font-size:13px; }}
.controls input {{ width:260px; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }}
.badge.zhaobiao {{ background:#e3f0ff; color:#1a73e8; }}
.badge.zhongbiao {{ background:#e6f4ea; color:#0d904f; }}
.badge.zhongzhi {{ background:#fce8e6; color:#d93025; }}
.badge.qita {{ background:#f0f0f0; color:#666; }}
.table-wrap {{ padding:0 32px 32px; background:#fff; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ background:#f8f9fa; padding:10px 12px; text-align:left; font-weight:600; border-bottom:2px solid #e0e0e0; white-space:nowrap; }}
td {{ padding:10px 12px; border-bottom:1px solid #f0f0f0; }}
tr:hover {{ background:#f8f9ff; }}
td.title {{ max-width:420px; }}
td.title a {{ color:#1a73e8; text-decoration:none; }}
td.title a:hover {{ text-decoration:underline; }}
.highlight {{ background:#fff9c4; padding:1px 3px; border-radius:2px; }}
.footer {{ text-align:center; padding:20px; color:#999; font-size:12px; }}
.tab-btn {{ padding:8px 16px; border:1px solid #d0d0d0; background:#fff; cursor:pointer; font-size:13px; border-radius:6px; margin-right:4px; }}
.tab-btn.active {{ background:#1a73e8; color:#fff; border-color:#1a73e8; }}
#resultInfo {{ font-size:12px; color:#888; margin-left:auto; }}
</style>
</head>
<body>

<div class="header">
  <h1>&#x1F3E5; 河南省医疗设备招投标数据看板</h1>
  <p>数据来源：河南省政府采购网 &middot; 查询范围：近1月 &middot; 数据截止：{data_latest} &middot; 生成时间：{gen_time}</p>
</div>

<div class="stats">
  <div class="stat-card zhaobiao"><div class="num" id="cnt-zhaobiao">{cats["招标"]}</div><div class="label">&#x1F7E2; 招标</div></div>
  <div class="stat-card zhongbiao"><div class="num" id="cnt-zhongbiao">{cats["中标"]}</div><div class="label">&#x1F535; 中标</div></div>
  <div class="stat-card zhongzhi"><div class="num" id="cnt-zhongzhi">{cats["终止"]}</div><div class="label">&#x1F534; 终止</div></div>
  <div class="stat-card"><div class="num">{len(items)}</div><div class="label">&#x1F4CA; 合计</div></div>
</div>

<div class="controls">
  <button class="tab-btn active" onclick="filterCat('全部',this)">全部</button>
  <button class="tab-btn" onclick="filterCat('招标',this)">&#x1F7E2; 招标</button>
  <button class="tab-btn" onclick="filterCat('中标',this)">&#x1F535; 中标</button>
  <button class="tab-btn" onclick="filterCat('终止',this)">&#x1F534; 终止</button>
  <select id="equipFilter" onchange="render()" style="margin-left:16px;">
    <option value="">全部设备类型</option>
    <option value="磁共振">磁共振/MRI</option>
    <option value="CT">CT</option>
    <option value="超声">超声/彩超</option>
    <option value="内镜">内镜/腔镜</option>
    <option value="呼吸机">呼吸机</option>
    <option value="监护仪">监护仪</option>
    <option value="血液透析">血液透析</option>
    <option value="生化分析">生化分析</option>
    <option value="手术系统">手术系统</option>
    <option value="直线加速器">直线加速器</option>
    <option value="DSA">DSA/血管造影</option>
    <option value="消毒">消毒/灭菌</option>
  </select>
  <select id="cityFilter" onchange="render()" style="margin-left:16px;">
    <option value="">全部城市</option>
  </select>
  <select id="dateFilter" onchange="render()" style="margin-left:16px;">
    <option value="">全部时间</option>
    <option value="7">近1周</option>
    <option value="30">近1月</option>
    <option value="90">近3月</option>
  </select>
  <input type="text" id="search" placeholder="&#x1F50D; 搜索标题、机构、设备关键词..." oninput="render()">
  <span id="resultInfo"></span>
</div>

<div class="table-wrap">
  <table>
    <thead><tr>
      <th style="width:40px">#</th>
      <th style="width:55px">类型</th>
      <th style="width:55px">城市</th>
      <th style="width:85px">时间</th>
      <th>标题</th>
      <th style="width:140px">机构</th>
      <th style="width:120px">设备词</th>
    </tr></thead>
    <tbody id="tbody"></tbody>
  </table>
</div>

<div class="footer">河南省政府采购网 &middot; zfcg.henan.gov.cn</div>

<script>
// Base64 解码 → UTF-8
var DATA_B64 = "{data_b64}";
var DATA_RAW = atob(DATA_B64);
var DATA_UTF8 = new TextDecoder('utf-8').decode(new Uint8Array([...DATA_RAW].map(function(c){{return c.charCodeAt(0);}})));
var ALL_DATA = JSON.parse(DATA_UTF8);

// 设备关键词映射
var EQUIP_KW = {{
  "磁共振":["磁共振","核磁","MRI"],
  "CT":["CT设备","CT机","CT扫描","CT球管","CT维保","CT采购","螺旋CT","CT"],
  "超声":["超声","彩超","B超"],
  "内镜":["内镜","腔镜","内窥镜","腹腔镜","胸腔镜"],
  "呼吸机":["呼吸机"],
  "监护仪":["监护仪","监护系统"],
  "血液透析":["血液透析","血透","血滤"],
  "生化分析":["生化分析","生化仪","分析仪"],
  "手术系统":["手术系统","手术导航","手术床"],
  "直线加速器":["直线加速器","放疗"],
  "DSA":["DSA","血管造影"],
  "消毒":["消毒","灭菌"]
}};

var currentCat = "全部";

// 动态生成城市下拉选项（从数据中提取，含"未知"）
(function initCityFilter() {{
  var cities = {{}};
  ALL_DATA.forEach(function(d) {{ cities[d.city || '未知'] = 1; }});
  var sel = document.getElementById("cityFilter");
  Object.keys(cities).sort().forEach(function(c) {{
    var opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    sel.appendChild(opt);
  }});
}})();

function filterCat(cat, btn) {{
  currentCat = cat;
  document.querySelectorAll('.tab-btn').forEach(function(b){{ b.classList.remove('active'); }});
  btn.classList.add('active');
  render();
}}

function highlight(text) {{
  var t = text;
  for (var cat in EQUIP_KW) {{
    var kws = EQUIP_KW[cat];
    for (var i = 0; i < kws.length; i++) {{
      var re = new RegExp('(' + kws[i].replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'g');
      t = t.replace(re, '<span class="highlight">$1</span>');
    }}
  }}
  return t;
}}

function render() {{
  var search = document.getElementById("search").value.toLowerCase();
  var equip = document.getElementById("equipFilter").value;
  var city = document.getElementById("cityFilter").value;
  var days = document.getElementById("dateFilter").value;

  var data = ALL_DATA;
  if (currentCat !== "全部") {{
    data = data.filter(function(d){{ return d.category === currentCat; }});
  }}

  // 城市筛选（精确匹配）
  if (city) {{
    data = data.filter(function(d){{ return (d.city || '未知') === city; }});
  }}

  // 日期筛选：近 N 天内（按 pub_time 前10位 YYYY-MM-DD）
  if (days) {{
    var cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - parseInt(days));
    var cutoffStr = cutoff.toISOString().slice(0,10);
    data = data.filter(function(d){{
      var t = (d.pub_time || "").slice(0,10);
      return t >= cutoffStr;
    }});
  }}

  if (equip) {{
    var kws = EQUIP_KW[equip] || [];
    data = data.filter(function(d){{
      var t = (d.title + " " + (d.body_html || "")).toLowerCase();
      return kws.some(function(kw){{ return t.indexOf(kw.toLowerCase()) >= 0; }});
    }});
  }}

  if (search) {{
    data = data.filter(function(d){{
      return (d.title + " " + (d.agency || "") + " " + (d.matched_eq || []).join(" ")).toLowerCase().indexOf(search) >= 0;
    }});
  }}

  data.sort(function(a,b){{ return (b.pub_time||"").localeCompare(a.pub_time||""); }});

  var catCounts = {{}};
  data.forEach(function(d){{ catCounts[d.category] = (catCounts[d.category]||0) + 1; }});
  ["招标","中标","终止"].forEach(function(c){{
    var el = document.getElementById("cnt-" + (c==="招标"?"zhaobiao":c==="中标"?"zhongbiao":"zhongzhi"));
    if (el) el.textContent = catCounts[c] || 0;
  }});

  document.getElementById("resultInfo").textContent = "共 " + data.length + " 条";

  var tbody = document.getElementById("tbody");
  if (data.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#999;">无匹配结果</td></tr>';
    return;
  }}

  var catCN = {{"招标":"zhaobiao","中标":"zhongbiao","终止":"zhongzhi","其他":"qita"}};

  tbody.innerHTML = data.map(function(d,i){{
    var cls = catCN[d.category] || "qita";
    var eq = (d.matched_eq || []).slice(0,4).join(", ");
    var title = highlight(d.title_short || d.title);
    var time = (d.pub_time || "").slice(5);

    return '<tr>' +
      '<td>' + (i+1) + '</td>' +
      '<td><span class="badge ' + cls + '">' + d.category + '</span></td>' +
      '<td style="font-size:12px">' + (d.city || '') + '</td>' +
      '<td style="white-space:nowrap;font-size:12px">' + time + '</td>' +
      '<td class="title"><a href="' + d.detail_url + '" target="_blank">' + title + '</a></td>' +
      '<td style="font-size:12px">' + (d.agency || "") + '</td>' +
      '<td style="font-size:11px;color:#888">' + eq + '</td>' +
      '</tr>';
  }}).join("");
}}

render();
</script>

</body>
</html>'''

with open("/home/wayne/projects/henan-procurement/docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 看板已生成: docs/index.html ({len(html)/1024:.0f} KB)")
print(f"   包含 {len(items)} 条记录")
print(f"   编码: UTF-8 + Base64 (防注入)")
