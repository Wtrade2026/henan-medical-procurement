"""Epoint/国泰新点平台爬虫 — 省交易中心、Anyang、南阳、郑州等（REST API）"""
import json, time, requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}

PAGE_SIZE = 15  # items per page
MAX_PAGES = 20  # safety limit before captcha kicks in (typically page 6+)


def crawl_epoint(source, config):
    """爬取 Epoint 平台的公告列表（REST API JSON）"""
    base = source["base_url"].rstrip("/")
    project_name = source.get("project_name", "/EpointWebBuilder")
    site_guid = source.get("site_guid", "")
    category = source.get("category", "002005001")  # default: 医药采购公告
    xiaqucode = source.get("xiaqucode", "")

    session = requests.Session()
    session.headers.update(HEADERS)

    api_url = f"{base}{project_name}/rest/frontAppCustomAction/getPageInfoListNewYzm"
    all_items = []

    print(f"    分类: {category}")

    for page in range(MAX_PAGES):
        data = {
            "siteGuid": site_guid,
            "categoryNum": category,
            "kw": "",
            "startDate": "",
            "endDate": "",
            "pageIndex": page,
            "pageSize": PAGE_SIZE,
            "jytype": "",
        }
        if xiaqucode:
            data["xiaqucode"] = xiaqucode

        try:
            r = session.post(api_url, data=data, timeout=(10, 20),
                           headers={"Referer": f"{base}/"})
            r.encoding = "utf-8"
        except Exception as e:
            print(f"    ⚠️ 第{page+1}页请求失败: {e}")
            break

        if r.status_code != 200:
            print(f"    ⚠️ 第{page+1}页 HTTP {r.status_code}")
            break

        try:
            resp = json.loads(r.text)
        except json.JSONDecodeError:
            print(f"    ⚠️ 第{page+1}页 JSON解析失败")
            break

        custom = resp.get("custom", {})
        items = custom.get("infodata", [])
        total = custom.get("count", 0)

        if page == 0:
            print(f"    共 {total} 条")

        if not items:
            break

        for item in items:
            detail_url = item.get("infourl", "")
            if detail_url and not detail_url.startswith("http"):
                detail_url = f"{base}{detail_url}"
            all_items.append({
                "title": item.get("title", ""),
                "info_id": f"ep_{item.get('infoid', '')}",
                "pub_date": item.get("infodate", ""),
                "detail_url": detail_url,
                "announce_type": item.get("categoryname", ""),
                "source": source["name"],
                "city": source.get("city", ""),
            })

        if (page + 1) % 5 == 0:
            print(f"    第{page+1}页: {len(all_items)} 条 (共{total})")
        time.sleep(1)

    print(f"    总计: {len(all_items)} 条")
    return all_items


def fetch_epoint_detail(session, item):
    """抓取 Epoint 详情页"""
    url = item.get("detail_url", "")
    if not url:
        return item

    try:
        r = session.get(url, timeout=(10, 20))
        r.encoding = "utf-8"
    except Exception:
        return item

    from bs4 import BeautifulSoup
    import re
    soup = BeautifulSoup(r.text, "html.parser")

    # Title
    h1 = soup.find("h1") or soup.find("h2") or soup.find("h3")
    if h1:
        item["title"] = h1.get_text(strip=True)

    # Meta info
    text = soup.get_text()
    m = re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})', text)
    if m:
        item["pub_time"] = m.group(1).strip()
    m = re.search(r'(?:发布机构|采购人|招标人|招标单位)[：:]\s*(.+?)(?:\n|$)', text)
    if m:
        item["agency"] = m.group(1).strip()
    m = re.search(r'(?:代理机构|采购代理)[：:]\s*(.+?)(?:\n|$)', text)
    if m:
        item["procurement_agent"] = m.group(1).strip()

    # Body
    content = soup.find("div", class_="epoint-article-content") or \
              soup.find("div", class_="article-content") or \
              soup.find("div", class_="content") or \
              soup.find("div", id="Content")
    if content:
        item["body_html"] = str(content)

    return item
