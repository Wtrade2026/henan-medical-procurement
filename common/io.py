"""数据读写与合并"""
import os, json
from collections import Counter


def load_existing(filepath):
    if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
        with open(filepath) as f:
            return json.load(f).get("items", [])
    return []


def save_output(filepath, items):
    from .classify import classify
    cats = {"招标": 0, "中标": 0, "终止": 0, "其他": 0}
    for d in items:
        c = classify(d.get("announce_type", ""))
        d["category"] = c
        cats[c] += 1
    city_cnt = Counter(d.get("city", "未知") for d in items)
    output = {"summary": {"total": len(items), "categories": cats, "cities": len(city_cnt)}, "items": items}
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return output


def merge_items(existing, new):
    existing_ids = {d.get("info_id") for d in existing if d.get("info_id")}
    merged = list(new)
    for d in existing:
        iid = d.get("info_id")
        if iid and iid not in existing_ids:
            merged.append(d)
    return merged
