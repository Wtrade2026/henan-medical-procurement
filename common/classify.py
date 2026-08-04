"""公告分类：招标/中标/终止/其他"""

def classify(announce_type):
    at = announce_type or ""
    if at in ("采购公告", "采购意向"):
        return "招标"
    elif at in ("结果公告", "合同公告"):
        return "中标"
    elif at in ("废标公告", "变更公告"):
        return "终止"
    return "其他"
