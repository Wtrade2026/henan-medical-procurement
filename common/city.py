"""城市归属判定 - 5级fallback，从公告字段反推真实地市"""
import re

ALL_CITIES = ["郑州", "开封", "洛阳", "平顶山", "安阳", "鹤壁", "新乡", "焦作", "濮阳",
              "许昌", "漯河", "三门峡", "南阳", "商丘", "信阳", "周口", "驻马店", "济源"]

CITY_CODE_MAP = {
    "H60": "省级", "H61": "郑州", "H62": "开封", "H63": "开封",
    "H64": "洛阳", "H65": "平顶山", "H66": "安阳", "H67": "鹤壁",
    "H68": "新乡", "H69": "焦作", "H70": "濮阳", "H71": "许昌",
    "H72": "漯河", "H73": "三门峡", "H74": "南阳", "H75": "商丘",
    "H76": "信阳", "H77": "周口", "H78": "驻马店", "H79": "济源",
}

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
    """从 region + agency + channelCode + content_url 推断真实城市"""
    # 1. region 字段直接匹配（列表页"区域"标签，最可靠）
    region = item.get("region", "") or ""
    for cn in ALL_CITIES:
        if cn in region:
            return cn
    for county, city in COUNTY_NAME_CITY.items():
        if county in region:
            return city
    if region and "河南" in region and "市" not in region:
        return "省级"

    # 2. agency 发布机构匹配
    agency = item.get("agency", "") or ""
    for cn in ALL_CITIES:
        if cn in agency:
            return cn
    for county, city in COUNTY_NAME_CITY.items():
        if county in agency:
            return city

    # 3. channelCode 前缀
    cc = item.get("channel_code", "") or ""
    for prefix in ("H60", "H61", "H62", "H63", "H64", "H65", "H66", "H67",
                   "H68", "H69", "H70", "H71", "H72", "H73", "H74", "H75",
                   "H76", "H77", "H78", "H79"):
        if cc.startswith(prefix):
            return CITY_CODE_MAP[prefix]

    # 4. content_url 路径 slug 反推
    cu = item.get("content_url", "") or ""
    m = re.search(r'/cmsweb[^/]+/([a-z0-9]+)/', cu)
    if m:
        sub = m.group(1)
        for county, city in COUNTY_CITY.items():
            if county == sub:
                return city
        if sub in CITY_SLUGS:
            return CITY_SLUGS[sub]
        for sl, cn in sorted(CITY_SLUGS.items(), key=lambda x: -len(x[0])):
            if len(sl) >= 3 and sub.startswith(sl):
                return cn

    return "未知"
