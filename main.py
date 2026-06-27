"""
cron: 0 */6 * * *
new Env("L站 签到")
"""

import os, re, random, time, functools
from urllib.parse import urlparse
from loguru import logger
from DrissionPage import ChromiumOptions, Chromium
from tabulate import tabulate
from curl_cffi import requests
from bs4 import BeautifulSoup
from notify import NotificationManager


def retry_decorator(retries=3, min_delay=5, max_delay=10):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:
                        logger.error(f"函数 {func.__name__} 最终执行失败: {str(e)}")
                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1}/{retries} 次尝试失败: {str(e)}")
                    if attempt < retries - 1:
                        sleep_s = random.uniform(min_delay, max_delay)
                        logger.info(f"将在 {sleep_s:.2f}s 后重试 ({min_delay}-{max_delay}s 随机延迟)")
                        time.sleep(sleep_s)
            return None
        return wrapper
    return decorator


os.environ.pop("DISPLAY", None)
os.environ.pop("DYLD_LIBRARY_PATH", None)

USERNAME = os.environ.get("L_SITE_USERNAME")
PASSWORD = os.environ.get("L_SITE_PASSWORD")
COOKIES = os.environ.get("L_SITE_COOKIES", "").strip()
BROWSE_ENABLED = os.environ.get("BROWSE_ENABLED", "true").strip().lower() not in ["false", "0", "off"]
if not USERNAME:
    USERNAME = os.environ.get("USERNAME")
if not PASSWORD:
    PASSWORD = os.environ.get("PASSWORD")

HOME_URL = os.environ.get("L_SITE_BASE", "")
CONNECT_URL = os.environ.get("L_SITE_CONNECT", "")
_SITE_HOSTNAME = urlparse(HOME_URL).hostname or os.environ.get("L_SITE_DOMAIN", "")
_SITE_COOKIE_DOMAIN = "." + _SITE_HOSTNAME if _SITE_HOSTNAME else ""

LOGIN_URL = HOME_URL + "login"
SESSION_URL = HOME_URL + "session"


class LSiteBrowser:
    def __init__(self) -> None:
        from sys import platform
        if platform == "linux" or platform == "linux2":
            pf = "X11; Linux x86_64"
        elif platform == "darwin":
            pf = "Macintosh; Intel Mac OS X 10_15_7"
        elif platform == "win32":
            pf = "Windows NT 10.0; Win64; x64"
        else:
            pf = "X11; Linux x86_64"
        co = (ChromiumOptions().headless(True).incognito(True)
              .set_argument("--no-sandbox"))
        co.set_user_agent(f"Mozilla/5.0 ({pf}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
        self.browser = Chromium(co)
        self.page = self.browser.new_tab()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self.notifier = NotificationManager()

    @staticmethod
    def parse_cookie_string(cs: str) -> list[dict]:
        cookies = []
        for part in cs.strip().split(";"):
            part = part.strip()
            if "=" in part:
                name, _, value = part.partition("=")
                ck = {"name": name.strip(), "value": value.strip(), "path": "/"}
                if _SITE_COOKIE_DOMAIN:
                    ck["domain"] = _SITE_COOKIE_DOMAIN
                cookies.append(ck)
        return cookies

    def login_with_cookies(self, cookie_str: str) -> bool:
        logger.info("Cookie 登录...")
        dp_cookies = self.parse_cookie_string(cookie_str)
        if not dp_cookies:
            logger.error("Cookie 解析失败")
            return False
        logger.info(f"解析 {len(dp_cookies)} 个 Cookie")
        for ck in dp_cookies:
            self.session.cookies.set(ck["name"], ck["value"], domain=_SITE_HOSTNAME)
        self.page.set.cookies(dp_cookies)
        logger.info(f"导航至 {_SITE_HOSTNAME}...")
        self.page.get(HOME_URL)
        time.sleep(5)
        try:
            user_ele = self.page.ele("@id=current-user")
        except Exception:
            user_ele = None
        if not user_ele:
            if "avatar" in self.page.html:
                logger.info("Cookie 验证成功")
                return True
            logger.error("Cookie 验证失败")
            return False
        logger.info("Cookie 验证成功")
        return True

    def login(self):
        logger.info("账号密码登录")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": LOGIN_URL,
        }
        import html as _html
        resp_home = self.session.get(HOME_URL, headers={"Accept": "text/html"}, impersonate="firefox135")
        m = re.search(r'data-preloaded="([^"]*)"', resp_home.text)
        csrf_token = None
        if m:
            pre = _html.unescape(m.group(1).replace('&quot;', '"'))
            cm = re.search(r'"csrf":"([^"]+)"', pre)
            if cm:
                csrf_token = cm.group(1)
        if not csrf_token:
            logger.error("获取 CSRF 失败")
            return False
        logger.info(f"CSRF: {csrf_token[:10]}...")

        headers.update({
            "X-CSRF-Token": csrf_token,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": HOME_URL.rstrip("/"),
        })
        try:
            resp = self.session.post(SESSION_URL, data={
                "login": USERNAME, "password": PASSWORD,
                "second_factor_method": "1", "timezone": "Asia/Shanghai",
            }, impersonate="firefox135", headers=headers)
            if resp.status_code == 200:
                rj = resp.json()
                if rj.get("error"):
                    logger.error(f"登录失败: {rj['error']}")
                    return False
                logger.info("登录成功!")
            else:
                logger.error(f"登录失败: {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False

        cookies_dict = self.session.cookies.get_dict()
        dp_cookies = []
        for n, v in cookies_dict.items():
            ck = {"name": n, "value": v, "path": "/"}
            if _SITE_COOKIE_DOMAIN:
                ck["domain"] = _SITE_COOKIE_DOMAIN
            dp_cookies.append(ck)
        self.page.set.cookies(dp_cookies)
        self.page.get(HOME_URL)
        time.sleep(5)
        try:
            user_ele = self.page.ele("@id=current-user")
        except Exception:
            user_ele = None
        if not user_ele:
            if "avatar" in self.page.html:
                return True
            return False
        return True

    def click_topic(self):
        topic_list = None
        for sel in ["@id=list-area", ".topic-list", "table.topic-list"]:
            try:
                area = self.page.ele(sel, timeout=5)
                if area:
                    topic_list = area.eles(".:title")
                    if topic_list:
                        break
            except Exception:
                continue
        if not topic_list:
            logger.error("未找到主题帖")
            return False
        logger.info(f"发现 {len(topic_list)} 个主题帖，随机选择10个")
        for topic in random.sample(topic_list, 10):
            self.click_one_topic(topic.attr("href"))
        return True

    @retry_decorator()
    def click_one_topic(self, topic_url):
        new_page = self.browser.new_tab()
        try:
            new_page.get(topic_url)
            if random.random() < 0.3:
                self.click_like(new_page)
            self.browse_post(new_page)
        finally:
            try:
                new_page.close()
            except Exception:
                pass

    def browse_post(self, page):
        prev_url = None
        for _ in range(10):
            d = random.randint(550, 650)
            logger.info(f"滚动 {d}px...")
            page.run_js(f"window.scrollBy(0, {d})")
            if random.random() < 0.03:
                logger.success("随机退出")
                break
            at_bottom = page.run_js("window.scrollY + window.innerHeight >= document.body.scrollHeight")
            cur = page.url
            if cur != prev_url:
                prev_url = cur
            elif at_bottom:
                logger.success("已到底部")
                break
            time.sleep(random.uniform(2, 4))

    def run(self):
        try:
            if COOKIES:
                ok = self.login_with_cookies(COOKIES)
                if not ok:
                    logger.warning("Cookie失败, 尝试密码...")
                    ok = self.login()
            else:
                ok = self.login()
            if not ok:
                logger.warning("登录验证失败")
            if BROWSE_ENABLED:
                if not self.click_topic():
                    logger.error("浏览失败")
                    return
                logger.info("浏览完成")
            self.print_connect_info()
            self.send_notifications(BROWSE_ENABLED)
        finally:
            try: self.page.close()
            except: pass
            try: self.browser.quit()
            except: pass

    def click_like(self, page):
        try:
            btn = page.ele(".discourse-reactions-reaction-button")
            if btn:
                btn.click()
                logger.info("点赞成功")
                time.sleep(random.uniform(1, 2))
        except Exception as e:
            logger.error(f"点赞失败: {e}")

    def print_connect_info(self):
        if not CONNECT_URL:
            logger.info("未配置 L_SITE_CONNECT, 跳过")
            return
        logger.info("获取 Connect 信息...")
        headers = {"Accept": "text/html,application/xhtml+xml"}
        try:
            resp = self.session.get(CONNECT_URL, headers=headers, impersonate="firefox135")
            soup = BeautifulSoup(resp.text, "html.parser")
            info = []
            for row in soup.select("table tr"):
                cells = row.select("td")
                if len(cells) >= 3:
                    info.append([c.text.strip() for c in cells[:3]])
            if info:
                logger.info("\n" + tabulate(info, headers=["项目", "当前", "要求"], tablefmt="pretty"))
        except Exception as e:
            logger.warning(f"Connect 获取失败: {e}")

    def send_notifications(self, browse_enabled):
        u = USERNAME or COOKIES[:20]
        msg = f"✅每日登录成功: {u}"
        if browse_enabled:
            msg += " + 浏览完成"
        self.notifier.send_all("L站签到", msg)


if __name__ == "__main__":
    if not COOKIES and (not USERNAME or not PASSWORD):
        print("请设置 L_SITE_COOKIES(Cookie) 或 L_SITE_USERNAME+L_SITE_PASSWORD(密码)")
        exit(1)
    LSiteBrowser().run()
