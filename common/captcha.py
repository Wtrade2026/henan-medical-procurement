"""验证码识别与会话管理"""
import re, time
import ddddocr
from . import parser


def new_session(headers):
    import requests
    s = requests.Session()
    s.headers.update(headers)
    return s


def solve_captcha(session, base_url, path, time_type, headers):
    """打开 ggcx 搜索页，解验证码提交搜索，返回 (soCode, 第一页items, 总页数)"""
    import requests
    ocr = ddddocr.DdddOcr(show_ad=False)
    ggcx_url = f"{base_url}/{path}/ggcx"

    for _ in range(15):
        session.cookies.clear()
        try:
            r = session.get(ggcx_url, timeout=(10, 20))
            r.encoding = "utf-8"
        except Exception:
            time.sleep(3)
            continue

        tm = re.search(r'getImage/([a-f0-9]+)', r.text)
        sm = re.search(r'soCode=([a-f0-9]+)', r.text)
        if not tm or not sm:
            continue

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

        if "访问频繁" in r2.text:
            print("  [限流] 等待30秒...")
            time.sleep(30)
            continue

        if "errCode=1" not in r2.url:
            items = parser.parse_list(r2.text)
            if "共搜到0条" in r2.text or "搜到0条" in r2.text:
                return sm.group(1), [], 0
            p = re.search(r'共\s*(\d+)\s*页', r2.text)
            total = int(p.group(1)) if p else 1
            return sm.group(1), items, total

        time.sleep(2)

    raise Exception("验证码失败")
