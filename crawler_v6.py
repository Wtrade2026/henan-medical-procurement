"""
河南省政府采购网 - 分批+断点续传 v6
解决代理不稳：每批20条保存，中断可续传
"""

import requests, ddddocr, re, json, time, os, socket, sys
from bs4 import BeautifulSoup

socket.setdefaulttimeout(20)
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

BASE_URL = "https://zfcg.henan.gov.cn"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FULL_OUTPUT = os.path.join(SCRIPT_DIR, "henan_medical_full.json")
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "crawl_progress.json")  # 断点续传

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BATCH_SIZE = 20  # 每批处理20条，立即保存

# ====== 关键词 ======
MEDICAL_EQUIPMENT = [
    '核磁共振', '核磁', 'MRI', '磁共振', 'CT设备', 'CT机', 'CT扫描', 'CT维保', 'CT维修',
    'CT采购', 'CT球管', '螺旋CT', '直线加速器', '放疗', '放射治疗',
    '超声诊断', '超声', '彩超', 'B超', '便携超声', '超声仪', '超声刀', '超声探头',
    '彩色多普勒', '四维彩超', 'DSA', '血管造影', 'C臂', 'C型臂', 'X射线', 'X光机',
    'DR设备', '数字胃肠', '乳腺机', '乳腺摄影', '钼靶', '骨密度', 'PET-CT', 'PET/MR',
    'SPECT', '内窥镜', '内镜', '腹腔镜', '胸腔镜', '宫腔镜', '关节镜', '输尿管镜',
    '膀胱镜', '胃镜', '肠镜', '鼻内镜', '腔镜', '喉镜', '气管镜',
    '监护仪', '监护系统', '呼吸机', '麻醉机', '除颤仪', '心电图', '脑电图',
    '输液泵', '注射泵', '血液透析', '血滤', 'ECMO', '体外循环', '起搏器',
    '血透', '血流动力学监测', '漂浮导管',
    '生化分析', '血球分析', '血细胞分析', '免疫分析', '质谱仪', '测序仪', 'PCR仪',
    '基因测序', '流式细胞', '病理切片', '酶联免疫',
    '手术显微镜', '手术系统', '手术床', '手术导航', '无影灯', '电刀', '激光治疗',
    '射频治疗', '微波治疗', '等离子手术', '高频电刀', '高频治疗', '冲击波碎石',
    '碎石机', '脑立体定向', '电生理导航',
    '消毒设备', '灭菌器', '清洗消毒', '高压蒸汽', '供氧', '超净工作台',
    '口腔CT', 'CBCT', '牙科', '眼科', '验光仪', '耳鼻喉', '听力计',
    '康复设备', '理疗', '高压氧舱', '牵引床', '康复科',
    '医疗设备', '医用设备', '医疗器械', '医疗仪器', '医用耗材',
    '设备购置', '设备采购', '设备更新换代', '仪器购置',
    '筛查仪', '治疗仪', '诊断仪', '产床', '病床', '吊塔', '吊桥', '护理设备',
]

INSTITUTION = ['医院', '卫生院', '疾控', '妇幼保健', '医科', '中医', '卫生服务',
               '社区卫生', '血站', '急救', '附属医院', '中心医院', '人民医院',
               '中医院', '卫生健康', '保健院', '医学院']


def is_medical(title, body, announce_type):
    text = f"{title} {body}" if body else title
    eq = [kw for kw in MEDICAL_EQUIPMENT if kw.lower() in text.lower()]
    inst = [kw for kw in INSTITUTION if kw in text]
    if eq: return True, eq, inst
    if inst and announce_type == "采购意向": return True, [], inst
    if inst and any(e in text for e in ['采购', '设备', '仪', '机', '系统', '镜']):
        return True, [], inst
    return False, [], []


def new_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def safe_get(session, url, **kw):
    for retry in range(3):
        try:
            return session.get(url, timeout=(10, 20), **kw)
        except Exception:
            if retry == 2: raise
            time.sleep(5)


def solve_captcha(session, time_type="2"):
    """time_type: 0=今日, 1=近1周, 2=近1月"""
    ocr = ddddocr.DdddOcr(show_ad=False)
    for _ in range(10):
        session.cookies.clear()
        try:
            r = session.get(f"{BASE_URL}/henan/ggcx", timeout=(10, 20))
            r.encoding = "utf-8"
        except Exception:
            time.sleep(3)
            continue
        tm = re.search(r'getImage/([a-f0-9]+)', r.text)
        sm = re.search(r'soCode=([a-f0-9]+)', r.text)
        if not tm or not sm: continue
        try:
            img = session.get(f"{BASE_URL}/henan/getImage/{tm.group(1)}", timeout=(5, 10))
            code = ocr.classification(img.content)
        except Exception:
            continue
        form = {"bidType": "0", "timeType": time_type, "fromtime": "", "endtime": "",
                "title": "", "croporgan_name": "", "project_no": "",
                "gpmethod": "", "agency_name": "", "code": code}
        try:
            r2 = session.post(f"{BASE_URL}/henan/ggcx?soCode={sm.group(1)}", data=form, timeout=(10, 20))
            r2.encoding = "utf-8"
        except Exception:
            continue
        if "errCode=1" not in r2.url:
            items = parse_list(r2.text)
            p = re.search(r'共\s*(\d+)\s*页', r2.text)
            total = int(p.group(1)) if p else 1
            print(f"  验证码 [{code}] ✓  {len(items)}条/{total}页")
            return sm.group(1), items, total
        print(f"  [{code}] ✗", end=" ")
    raise Exception("验证码持续失败")


def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for li in soup.select("div.List2 ul li"):
        a = li.find("a")
        if not a: continue
        title = a.get_text(strip=True)
        href = a.get("href", "")
        iid, ch = "", ""
        if "infoId=" in href:
            m = re.search(r'infoId=(\d+)', href); iid = m.group(1) if m else ""
            m = re.search(r'channelCode=(\w+)', href); ch = m.group(1) if m else ""
        atype = ""
        p = li.find("p")
        if p:
            for sp in p.find_all("span", class_="Right10"):
                txt = sp.get_text(strip=True)
                if "公告类型" in txt:
                    b = sp.find("span", class_="Blue"); atype = b.get_text(strip=True) if b else ""
        results.append({"title": title, "info_id": iid, "channel_code": ch,
                        "announce_type": atype,
                        "detail_url": f"{BASE_URL}{href}" if href else ""})
    return results


def fetch_page(session, so_code, page_no):
    for _ in range(3):
        try:
            r = session.get(f"{BASE_URL}/henan/ggcx",
                params={"appCode": "H60", "pageSize": "15", "soCode": so_code, "pageNo": str(page_no)},
                timeout=(10, 20)); r.encoding = "utf-8"
            if "访问频繁" in r.text: time.sleep(10); continue
            if "cgxxForm" in r.text and "infoId=" not in r.text: return None
            return parse_list(r.text)
        except Exception:
            time.sleep(5)
    return []


def fetch_detail(session, url):
    try:
        r = safe_get(session, url); r.encoding = "utf-8"
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
            m = re.search(p, t);
            if m: result[k] = m.group(1).strip()
    for s in soup.find_all("script"):
        if s.string and "$.get" in s.string and ".htm" in s.string:
            m = re.search(r'\$\.get\("([^"]+\.htm)"', s.string)
            if m:
                result["content_url"] = f"{BASE_URL}{m.group(1)}" if m.group(1).startswith("/") else m.group(1)
                break
    ad = soup.find("div", class_="List1")
    if ad:
        atts = [{"name": a.get_text(strip=True), "url": (f"{BASE_URL}{a.get('href')}" if a.get("href","").startswith("/") else a.get("href",""))}
                for a in ad.find_all("a") if a.get("href")]
        if atts: result["attachments"] = atts
    return result


def fetch_body(session, url):
    try:
        return safe_get(session, url).text
    except Exception as e:
        return f"[失败: {e}]"


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return None


def save_progress(state):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(state, f)


def main():
    import sys
    TIME_TYPE = sys.argv[1] if len(sys.argv) > 1 else "2"
    labels = {"0": "今日", "1": "近1周", "2": "近1月"}
    print("=" * 55)
    print(f"河南省政府采购网 v6 - {labels.get(TIME_TYPE, TIME_TYPE)}")
    print("=" * 55)

    # 检查断点
    progress = load_progress()
    if progress and progress.get("phase") == "detail":
        print(f"\n[断点续传] 从第 {progress['next_idx']+1}/{progress['total_items']} 条继续\n")
        session = new_session()
        items = progress["items"]
        start_idx = progress["next_idx"]
    else:
        # ==== Phase 1: List ====
        print("\n[Phase 1] 列表采集")
        session = new_session()
        so_code, p1, total_pages = solve_captcha(session, TIME_TYPE)
        all_items = list(p1)
        for p in range(2, total_pages + 1):
            items = fetch_page(session, so_code, p)
            if items is None:
                print("  soCode过期，重新验证...")
                session = new_session()
                so_code, _, _ = solve_captcha(session, TIME_TYPE)
                items = fetch_page(session, so_code, p) or []
            all_items.extend(items)
            if p % 30 == 0: print(f"    {p}/{total_pages} ({len(all_items)}条)")
            time.sleep(2)
        print(f"  列表完成: {len(all_items)} 条")

        # ==== Filter ====
        print("\n[Filter] 医疗设备筛选")
        items = []
        for d in all_items:
            ok, eq, inst = is_medical(d["title"], "", d.get("announce_type", ""))
            if ok: d["matched_eq"] = eq; d["matched_inst"] = inst; items.append(d)
        print(f"  命中: {len(items)} 条")
        start_idx = 0

    # ==== Phase 2: Detail + Body (分批) ====
    print(f"\n[Phase 2] 详情+正文 ({len(items)}条, 每{BATCH_SIZE}条存盘)\n")
    for i in range(start_idx, len(items)):
        d = items[i]
        if i % BATCH_SIZE == 0 or i == len(items) - 1:
            print(f"  {i+1}/{len(items)}...", end=" ", flush=True)

        # Detail
        detail = fetch_detail(session, d["detail_url"])
        for k in ["title_detail", "agency", "pub_time", "views", "content_url", "attachments"]:
            if detail.get(k):
                d[k if k != "title_detail" else "title"] = detail[k] if k != "title_detail" else detail[k]

        # 二次确认
        if d.get("body_html") is None and not d.get("matched_eq"):
            d.setdefault("body_html", "")  # placeholder

        time.sleep(3)

        # Body
        if d.get("content_url"):
            try:
                d["body_html"] = fetch_body(session, d["content_url"])
            except Exception as e:
                d["body_html"] = f"[失败: {e}]"
            time.sleep(3)

        if i % BATCH_SIZE == BATCH_SIZE - 1 or i == len(items) - 1:
            # 立即保存进度
            print(f"保存...", end=" ", flush=True)
            categorized = categorize(items)
            output = {"summary": {"total_matched": len(items), "categories": {k: len(v) for k, v in categorized.items()}}, "items": items}
            with open(FULL_OUTPUT, "w") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            save_progress({"phase": "detail", "next_idx": i + 1, "total_items": len(items), "items": items})
            # 重建session防止代理连接僵死
            session = new_session()
            print("✓")

    # 清理
    if os.path.exists(PROGRESS_FILE): os.remove(PROGRESS_FILE)

    # ==== Final ====
    categorized = categorize(items)
    print(f"\n{'='*55}")
    print(f"完成! {len(items)} 条 → {FULL_OUTPUT}")
    for k, v in categorized.items():
        print(f"  {k}: {len(v)} 条")
    # 预览
    print("\n--- 前3条 ---")
    for d in items[:3]:
        body = d.get("body_html", "")
        body_preview = re.sub(r'<[^>]+>', ' ', body[:300]).strip()[:80] if body else "(无)"
        print(f"  [{d.get('pub_time','?')}] [{d.get('announce_type','?')}] {d['title'][:60]}...")
        print(f"    匹配: {d.get('matched_eq',[])[:4]} | 正文: {body_preview}...")


def categorize(items):
    cats = {"招标": [], "中标": [], "终止": [], "其他": []}
    for d in items:
        at = d.get("announce_type", "")
        if at in ("采购公告", "采购意向"): cats["招标"].append(d)
        elif at in ("结果公告", "合同公告"): cats["中标"].append(d)
        elif at in ("废标公告", "变更公告"): cats["终止"].append(d)
        else: cats["其他"].append(d)
    return cats


if __name__ == "__main__":
    main()
