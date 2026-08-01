#!/usr/bin/env python3
"""
河南省医疗设备招投标爬虫 - 省网单入口
====================================
省网 /henan/ggcx 搜索一次返回全省公告，无需逐市爬取。

用法:
  python3 crawler_province.py 0   # 今日
  python3 crawler_province.py 1   # 近1周 (默认)
  python3 crawler_province.py 2   # 近1月

关键点:
  - 省网 ggcx 聚合全省，一次搜索覆盖 18 市
  - 翻页 GET ggcx?appCode=H60&pageSize=15&soCode={so}&pageNo={N}
  - 限流: 间隔≥3秒，命中"访问频繁"等待30秒重试
  - 城市标注: 优先 region 字段，其次 channelCode 前缀，不信任子站名
"""

import requests, ddddocr, re, json, time, os, socket, sys
from bs4 import BeautifulSoup

socket.setdefaulttimeout(25)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(SCRIPT_DIR, "henan_medical_full.json")

# ==================== 省网固定入口 ====================
BASE_URL = "https://zfcg.henan.gov.cn"
PATH = "henan"          # 省网主路径（聚合全省）
GGCX_URL = f"{BASE_URL}/{PATH}/ggcx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": GGCX_URL,
}

# ==================== 医疗关键词过滤 ====================
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


# ==================== 城市反推 ====================
ALL_CITIES = ["郑州", "开封", "洛阳", "平顶山", "安阳", "鹤壁", "新乡", "焦作", "濮阳",
              "许昌", "漯河", "三门峡", "南阳", "商丘", "信阳", "周口", "驻马店", "济源"]

# H 系列前缀 → 地市（省级/市直）
CITY_CODE_MAP = {
    "H60": "省级", "H61": "郑州", "H62": "开封", "H63": "开封",
    "H64": "洛阳", "H65": "平顶山", "H66": "安阳", "H67": "鹤壁",
    "H68": "新乡", "H69": "焦作", "H70": "濮阳", "H71": "许昌",
    "H72": "漯河", "H73": "三门峡", "H74": "南阳", "H75": "商丘",
    "H76": "信阳", "H77": "周口", "H78": "驻马店", "H79": "济源",
}

# content_url 的 slug 前缀 → 地市（处理 pdsyx/pdsslq/lyssx 等缩写变体）
# key 为 slug，值为中文地市名
CITY_SLUGS = {
    "zhengzhou": "郑州", "zz": "郑州", "jinshui": "郑州", "shangjie": "郑州", "hkgq": "郑州",
    "kaifeng": "开封",
    "luoyang": "洛阳", "lys": "洛阳",
    "pingdingshan": "平顶山", "pds": "平顶山",
    "anyang": "安阳", "ay": "安阳",
    "hebi": "鹤壁", "hb": "鹤壁",
    "xinxiang": "新乡", "xxs": "新乡",
    "jiaozuo": "焦作", "jzs": "焦作",
    "puyang": "濮阳", "py": "濮阳",
    "xuchang": "许昌",
    "luohe": "漯河", "lh": "漯河",
    "sanmenxia": "三门峡", "smx": "三门峡",
    "nanyang": "南阳", "ny": "南阳",
    "shangqiu": "商丘", "sqs": "商丘", "ycs": "商丘",
    "xinyang": "信阳", "xy": "信阳",
    "zhoukou": "周口", "zk": "周口",
    "zhumadian": "驻马店", "zmd": "驻马店",
    "jiyuan": "济源",
    "henan": "省级",
}

# 中文县区名 → 地市（用于 region/agency 字段匹配）
COUNTY_NAME_CITY = {
    "中牟": "郑州", "登封": "郑州", "巩义": "郑州", "荥阳": "郑州", "新密": "郑州", "新郑": "郑州",
    "兰考": "开封", "杞县": "开封", "通许": "开封", "尉氏": "开封",
    "偃师": "洛阳", "孟津": "洛阳", "新安": "洛阳", "栾川": "洛阳", "嵩县": "洛阳", "汝阳": "洛阳", "宜阳": "洛阳", "洛宁": "洛阳", "伊川": "洛阳",
    "汝州": "平顶山", "舞钢": "平顶山", "宝丰": "平顶山", "叶县": "平顶山", "郏县": "平顶山", "鲁山": "平顶山",
    "林州": "安阳", "滑县": "安阳", "汤阴": "安阳", "内黄": "安阳",
    "浚县": "鹤壁", "淇县": "鹤壁",
    "辉县": "新乡", "卫辉": "新乡", "延津": "新乡", "封丘": "新乡", "获嘉": "新乡", "原阳": "新乡", "长垣": "新乡",
    "温县": "焦作", "武陟": "焦作", "修武": "焦作", "博爱": "焦作", "沁阳": "焦作", "孟州": "焦作",
    "清丰": "濮阳", "南乐": "濮阳", "台前": "濮阳", "范县": "濮阳",
    "禹州": "许昌", "长葛": "许昌", "鄢陵": "许昌", "襄城": "许昌",
    "临颍": "漯河", "舞阳": "漯河",
    "义马": "三门峡", "灵宝": "三门峡", "渑池": "三门峡", "卢氏": "三门峡", "陕州": "三门峡",
    "镇平": "南阳", "唐河": "南阳", "新野": "南阳", "内乡": "南阳", "西峡": "南阳", "淅川": "南阳", "社旗": "南阳", "方城": "南阳", "桐柏": "南阳", "邓州": "南阳", "南召": "南阳",
    "虞城": "商丘", "永城": "商丘", "夏邑": "商丘", "睢县": "商丘", "宁陵": "商丘", "民权": "商丘", "柘城": "商丘", "梁园": "商丘", "睢阳": "商丘",
    "潢川": "信阳", "罗山": "信阳", "光山": "信阳", "新县": "信阳", "商城": "信阳", "固始": "信阳", "息县": "信阳", "淮滨": "信阳", "浉河": "信阳", "平桥": "信阳",
    "项城": "周口", "扶沟": "周口", "鹿邑": "周口", "郸城": "周口", "太康": "周口", "沈丘": "周口", "淮阳": "周口", "西华": "周口", "商水": "周口",
    "确山": "驻马店", "泌阳": "驻马店", "正阳": "驻马店", "新蔡": "驻马店", "上蔡": "驻马店", "西平": "驻马店", "平舆": "驻马店", "遂平": "驻马店", "汝南": "驻马店",
    "上街": "郑州", "航空港": "郑州", "管城": "郑州", "中原": "郑州", "二七": "郑州", "金水": "郑州", "惠济": "郑州",
}

# 常见县区 → 地市（用于 content_url 路径反推）
# 注意：qixian 歧义（淇县=鹤壁 vs 杞县=开封），由 channelCode 兜底
COUNTY_CITY = {
    "xinzheng": "郑州", "zhongmu": "郑州", "zhongmou": "郑州", "dengfeng": "郑州", "xingyang": "郑州", "xinsi": "郑州", "gongyi": "郑州",
    "weishi": "开封", "qixian": "开封", "lankao": "开封", "tongxu": "开封", "yuxian": "开封",
    "yanshi": "洛阳", "mengjin": "洛阳", "xinan": "洛阳", "luanchuan": "洛阳", "songxian": "洛阳", "ruyang": "洛阳", "yiyang": "洛阳", "luoning": "洛阳", "yichuan": "洛阳",
    "lyslcx": "洛阳", "lyslnx": "洛阳", "lysyyx": "洛阳", "lysxax": "洛阳", "lysmjx": "洛阳", "lysybq": "洛阳", "lyssx": "洛阳",
    "ruzhou": "平顶山", "wugang": "平顶山", "baofeng": "平顶山", "yexian": "平顶山", "jiaxiang": "平顶山", "lushan": "平顶山",
    "pdsyx": "平顶山", "pdsjx": "平顶山", "pdsslq": "平顶山", "pdsxcq": "平顶山", "pdswdq": "平顶山", "pdsxhq": "平顶山",
    "linzhou": "安阳", "huaxian": "安阳", "tangyin": "安阳", "neihuang": "安阳", "anyangxian": "安阳",
    "xunxian": "鹤壁", "qixian": "鹤壁",
    "huixian": "新乡", "weihui": "新乡", "yanjin": "新乡", "fengqiu": "新乡", "huojia": "新乡", "yuanyang": "新乡", "changyuan": "新乡",
    "wenxian": "焦作", "wuzhi": "焦作", "xiuwu": "焦作", "boai": "焦作", "qinyang": "焦作", "mengzhou": "焦作",
    "qingfeng": "濮阳", "nanle": "濮阳", "taiquan": "濮阳", "fanxian": "濮阳", "puyangxian": "濮阳", "pystqx": "濮阳",
    "yuzhou": "许昌", "changge": "许昌", "yanling": "许昌", "xiangcheng": "许昌",
    "linshan": "漯河", "wuyang": "漯河",
    "yima": "三门峡", "lingbao": "三门峡", "mianchi": "三门峡", "lushi": "三门峡", "shanzhou": "三门峡",
    "zhenping": "南阳", "tanghe": "南阳", "xinye": "南阳", "neixiang": "南阳", "xixia": "南阳", "xichuan": "南阳", "sheqi": "南阳", "fangcheng": "南阳", "tongbai": "南阳", "dengzhou": "南阳",
    "yucheng": "商丘", "yongcheng": "商丘", "xiayi": "商丘", "suixian": "商丘", "ningling": "商丘", "minquan": "商丘", "zhecheng": "商丘",
    "sqsmqx": "商丘", "sqsxyx": "商丘",
    "huangchuan": "信阳", "luoshan": "信阳", "guangshan": "信阳", "xinxian": "信阳", "shangcheng": "信阳", "gushi": "信阳", "xixian": "信阳", "huaihe": "信阳",
    "xiangcheng": "周口", "fugou": "周口", "luyi": "周口", "dancheng": "周口", "taikang": "周口", "shenqiu": "周口", "huaiyang": "周口", "xihua": "周口",
    "queshan": "驻马店", "biyang": "驻马店", "zhengyang": "驻马店", "xincai": "驻马店", "shangcai": "驻马店", "xiping": "驻马店", "pingyu": "驻马店", "suiping": "驻马店",
    "jiyuan": "济源",
}


def fix_city(item):
    """从 region + agency + channelCode + content_url 推断真实城市（不信任子站名）"""
    # 1. region 字段直接匹配（列表页"区域"标签，最可靠）
    region = item.get("region", "") or ""
    for cn in ALL_CITIES:
        if cn in region:
            return cn
    # 1b. region 含县名 → 映射到地市
    for county, city in COUNTY_NAME_CITY.items():
        if county in region:
            return city
    if region and "河南" in region and "市" not in region:
        return "省级"

    # 2. agency 发布机构匹配（如"滑县卫生健康委员会"、"镇平县人民医院"）
    agency = item.get("agency", "") or ""
    for cn in ALL_CITIES:
        if cn in agency:
            return cn
    # 2b. agency 含县名 → 映射到地市
    for county, city in COUNTY_NAME_CITY.items():
        if county in agency:
            return city

    # 3. channelCode 前缀（H 系列前2位 = 地市）
    cc = item.get("channel_code", "") or ""
    for prefix in ("H60", "H61", "H62", "H63", "H64", "H65", "H66", "H67",
                   "H68", "H69", "H70", "H71", "H72", "H73", "H74", "H75",
                   "H76", "H77", "H78", "H79"):
        if cc.startswith(prefix):
            return CITY_CODE_MAP[prefix]

    # 4. content_url 路径 slug 反推（/huaxian/ → 滑县 → 安阳）
    cu = item.get("content_url", "") or ""
    m = re.search(r'/cmsweb[^/]+/([a-z0-9]+)/', cu)
    if m:
        sub = m.group(1)
        # 先精确匹配已知县区 slug
        for county, city in COUNTY_CITY.items():
            if county == sub:
                return city
        # 再精确匹配地市 slug
        if sub in CITY_SLUGS:
            return CITY_SLUGS[sub]
        # 最后尝试 slug 前缀匹配（pdsyx=平顶山叶县, lyssx=洛阳嵩县, sqsmqx=商丘民权）
        # 仅匹配 ≥3 字母的前缀，避免误匹配
        for sl, cn in sorted(CITY_SLUGS.items(), key=lambda x: -len(x[0])):
            if len(sl) >= 3 and sub.startswith(sl):
                return cn

    # 5. 兜底
    return "未知"


# ==================== 请求工具（复用自 crawler_city.py） ====================
def new_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def solve_captcha(session, time_type="1"):
    """打开省网 ggcx，解验证码提交搜索，返回 (soCode, 第一页items, 总页数)"""
    ocr = ddddocr.DdddOcr(show_ad=False)

    for _ in range(15):
        session.cookies.clear()
        try:
            r = session.get(GGCX_URL, timeout=(10, 20))
            r.encoding = "utf-8"
        except Exception:
            time.sleep(3)
            continue

        tm = re.search(r'getImage/([a-f0-9]+)', r.text)
        sm = re.search(r'soCode=([a-f0-9]+)', r.text)
        if not tm or not sm: continue

        try:
            img = session.get(f"{BASE_URL}/{PATH}/getImage/{tm.group(1)}", timeout=(5, 10))
            code = ocr.classification(img.content)
        except Exception:
            continue

        form = {"bidType": "0", "timeType": time_type, "fromtime": "", "endtime": "",
                "title": "", "croporgan_name": "", "project_no": "",
                "gpmethod": "", "agency_name": "", "code": code}

        try:
            r2 = session.post(f"{GGCX_URL}?soCode={sm.group(1)}", data=form, timeout=(10, 20))
            r2.encoding = "utf-8"
        except Exception:
            continue

        if "访问频繁" in r2.text:
            print("  [限流] 等待30秒...")
            time.sleep(30)
            continue

        if "errCode=1" not in r2.url:
            items = parse_list(r2.text)
            # 检测无结果："您共搜到0条内容"
            if "共搜到0条" in r2.text or "搜到0条" in r2.text:
                return sm.group(1), [], 0
            p = re.search(r'共\s*(\d+)\s*页', r2.text)
            total = int(p.group(1)) if p else 1
            return sm.group(1), items, total

        time.sleep(2)

    raise Exception("验证码失败")


def parse_list(html):
    """解析列表页，提取公告（保留 region 字段用于城市反推）"""
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
        results.append({
            "title": title, "info_id": iid.group(1) if iid else "",
            "channel_code": ch.group(1) if ch else "",
            "announce_type": atype, "region": region,
            "detail_url": abs_url,
        })
    return results


def fetch_page(session, so_code, page_no):
    """慢速翻页，带限流检测（间隔由调用方控制）"""
    params = {"appCode": "H60", "pageSize": "15", "soCode": so_code, "pageNo": str(page_no)}
    h_xhr = dict(HEADERS)
    h_xhr["X-Requested-With"] = "XMLHttpRequest"
    for attempt in range(3):
        try:
            r = session.get(GGCX_URL, params=params, headers=h_xhr, timeout=(10, 20))
            r.encoding = "utf-8"
            if "访问频繁" in r.text:
                wait = 60 if attempt < 2 else 90
                print(f"    [限流] 第{page_no}页 尝试{attempt+1}/3, 等待{wait}秒...")
                time.sleep(wait)
                continue
            if "cgxxForm" in r.text and "infoId=" not in r.text:
                return None
            return parse_list(r.text)
        except Exception:
            time.sleep(8)
    return []


def fetch_detail(session, detail_url):
    """抓取详情页元信息"""
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


# ==================== 主流程 ====================
def crawl_all(time_type):
    """单入口爬全省，返回医疗设备列表"""
    session = new_session()

    print(f"\n{'='*55}")
    print(f"🕸️  河南省政府采购网 - 省网单入口")
    print(f"    {GGCX_URL}")
    print(f"{'='*55}")

    # Phase 1: 搜索列表
    try:
        so_code, p1, total = solve_captcha(session, time_type)
    except Exception as e:
        print(f"  ❌ 验证码失败: {e}")
        return []

    all_items = list(p1)
    print(f"  共 {total} 页")

    if total == 0:
        print("  ℹ️ 该时间段无公告（0条），跳过翻页")
        return []

    rate_limited = 0   # 连续限流计数
    for p in range(2, total + 1):
        items = fetch_page(session, so_code, p)
        if items is None:
            # 会话失效，重建
            print(f"    [会话失效] 第{p}页, 等待20秒后重新验证码...")
            time.sleep(20)
            session = new_session()
            try:
                so_code, p1, total = solve_captcha(session, time_type)
            except Exception:
                break
            items = list(p1)
        if not items:
            # 翻页失败（限流或异常）
            rate_limited += 1
            if rate_limited >= 5:
                print(f"  ⚠️ 连续 {rate_limited} 页失败（可能限流），提前停止翻页")
                break
        else:
            rate_limited = 0
        all_items.extend(items)
        if p % 10 == 0:
            print(f"    {p}/{total} ({len(all_items)}条)")
        time.sleep(5)  # 限流缓冲

    print(f"  列表: {len(all_items)} 条")

    # Phase 2: 过滤医疗 + 城市标注
    medical = []
    seen_ids = set()
    for d in all_items:
        ok, eq = is_medical(d["title"])
        if not ok: continue
        iid = d.get("info_id", "")
        if iid and iid in seen_ids: continue  # 省网去重
        if iid: seen_ids.add(iid)
        d["matched_eq"] = eq
        d["city"] = fix_city(d)  # 反推真实城市
        medical.append(d)

    print(f"  医疗: {len(medical)} 条")

    # Phase 3: 详情 + 正文
    for i, d in enumerate(medical):
        detail_url = d["detail_url"]
        if detail_url and not detail_url.startswith("http"):
            detail_url = f"{BASE_URL}{detail_url}" if detail_url.startswith("/") else f"{BASE_URL}/{detail_url}"
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

            # 详情抓取后无条件重算城市（此时有 agency + content_url，最可靠）
            new_city = fix_city(d)
            if new_city != "未知":
                d["city"] = new_city

            if d.get("content_url"):
                d["body_html"] = fetch_body(session, d["content_url"])
                time.sleep(2)

        if (i + 1) % 10 == 0:
            print(f"    详情: {i+1}/{len(medical)}")

    return medical


def main():
    TIME_TYPE = sys.argv[1] if len(sys.argv) > 1 else "1"
    labels = {"0": "今日", "1": "近1周", "2": "近1月"}

    # 省网"今日"(timeType=0) 通常返回0条，回退到近1周保证有数据
    if TIME_TYPE == "0":
        print("⚠️ 省网今日(timeType=0)常无数据，回退到近1周(timeType=1)")
        TIME_TYPE = "1"

    print(f"河南省医疗设备招投标爬虫 - 省网单入口 [{labels.get(TIME_TYPE, TIME_TYPE)}]")

    # 加载已有数据
    existing = []
    if os.path.exists(OUTPUT) and os.path.getsize(OUTPUT) > 100:
        with open(OUTPUT) as f:
            existing = json.load(f).get("items", [])
    existing_ids = {d.get("info_id") for d in existing if d.get("info_id")}

    all_medical = crawl_all(TIME_TYPE)

    # 合并旧数据（保留历史）
    new_ids = {d.get("info_id") for d in all_medical if d.get("info_id")}
    merged = list(all_medical)
    for d in existing:
        iid = d.get("info_id")
        if iid and iid not in new_ids:
            merged.append(d)

    # 分类
    cats = {"招标": 0, "中标": 0, "终止": 0, "其他": 0}
    for d in merged:
        at = d.get("announce_type", "")
        if at in ("采购公告", "采购意向"): d["category"] = "招标"; cats["招标"] += 1
        elif at in ("结果公告", "合同公告"): d["category"] = "中标"; cats["中标"] += 1
        elif at in ("废标公告", "变更公告"): d["category"] = "终止"; cats["终止"] += 1
        else: d["category"] = "其他"; cats["其他"] += 1

    # 城市统计
    from collections import Counter
    city_cnt = Counter(d.get("city", "未知") for d in merged)

    output = {"summary": {"total": len(merged), "categories": cats, "cities": len(city_cnt)}, "items": merged}
    with open(OUTPUT, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"✅ 完成! 共 {len(merged)} 条 (本次采集 {len(all_medical)} 条)")
    print(f"   分类:")
    for k, v in cats.items():
        print(f"     {k}: {v}")
    print(f"   城市分布:")
    for c, n in city_cnt.most_common():
        print(f"     {c}: {n}")
    print(f"   保存到: {OUTPUT}")


if __name__ == "__main__":
    main()
