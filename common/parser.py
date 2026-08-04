"""列表页/详情页解析"""
import re, time
from bs4 import BeautifulSoup


def parse_list(html):
    """解析列表页，提取公告（保留 region 字段用于城市反推）"""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for li in soup.select("div.List2 ul li"):
        a = li.find("a")
        if not a:
            continue
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
        abs_url = href if href.startswith("http") else ""
        if not abs_url:
            abs_url = href
        results.append({
            "title": title, "info_id": iid.group(1) if iid else "",
            "channel_code": ch.group(1) if ch else "",
            "announce_type": atype, "region": region,
            "detail_url": abs_url,
        })
    return results


def fetch_page(session, base_url, path, so_code, page_no, headers):
    """慢速翻页，带限流检测"""
    import requests
    ggcx_url = f"{base_url}/{path}/ggcx"
    params = {"appCode": "H60", "pageSize": "15", "soCode": so_code, "pageNo": str(page_no)}
    h_xhr = dict(headers)
    h_xhr["X-Requested-With"] = "XMLHttpRequest"
    for attempt in range(3):
        try:
            r = session.get(ggcx_url, params=params, headers=h_xhr, timeout=(10, 20))
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
    import requests
    try:
        r = session.get(detail_url, timeout=(10, 20))
        r.encoding = "utf-8"
    except Exception:
        return {}
    soup = BeautifulSoup(r.text, "html.parser")
    result = {}
    h1 = soup.find("h1")
    if h1:
        result["title_detail"] = h1.get_text(strip=True)
    md = soup.find("div", class_="TxtCenter")
    if md:
        t = md.get_text()
        for k, p in [("agency", r'发布机构[：:]\s*(.+?)(?:&nbsp;|\s{2,})'),
                     ("pub_time", r'发布日期[：:]\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})'),
                     ("views", r'访问次数[：:]\s*(\d+)')]:
            m = re.search(p, t)
            if m:
                result[k] = m.group(1).strip()
    for s in soup.find_all("script"):
        if s.string and ".htm" in (s.string or ""):
            m = re.search(r'\$\.get\("([^"]+\.htm)"', s.string)
            if m:
                cu = m.group(1)
                if cu.startswith("/"):
                    result["content_url"] = f"https://{cu.lstrip('/')}" if "//" in cu else cu
                elif cu.startswith("http"):
                    result["content_url"] = cu
    return result


def fetch_body(session, url):
    """抓取正文HTML"""
    import requests
    try:
        if not url.startswith("http"):
            return ""
        return session.get(url, timeout=(10, 20)).text
    except Exception:
        return ""
