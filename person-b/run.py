#!/usr/bin/env python3
"""个人招投标数据采集程序 — 双击运行或 python run.py"""
import sys, os, json, time, socket
from collections import Counter

# 确保可以导入同级的 common 模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from common.captcha import new_session, solve_captcha
from common.parser import parse_list, fetch_page, fetch_detail, fetch_body
from common.filter import is_medical
from common.city import fix_city
from common.classify import classify
from common.io import load_existing, save_output, merge_items

socket.setdefaulttimeout(25)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}


def load_config():
    config_path = os.path.join(SCRIPT_DIR, 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_by_config(items, config):
    mode = config.get('filter_mode', 'all')
    if mode == 'provincial_only':
        return [d for d in items if d.get('city') == '省级']
    elif mode == 'city_list':
        allowed = set(config.get('my_cities', []))
        return [d for d in items if d.get('city') in allowed]
    return items


def crawl_source(source, config):
    base_url = source['base_url']
    path = source['path']
    time_type = str(config.get('time_range', 1))

    headers = dict(HEADERS)
    headers["Referer"] = f"{base_url}/{path}/ggcx"

    print(f"\n  → {source['name']}")
    print(f"    {base_url}/{path}/ggcx")

    session = new_session(headers)
    try:
        so_code, p1, total = solve_captcha(session, base_url, path, time_type, headers)
    except Exception as e:
        print(f"    ❌ 验证码失败: {e}")
        return []

    all_items = list(p1)
    print(f"    共 {total} 页")

    if total == 0:
        print("    ℹ️ 该时间段无公告")
        return []

    rate_limited = 0
    for p in range(2, total + 1):
        items = fetch_page(session, base_url, path, so_code, p, headers)
        if items is None:
            print(f"    [会话失效] 第{p}页, 等待20秒...")
            time.sleep(20)
            session = new_session(headers)
            try:
                so_code, p1, total = solve_captcha(session, base_url, path, time_type, headers)
            except Exception:
                break
            items = list(p1)
        if not items:
            rate_limited += 1
            if rate_limited >= 5:
                print(f"    ⚠️ 连续 {rate_limited} 页失败，提前停止")
                break
        else:
            rate_limited = 0
        all_items.extend(items)
        if p % 10 == 0:
            print(f"    {p}/{total} ({len(all_items)}条)")
        time.sleep(5)

    print(f"    列表: {len(all_items)} 条")

    # 过滤医疗 + 城市标注
    medical = []
    seen_ids = set()
    for d in all_items:
        ok, eq = is_medical(d["title"])
        if not ok:
            continue
        iid = d.get("info_id", "")
        if iid and iid in seen_ids:
            continue
        if iid:
            seen_ids.add(iid)
        d["matched_eq"] = eq
        d["city"] = fix_city(d)
        medical.append(d)

    # 按城市过滤
    medical = filter_by_config(medical, config)
    print(f"    医疗(过滤后): {len(medical)} 条")

    # 详情
    for i, d in enumerate(medical):
        detail_url = d.get("detail_url", "")
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
    config = load_config()
    time_labels = {"0": "今日", "1": "近1周", "2": "近1月"}
    tr = str(config.get('time_range', 1))

    print("=" * 55)
    print(f"  河南医疗设备招投标采集 — Person {config['person']}")
    print(f"  时间范围: {time_labels.get(tr, tr)}")
    cities = config.get('my_cities', ['省级'])
    print(f"  负责范围: {', '.join(cities) if len(cities) <= 9 else f'{len(cities)}个城市'}")
    print("=" * 55)

    output_file = os.path.join(SCRIPT_DIR, config.get('output_file', 'output/result.json'))
    existing = load_existing(output_file)

    all_medical = []
    sources = config.get('sources', [])
    for src in sources:
        if not src.get('enabled', True):
            print(f"\n⏭ 跳过（未启用）: {src['name']}")
            continue
        items = crawl_source(src, config)
        all_medical.extend(items)

    # 合并去重
    merged = merge_items(existing, all_medical)
    for d in merged:
        d.setdefault('category', classify(d.get('announce_type', '')))

    # 保存
    result = save_output(output_file, merged)
    summary = result['summary']

    print(f"\n{'=' * 55}")
    print(f"✅ 完成! 共 {summary['total']} 条 (本次新增 {len(all_medical)} 条)")
    print(f"   分类: 招标{summary['categories'].get('招标',0)} "
          f"中标{summary['categories'].get('中标',0)} "
          f"终止{summary['categories'].get('终止',0)} "
          f"其他{summary['categories'].get('其他',0)}")
    print(f"   保存: {output_file}")

    if sys.stdin.isatty():
        input("\n按 Enter 退出...")


if __name__ == '__main__':
    main()
