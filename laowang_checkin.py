"""
cron: 0 */12 * * *
new Env("老王签到")
"""

import os, re, sys, random, time
from DrissionPage import ChromiumOptions, Chromium

COOKIE = os.environ.get("LAOWANG_COOKIE", "").strip()
HEADLESS = True

BASE = "https://laowang.vip"
SIGN_URL = f"{BASE}/plugin.php?id=k_misign:sign"


def parse_cookies(s):
    return [{"name": k.strip(), "value": v.strip(), "domain": "laowang.vip", "path": "/"}
            for p in s.split(";") if "=" in p
            for k, _, v in [p.partition("=")]]


def solve_slider(page):
    """Canvas像素对比检测缺口"""
    for attempt in range(15):
        try:
            gap = page.run_js("""
                const c = document.createElement('canvas');
                c.width = 240; c.height = 450;
                const ctx = c.getContext('2d');
                ctx.drawImage(tncode._img, 0, 0);
                const d = ctx.getImageData(0, 0, 240, 450).data;
                let bestX = 0, bestScore = 0, scores = [];
                for (let col = 0; col < 190; col++) {
                    let score = 0;
                    for (let x = col; x < col + 50; x++) {
                        for (let y = 0; y < 150; y++) {
                            const i1 = (y*240+x)*4, i2 = ((y+300)*240+x)*4;
                            const dr=d[i1]-d[i2], dg=d[i1+1]-d[i2+1], db=d[i1+2]-d[i2+2];
                            score += dr*dr+dg*dg+db*db;
                        }
                    }
                    scores.push(score);
                    if (score > bestScore) { bestScore = score; bestX = col; }
                }
                if (bestX>0 && bestX<189) {
                    const y0=scores[bestX-1],y1=scores[bestX],y2=scores[bestX+1];
                    const den=2*(2*y1-y0-y2);
                    if(den!==0) bestX = Math.round(bestX + (y0-y2)/den);
                }
                return bestX;
            """)
        except:
            if attempt < 14:
                page.ele(".tncode").click()
                time.sleep(2)
                continue
            return None

        if not gap:
            return None

        # 拖动滑块
        block = page.ele(".slide_block")
        if not block:
            return None
        rect = block.rect
        sx, sy = rect.viewport_midpoint
        page.actions.move_to(block).hold(block)
        # 人类化轨迹
        steps = 30
        for i in range(1, steps + 1):
            p = i / steps
            ease = 1 - (1 - p) ** 3
            jx = sx + gap * ease
            jy = sy + (random.random() - 0.5) * 2
            page.actions.move(jx, jy)
            time.sleep(0.005 + random.random() * 0.015)
        page.actions.release(sx + gap + random.randint(1, 3), sy)
        time.sleep(3)

        # 检查结果
        try:
            ok = page.run_js("""
                const el = document.getElementById('cliccaptcha-submit-info');
                if(el && el.value && el.value.includes('_ok')) return el.value;
                const msg = document.querySelector('.tncode_msg_ok');
                if(msg && msg.textContent.includes('验证成功')) return 'ok';
                return null;
            """)
            if ok:
                return ok
        except:
            pass

        if attempt < 14:
            page.run_js("if(typeof tncode!=='undefined') tncode.refresh();")
            time.sleep(2)

    return None


def sign():
    co = (ChromiumOptions().headless(HEADLESS).incognito(True)
          .set_argument("--no-sandbox")
          .set_argument("--disable-gpu")
          .set_argument("--disable-dev-shm-usage"))
    browser = Chromium(co)
    tab = browser.new_tab()
    try:
        # 设Cookie
        tab.set.cookies(parse_cookies(COOKIE))
        tab.get(SIGN_URL)
        time.sleep(3)

        # 获取formhash
        formhash = None
        try:
            m = tab.run_js("""
                const el = document.querySelector('input[name=formhash]');
                if(el) return el.value;
                const m = document.documentElement.innerHTML.match(/formhash[:=]\\\\s*['"]?([a-f0-9]{8})/);
                return m ? m[1] : null;
            """)
            if m:
                formhash = m
        except:
            pass
        if not formhash:
            return "❌ 无法获取formhash"

        # 触发签到请求
        tab.get(f"{SIGN_URL}&operation=qiandao&formhash={formhash}&format=empty")
        time.sleep(3)

        # 处理滑块
        try:
            tab.ele(".tncode", timeout=5).click()
        except:
            # 可能已签到或不需要验证
            pass

        time.sleep(2)
        captcha = solve_slider(tab)
        if not captcha:
            return "❌ 滑块验证失败"

        # 点击提交
        try:
            tab.ele("#submit-btn", timeout=5).click()
            time.sleep(3)
        except:
            pass

        # 获取结果
        result = tab.run_js("""
            const t = document.body.innerText;
            const days = t.match(/连续签到\\\\s*(\\\\d+)\\\\s*天/);
            const lv = t.match(/(\\\\[LV\\\\.\\\\d+\\\\][^\\\\n]*)/);
            return (days?days[1]:'') + '天 ' + (lv?lv[1]:'');
        """)
        return f"✅ 签到成功 {result}" if result.strip() else "✅ 签到提交完成"

    except Exception as e:
        return f"❌ {e}"
    finally:
        try: tab.close()
        except: pass
        try: browser.quit()
        except: pass


if __name__ == "__main__":
    if not COOKIE:
        print("❌ 请设置 LAOWANG_COOKIE 环境变量")
        sys.exit(1)

    print("🚀 老王签到...")
    result = sign()
    print(result)

    # 通知
    try:
        from notify import sendNotify
        sendNotify("老王签到", result)
    except:
        pass
