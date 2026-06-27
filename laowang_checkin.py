"""
cron: 0 */12 * * *
new Env("老王签到")
老王论坛签到 - 纯HTTP版（基于HAR分析）
依赖: curl-cffi
环境变量: LAOWANG_COOKIE
"""

import os, re, sys
from curl_cffi import requests

COOKIE = os.environ.get("LAOWANG_COOKIE", "").strip()
BASE = "https://laowang.vip"
SIGN_PAGE = f"{BASE}/plugin.php?id=k_misign:sign"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"


def sign():
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    for p in COOKIE.split(";"):
        p = p.strip()
        if "=" in p:
            k, _, v = p.partition("=")
            s.cookies.set(k.strip(), v.strip(), domain="laowang.vip")

    # Step 1: visit sign page
    print("[1/3] opening sign page...")
    r = s.get(SIGN_PAGE, impersonate="chrome131", timeout=15,
              headers={"Referer": f"{BASE}/"})
    if r.status_code != 200:
        return f"FAIL sign page http {r.status_code}"
    html = r.text
    print(f"  HTTP 200, {len(html)} bytes")

    # Step 2: extract formhash (Discuz! standard, from HAR: formhash=78fdc48b)
    formhash = ""
    patterns = [
        r'input\s[^>]*name=["\']formhash["\'][^>]*value=["\']([a-f0-9]{8})["\']',
        r'name=["\']formhash["\'][^>]*value=["\']([a-f0-9]{8})["\']',
        r'value=["\']([a-f0-9]{8})["\'][^>]*name=["\']formhash["\']',
        r'formhash["\']?\s*[=:]\s*["\']?([a-f0-9]{8})',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            formhash = m.group(1)
            break
    if not formhash:
        # debug: show snippets
        for kw in ['formhash', 'mi_sign', 'qiandao']:
            ctx = re.findall(r'.{0,100}' + kw + r'.{0,100}', html, re.IGNORECASE)
            if ctx:
                print(f"  DEBUG [{kw}]: {ctx[0][:200]}")
                break
        else:
            print(f"  DEBUG HTML: {html[:800]}")
        return "FAIL no formhash (cookie expired?)"
    print(f"  formhash={formhash}")

    # Step 3: sign in (HAR flow: GET → POST)
    sign_url = f"{SIGN_PAGE}&operation=qiandao&formhash={formhash}&format=empty"
    headers_ajax = {"X-Requested-With": "XMLHttpRequest", "Referer": SIGN_PAGE}

    print("[2/3] GET sign...")
    s.get(sign_url, impersonate="chrome131", timeout=15, headers=headers_ajax)

    print("[3/3] POST sign...")
    r = s.post(sign_url, impersonate="chrome131", timeout=15, headers=headers_ajax)

    if r.status_code not in (200, 302):
        return f"FAIL sign http {r.status_code}"

    # check result
    r = s.get(SIGN_PAGE, impersonate="chrome131", timeout=15,
              headers={"Referer": SIGN_PAGE})
    html = r.text
    lx = re.search(r'lxdays[^>]*value[^>]*["\'](\d+)["\']', html, re.IGNORECASE)
    days = lx.group(1) if lx else "?"
    return f"OK 签到完成 (连续{days}天)"


if __name__ == "__main__":
    if not COOKIE:
        print("FAIL no LAOWANG_COOKIE")
        sys.exit(1)
    result = sign()
    print(result)
    try:
        from notify import sendNotify
        sendNotify("老王签到", result)
    except Exception:
        pass
