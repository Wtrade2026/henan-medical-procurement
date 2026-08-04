"""信源平台爬虫 — 开封、濮阳等公共资源交易中心（非Epoint系）"""
import re, time, requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def crawl_xinyuan(source, config):
    """爬取信源平台的公告列表（服务端渲染，index_N.jhtml分页）"""
    base = source["base_url"].rstrip("/")
    prefix = source.get("prefix", "/zcgkfs/")  # e.g. /zcgkfs/ for 采购公告
    session = requests.Session()
    session.headers.update(HEADERS)

    all_items = []
    page = 1
    total_pages = 9999  # will be set from first page

    while page <= total_pages:
        if page == 1:
            url = f"{base}{prefix}index.jhtml"
        else:
            url = f"{base}{prefix}index_{page}.jhtml"

        try:
            r = session.get(url, timeout=(10, 20))
            r.encoding = "utf-8"
        except Exception as e:
            print(f"    ⚠️ 第{page}页请求失败: {e}")
            break

        if r.status_code != 200:
            print(f"    ⚠️ 第{page}页 HTTP {r.status_code}")
            break

        soup = BeautifulSoup(r.text, "html.parser")

        # First page: extract total pages
        if page == 1:
            match = re.search(r'共\s*(\d+)\s*条记录\s*[\d]+/(\d+)页', r.text)
            if match:
                total_records = int(match.group(1))
                total_pages = int(match.group(2))
                print(f"    共 {total_records} 条, {total_pages} 页")
            else:
                page_links = re.findall(r'index_(\d+)\.jhtml', r.text)
                if page_links:
                    total_pages = max(int(p) for p in page_links)
                else:
                    total_pages = 1
                print(f"    检测到 {total_pages} 页")

        # Parse items from infolist div
        list_div = soup.find("div", class_="infolist")
        if not list_div:
            list_div = soup.find("div", class_="infolist-main")
        if not list_div:
            print(f"    ⚠️ 第{page}页无列表数据")
            break

        links = list_div.find_all("a")
        page_items = 0
        for a in links:
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if not href or not text:
                continue
            # href: /zcgkfs/81221.jhtml
            id_match = re.search(r'/(\d+)\.jhtml', href)
            if not id_match:
                continue
            item_id = id_match.group(1)

            # text format: "title2026-08-04" or "title 2026-08-04"
            # Date is YYYY-MM-DD at the end
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})\s*$', text)
            if date_match:
                pub_date = date_match.group(1)
                title = text[:date_match.start()].strip()
            else:
                pub_date = ""
                title = text

            abs_url = href if href.startswith("http") else f"{base}{href}"
            all_items.append({
                "title": title,
                "info_id": f"kf_{item_id}",
                "pub_date": pub_date,
                "detail_url": abs_url,
                "source": source["name"],
                "city": source.get("city", "开封"),
            })
            page_items += 1

        print(f"    第{page}页: {page_items} 条")

        if page_items == 0:
            break

        page += 1
        time.sleep(1)  # polite delay

    print(f"    总计: {len(all_items)} 条")
    return all_items


def fetch_xinyuan_detail(session, item):
    """抓取信源平台详情页"""
    url = item.get("detail_url", "")
    if not url:
        return item

    try:
        r = session.get(url, timeout=(10, 20))
        r.encoding = "utf-8"
    except Exception:
        return item

    soup = BeautifulSoup(r.text, "html.parser")

    # Title — try breadcrumb last segment first
    for td in soup.find_all("td", class_=True):
        cls = " ".join(td.get("class", []))
        if "position" in cls.lower() or "location" in cls.lower():
            links = td.find_all("a")
            if links:
                item["title"] = links[-1].get_text(strip=True)
            break

    # Content
    content_div = soup.find("div", class_="s_content")
    if not content_div:
        content_div = soup.find("div", class_="Contnet")
    if content_div:
        item["body_html"] = str(content_div)

    # Meta: publish time 发布时间：2026-08-04 16:08:52
    text = soup.get_text()
    m = re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2})', text)
    if m:
        item["pub_time"] = m.group(1).strip()

    # Agency: 采购人信息 名称：XXX
    m = re.search(r'采购人信息\s*名称[：:]\s*(.+?)(?:\n|$)', text)
    if m:
        item["agency"] = m.group(1).strip()

    # Announce type from breadcrumb
    m = re.search(r'交易信息\s*[>>]+\s*政府采购\s*[>>]+\s*(\S+?)\s*[>>]', text)
    if m:
        item["announce_type"] = m.group(1)

    return item
