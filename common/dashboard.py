"""生成本地HTML看板 — 自包含，双击即可查看"""
import json, os


def build_dashboard(json_path, html_path):
    """从JSON生成自包含HTML看板"""
    with open(json_path) as f:
        data = json.load(f)

    items = data.get("items", [])
    summary = data.get("summary", {})

    # 嵌入JSON数据
    json_str = json.dumps(items, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>河南医疗设备招投标 — 本地看板</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background:#f5f5f5; color:#333; }}
.header {{ background:#2c3e50; color:#fff; padding:20px 30px; }}
.header h1 {{ font-size:22px; }}
.header p {{ font-size:13px; opacity:.7; margin-top:5px; }}
.summary {{ display:flex; gap:15px; padding:15px 30px; background:#fff; border-bottom:1px solid #e0e0e0; flex-wrap:wrap; }}
.stat {{ text-align:center; min-width:80px; }}
.stat .num {{ font-size:28px; font-weight:bold; }}
.stat .label {{ font-size:12px; color:#888; }}
.stat .num.bid {{ color:#e74c3c; }} .stat .num.win {{ color:#27ae60; }} .stat .num.stop {{ color:#95a5a6; }} .stat .num.other {{ color:#3498db; }}
.controls {{ display:flex; gap:10px; padding:12px 30px; background:#fff; border-bottom:1px solid #e0e0e0; flex-wrap:wrap; align-items:center; }}
.controls input {{ padding:8px 12px; border:1px solid #ccc; border-radius:4px; width:250px; font-size:14px; }}
.controls select {{ padding:8px; border:1px solid #ccc; border-radius:4px; font-size:14px; }}
.tabs {{ display:flex; gap:0; }}
.tab {{ padding:8px 16px; border:1px solid #ccc; background:#fff; cursor:pointer; font-size:13px; border-radius:4px; margin-right:4px; }}
.tab.active {{ background:#2c3e50; color:#fff; border-color:#2c3e50; }}
table {{ width:100%; border-collapse:collapse; background:#fff; }}
th {{ background:#f8f9fa; padding:10px 12px; text-align:left; font-size:13px; border-bottom:2px solid #dee2e6; position:sticky; top:0; }}
td {{ padding:8px 12px; font-size:13px; border-bottom:1px solid #eee; }}
tr:hover {{ background:#f8f9ff; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; }}
.badge-bid {{ background:#fde8e8; color:#c0392b; }}
.badge-win {{ background:#d5f5e3; color:#1e8449; }}
.badge-stop {{ background:#eaecee; color:#7f8c8d; }}
.badge-other {{ background:#d6eaf8; color:#2471a3; }}
a {{ color:#2980b9; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
#count {{ font-size:13px; color:#888; padding:8px 30px; }}
</style>
</head>
<body>
<div class="header">
<h1>🏥 河南医疗设备招投标 — 本地看板</h1>
<p>运行时间: {datetime_now()}</p>
</div>
<div class="summary">
<div class="stat"><div class="num">{summary.get("total","?")}</div><div class="label">总计</div></div>
<div class="stat"><div class="num bid">{summary.get("categories",{}).get("招标","?")}</div><div class="label">招标</div></div>
<div class="stat"><div class="num win">{summary.get("categories",{}).get("中标","?")}</div><div class="label">中标</div></div>
<div class="stat"><div class="num stop">{summary.get("categories",{}).get("终止","?")}</div><div class="label">终止</div></div>
<div class="stat"><div class="num other">{summary.get("categories",{}).get("其他","?")}</div><div class="label">其他</div></div>
</div>
<div class="controls">
<div class="tabs" id="tabs">
<span class="tab active" data-cat="all">全部</span>
<span class="tab" data-cat="招标">招标</span>
<span class="tab" data-cat="中标">中标</span>
<span class="tab" data-cat="终止">终止</span>
<span class="tab" data-cat="其他">其他</span>
</div>
<select id="cityFilter"><option value="all">全部城市</option></select>
<input id="search" placeholder="搜索标题、设备关键词...">
</div>
<div id="count"></div>
<table>
<thead><tr>
<th style="width:60px">分类</th><th>标题</th><th style="width:70px">城市</th><th style="width:90px">发布日期</th><th style="width:120px">发布机构</th>
</tr></thead>
<tbody id="tbody"></tbody>
</table>

<script>
var DATA = {json_str};
var CATS = ["招标","中标","终止","其他"];
var activeCat = "all";

// Init city dropdown
var cities = [...new Set(DATA.map(function(d){{return d.city||"未知"}}))].sort();
var sel = document.getElementById("cityFilter");
cities.forEach(function(c){{
  var o = document.createElement("option");
  o.value = c; o.textContent = c;
  sel.appendChild(o);
}});

function render(){{
  var cat = activeCat;
  var city = document.getElementById("cityFilter").value;
  var kw = document.getElementById("search").value.toLowerCase();
  var filtered = DATA.filter(function(d){{
    if (cat !== "all" && d.category !== cat) return false;
    if (city !== "all" && d.city !== city) return false;
    if (kw && (d.title||"").toLowerCase().indexOf(kw) === -1) return false;
    return true;
  }});
  document.getElementById("count").textContent = "显示 " + filtered.length + " / " + DATA.length + " 条";
  var html = "";
  filtered.forEach(function(d){{
    var catClass = ""; var catText = d.category||"其他";
    if (catText==="招标") catClass="badge-bid";
    else if (catText==="中标") catClass="badge-win";
    else if (catText==="终止") catClass="badge-stop";
    else catClass="badge-other";
    var title = d.title||"";
    var url = d.detail_url||"";
    html += "<tr><td><span class=\\"badge " + catClass + "\\">" + catText + "</span></td>";
    html += "<td>" + (url ? "<a href=\\"" + url + "\\" target=\\"_blank\\">" + title + "</a>" : title) + "</td>";
    html += "<td>" + (d.city||"") + "</td>";
    html += "<td>" + (d.pub_time||d.pub_date||"").slice(0,10) + "</td>";
    html += "<td>" + (d.agency||"").slice(0,20) + "</td></tr>";
  }});
  document.getElementById("tbody").innerHTML = html;
}}

// Tab clicks
document.querySelectorAll(".tab").forEach(function(t){{
  t.addEventListener("click", function(){{
    document.querySelectorAll(".tab").forEach(function(x){{x.classList.remove("active")}});
    this.classList.add("active");
    activeCat = this.dataset.cat;
    render();
  }});
}});

// Search + city filter
document.getElementById("search").addEventListener("input", render);
document.getElementById("cityFilter").addEventListener("change", render);

render();
</script>
</body>
</html>'''

    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path


def datetime_now():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")
