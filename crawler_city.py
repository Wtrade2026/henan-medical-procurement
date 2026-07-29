"""
九市医疗设备招投标爬虫
每个市独立 ggcx，自动遍历采集 + 本地合并
"""

import requests, ddddocr, re, json, time, os, socket, sys
from bs4 import BeautifulSoup

socket.setdefaulttimeout(20)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(SCRIPT_DIR, "henan_medical_full.json")

# 城市配置：域名 + URL路径
CITIES = {
    "郑州":   {"base": "https://zhengzhou.zfcg.henan.gov.cn", "path": "zhengzhou"},
    "开封":   {"base": "https://zfcg.henan.gov.cn",           "path": "kaifeng"},
    "洛阳":   {"base": "https://luoyang.zfcg.henan.gov.cn",   "path": "luoyang"},
    "平顶山": {"base": "https://zfcg.henan.gov.cn",           "path": "pingdingshan"},
    "安阳":   {"base": "https://anyang.zfcg.henan.gov.cn",    "path": "anyang"},
    "鹤壁":   {"base": "https://hebi.zfcg.henan.gov.cn",      "path": "hebi"},
    "新乡":   {"base": "https://xinxiang.zfcg.henan.gov.cn",  "path": "xinxiang"},
    "焦作":   {"base": "https://zfcg.henan.gov.cn",           "path": "jiaozuo"},
    "濮阳":   {"base": "https://zfcg.henan.gov.cn",           "path": "puyang"},
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

MEDICAL_EQUIPMENT = [
    '核磁共振', '核磁', 'MRI', '磁共振', 'CT', '直线加速器', '放疗',
    '超声', '彩超', 'B超', 'DSA', '血管造影', 'C臂', 'X射线', 'X光', 'DR',
    '内窥镜', '内镜', '腹腔镜', '胸腔镜', '腔镜', '喉镜',
    '监护仪', '监护系统', '呼吸机', '麻醉机', '除颤仪', '血液透析', '血透',
    '生化分析', '血球分析', '免疫分析', '质谱仪', '测序仪', 'PCR',
    '手术系统', '手术显微镜', '手术床', '无影灯', '电刀', '激光治疗',
    '消毒设备', '灭菌器', '清洗消毒', '供氧', '口腔CT', 'CBCT',
    '康复设备', '理疗', '高压氧舱', '碎石机', '治疗仪', '诊断仪',
    '医用设备', '医疗设备', '医疗器械', '医用耗材',
    '设备采购', '设备购置', '设备更新', '仪器购置',
]

INSTITUTION = ['医院', '卫生院', '疾控', '妇幼保健', '中医', '医科',
               '血站', '急救', '附属医院', '中心医院', '人民医院', '中医院',
               '卫生健康', '保健院', '社区卫生']


def is_medical(title, body=""):
    text = f"{title} {body}"
    eq = [kw for kw in MEDICAL_EQUIPMENT if kw.lower() in text.lower()]
    inst = [kw for kw in INSTITUTION if kw in text]
    if eq: return True, eq
    if inst and any(e in text for e in ['采购', '设备', '仪', '机', '系统', '镜']):
        return True, []
    return False, []


def new_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def solve_captcha(session, base_url, path, time_type="1"):
    """time_type: 0=今日, 1=近1周, 2=近1月"""
    ocr = ddddocr.DdddOcr(show_ad=False)
    ggcx_url = f"{base_url}/{path}/ggcx"

    for _ in range(10):
        session.cookies.clear()
        try:
            r = session.get(ggcx_url, timeout=(10, 20))
            r.encoding = "utf-8"
        except Exception:
            time.sleep(3)
            continue

        tm = re.search(r'getImage/([a-f0-9]+)', r.text)
        sm = re.search(r'soCode=([a-f0-9]+)', r.text)
        if not tm or not sm: continue

        try:
            img = session.get(f"{base_url}/{path}/getImage/{tm.group(1)}", timeout=(5, 10))
            code = ocr.classification(img.content)
        except Exception:
            continue

        form = {"bidType": "0", "timeType": time_type, "fromtime": "", "endtime": "",
                "title": "", "croporgan_name": "", "project_no": "",
                "gpmethod": "", "agency_name": "", "code": code}

        try:
            r2 = session.post(f"{ggcx_url}?soCode={sm.group(1)}", data=form, timeout=(10, 20))
            r2.encoding = "utf-8"
        except Exception:
            continue

        if "errCode=1" not in r2.url:
            items = parse_list(r2.text)
            p = re.search(r'共\s*(\d+)\s*页', r2.text)
            total = int(p.group(1)) if p else 1
            return sm.group(1), items, total
    raise Exception("验证码失败")


def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for li in soup.select("div.List2 ul li"):
        a = li.find("a")
        if not a: continue
        title = a.get_text(strip=True)
        href = a.get("href", "")
        iid = re.search(r'infoId=(\d+)', href)
        ch = re.search(r'channelCode=(\w+)', href)
        atype = ""
        region = ""
        p = li.find("p")
        if p:
            for sp in p.find_all("span", class_="Right10"):
                txt = sp.get_text(strip=True)
                b = sp.find("span", class_="Blue")
                if "公告类型" in txt:
                    atype = b.get_text(strip=True) if b else ""
                elif "区域" in txt:
                    region = b.get_text(strip=True) if b else ""
        abs_url = href if href.startswith("http") else f"https://{href.lstrip('/')}" if href.startswith("//") else ""
        if not abs_url:
            abs_url = href
        # 从 region 字段推断城市
        city = ""
        if region:
            for cn in ["郑州","开封","洛阳","平顶山","安阳","鹤壁","新乡","焦作","濮阳",
                       "南阳","许昌","周口","商丘","驻马店","信阳","漯河","三门峡","济源"]:
                if cn in region: city = cn; break
            if not city and "河南" in region: city = "省级"
        results.append({
            "title": title, "info_id": iid.group(1) if iid else "",
            "channel_code": ch.group(1) if ch else "",
            "announce_type": atype, "region": region, "city": city,
            "detail_url": abs_url,
        })
    return results


def fetch_page(session, base_url, path, so_code, page_no):
    for _ in range(3):
        try:
            url = f"{base_url}/{path}/ggcx"
            params = {"appCode": "H60", "pageSize": "15", "soCode": so_code, "pageNo": str(page_no)}
            r = session.get(url, params=params, timeout=(10, 20))
            r.encoding = "utf-8"
            if "访问频繁" in r.text: time.sleep(10); continue
            if "cgxxForm" in r.text and "infoId=" not in r.text: return None
            return parse_list(r.text)
        except Exception:
            time.sleep(5)
    return []


def fetch_detail(session, detail_url):
    try:
        r = session.get(detail_url, timeout=(10, 20))
        r.encoding = "utf-8"
    except Exception:
        return {}
    soup = BeautifulSoup(r.text, "html.parser")
    result = {}
    h1 = soup.find("h1")
    if h1: result["title_detail"] = h1.get_text(strip=True)
    md = soup.find("div", class_="TxtCenter")
    if md:
        t = md.get_text()
        for k, p in [("agency", r'发布机构[：:]\s*(.+?)(?:&nbsp;|\s{2,})'),
                      ("pub_time", r'发布日期[：:]\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})'),
                      ("views", r'访问次数[：:]\s*(\d+)')]:
            m = re.search(p, t)
            if m: result[k] = m.group(1).strip()
    for s in soup.find_all("script"):
        if s.string and ".htm" in (s.string or ""):
            m = re.search(r'\$\.get\("([^"]+\.htm)"', s.string)
            if m:
                cu = m.group(1)
                if cu.startswith("/"): result["content_url"] = f"https://{cu.lstrip('/')}" if "//" in cu else cu
                elif cu.startswith("http"): result["content_url"] = cu
    return result


def fetch_body(session, url):
    try:
        if not url.startswith("http"):
            return ""
        return session.get(url, timeout=(10, 20)).text
    except Exception:
        return ""


def crawl_city(name, cfg, time_type):
    """爬取单个城市，返回医疗设备列表"""
    base_url = cfg["base"]
    path = cfg["path"]
    session = new_session()

    print(f"\n{'='*50}")
    print(f"🏙️  {name} ({base_url}/{path})")
    print(f"{'='*50}")

    # Phase 1: 列表
    try:
        so_code, p1, total = solve_captcha(session, base_url, path, time_type)
    except Exception as e:
        print(f"  ❌ 验证码失败: {e}")
        return []

    all_items = list(p1)
    print(f"  共 {total} 页")

    for p in range(2, min(total, 50) + 1):  # 每城市最多50页
        items = fetch_page(session, base_url, path, so_code, p)
        if items is None:
            session = new_session()
            try:
                so_code, _, _ = solve_captcha(session, base_url, path, time_type)
            except Exception:
                break
            items = fetch_page(session, base_url, path, so_code, p) or []
        all_items.extend(items)
        if p % 15 == 0:
            print(f"    {p}/{total} ({len(all_items)}条)")
        time.sleep(2)

    print(f"  列表: {len(all_items)} 条")

    # Phase 2: 过滤
    medical = []
    for d in all_items:
        ok, eq = is_medical(d["title"])
        if ok:
            d["matched_eq"] = eq
            d["city"] = name
            medical.append(d)

    print(f"  医疗: {len(medical)} 条")

    # Phase 3: 详情+正文
    for i, d in enumerate(medical):
        detail_url = d["detail_url"]
        if detail_url and not detail_url.startswith("http"):
            detail_url = f"{base_url}{detail_url}" if detail_url.startswith("/") else f"{base_url}/{detail_url}"
            d["detail_url"] = detail_url

        if detail_url:
            detail = fetch_detail(session, detail_url)
            for k in ["title_detail", "agency", "pub_time", "views", "content_url"]:
                if detail.get(k):
                    if k == "title_detail":
                        d["title"] = detail[k]
                    else:
                        d[k] = detail[k]
            time.sleep(2)

            if d.get("content_url"):
                d["body_html"] = fetch_body(session, d["content_url"])
                time.sleep(2)

        if (i + 1) % 10 == 0:
            print(f"    详情: {i+1}/{len(medical)}")

    return medical


def main():
    import sys
    TIME_TYPE = sys.argv[1] if len(sys.argv) > 1 else "1"
    labels = {"0": "今日", "1": "近1周", "2": "近1月"}
    cities_to_crawl = sys.argv[2:] if len(sys.argv) > 2 else list(CITIES.keys())

    print(f"九市医疗设备爬虫 - {labels.get(TIME_TYPE, TIME_TYPE)}")
    print(f"目标城市: {', '.join(cities_to_crawl)}")

    # 加载已有数据
    existing = []
    if os.path.exists(OUTPUT) and os.path.getsize(OUTPUT) > 100:
        with open(OUTPUT) as f:
            existing = json.load(f).get("items", [])

    existing_ids = {d.get("info_id") for d in existing if d.get("info_id")}

    all_medical = []
    for city in cities_to_crawl:
        if city not in CITIES:
            print(f"未知城市: {city}")
            continue
        items = crawl_city(city, CITIES[city], TIME_TYPE)
        all_medical.extend(items)

    # 合并去重
    for d in existing:
        if d.get("info_id") and d["info_id"] not in {x.get("info_id") for x in all_medical}:
            all_medical.append(d)

    # 分类
    cats = {"招标": 0, "中标": 0, "终止": 0, "其他": 0}
    for d in all_medical:
        at = d.get("announce_type", "")
        if at in ("采购公告", "采购意向"): d["category"] = "招标"; cats["招标"] += 1
        elif at in ("结果公告", "合同公告"): d["category"] = "中标"; cats["中标"] += 1
        elif at in ("废标公告", "变更公告"): d["category"] = "终止"; cats["终止"] += 1
        else: d["category"] = "其他"; cats["其他"] += 1

    output = {"summary": {"total": len(all_medical), "categories": cats, "cities": len(cities_to_crawl)}, "items": all_medical}
    with open(OUTPUT, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ 完成! {len(all_medical)} 条 ({len(existing_ids)} 条旧 + {len(all_medical)-len(existing_ids)} 条新)")
    for k, v in cats.items():
        print(f"  {k}: {v}")
    print(f"  保存到: {OUTPUT}")


if __name__ == "__main__":
    main()
