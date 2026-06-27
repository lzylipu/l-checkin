"""
cron: 5 */6 * * *
new Env("L站 签到")
"""

import os
import re
import random
import time
import functools
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
                    if attempt == retries - 1:  # 最后一次尝试
                        logger.error(f"函数 {func.__name__} 最终执行失败: {str(e)}")
                    logger.warning(
                        f"函数 {func.__name__} 第 {attempt + 1}/{retries} 次尝试失败: {str(e)}"
                    )
                    if attempt < retries - 1:
                        sleep_s = random.uniform(min_delay, max_delay)
                        logger.info(
                            f"将在 {sleep_s:.2f}s 后重试 ({min_delay}-{max_delay}s 随机延迟)"
                        )
                        time.sleep(sleep_s)
            return None

        return wrapper

    return decorator


os.environ.pop("DISPLAY", None)
os.environ.pop("DYLD_LIBRARY_PATH", None)

COOKIES = os.environ.get("LINUXDO_COOKIES", "").strip()  # 手动设置的 Cookie 字符串，优先使用
BROWSE_ENABLED = os.environ.get("BROWSE_ENABLED", "true").strip().lower() not in [
    "false",
    "0",
    "off",
]
TOPIC_LIMIT = int(os.environ.get("TOPIC_LIMIT", "50"))  # 发现帖子数上限
BROWSE_COUNT = int(os.environ.get("BROWSE_COUNT", "20"))  # 浏览帖子数量

HOME_URL = "https://linux.do/"


class LinuxDoBrowser:
    def __init__(self) -> None:
        from sys import platform

        if platform == "linux" or platform == "linux2":
            platformIdentifier = "X11; Linux x86_64"
        elif platform == "darwin":
            platformIdentifier = "Macintosh; Intel Mac OS X 10_15_7"
        elif platform == "win32":
            platformIdentifier = "Windows NT 10.0; Win64; x64"
        else:
            platformIdentifier = "X11; Linux x86_64"

        co = (
            ChromiumOptions()
            .headless(True)
            .incognito(True)
            .set_argument("--no-sandbox")
        )
        co.set_user_agent(
            f"Mozilla/5.0 ({platformIdentifier}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        self.browser = Chromium(co)
        self.page = self.browser.new_tab()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        # 初始化通知管理器
        self.notifier = NotificationManager()

    @staticmethod
    def parse_cookie_string(cookie_str: str) -> list[dict]:
        """
        解析浏览器复制的 Cookie 字符串格式: "name1=value1; name2=value2"
        返回 DrissionPage 所需的 cookie 列表格式。
        """
        cookies = []
        for part in cookie_str.strip().split(";"):
            part = part.strip()
            if "=" in part:
                name, _, value = part.partition("=")
                cookies.append(
                    {
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".linux.do",
                        "path": "/",
                    }
                )
        return cookies

    def login_with_cookies(self, cookie_str: str) -> bool:
        """使用手动设置的 Cookie 直接登录，跳过账号密码流程"""
        logger.info("检测到手动 Cookie，尝试 Cookie 登录...")
        dp_cookies = self.parse_cookie_string(cookie_str)
        if not dp_cookies:
            logger.error("Cookie 解析失败或为空，无法使用 Cookie 登录")
            return False

        logger.info(f"成功解析 {len(dp_cookies)} 个 Cookie 条目")

        # 同步到 requests.Session，以便后续 API 请求（如 print_connect_info）使用
        for ck in dp_cookies:
            self.session.cookies.set(ck["name"], ck["value"], domain=".linux.do")

        # 同步到 DrissionPage
        self.page.set.cookies(dp_cookies)
        logger.info("Cookie 设置完成，导航至 linux.do...")
        self.page.get(HOME_URL)
        time.sleep(5)

        # 验证登录状态
        try:
            user_ele = self.page.ele("@id=current-user")
        except Exception as e:
            logger.warning(f"Cookie 登录验证异常: {str(e)}")
            return True
        if not user_ele:
            if "avatar" in self.page.html:
                logger.info("Cookie 登录验证成功 (通过 avatar)")
                return True
            logger.error("Cookie 登录验证失败 (未找到 current-user)，Cookie 可能已过期")
            return False
        else:
            logger.info("Cookie 登录验证成功")
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

        # 滚动加载更多帖子直到达到TOPIC_LIMIT
        scroll_attempts = 0
        while len(topic_list) < TOPIC_LIMIT and scroll_attempts < 5:
            self.page.scroll.to_bottom()
            time.sleep(2)
            for sel in ["@id=list-area", ".topic-list", "table.topic-list"]:
                try:
                    area = self.page.ele(sel, timeout=3)
                    if area:
                        new_list = area.eles(".:title")
                        if len(new_list) > len(topic_list):
                            topic_list = new_list
                            break
                except Exception:
                    continue
            scroll_attempts += 1

        browse_count = min(BROWSE_COUNT, len(topic_list))
        logger.info(f"发现 {len(topic_list)} 个主题帖，随机选择{browse_count}个")
        for topic in random.sample(topic_list, browse_count):
            self.click_one_topic(topic.attr("href"))
        return True

    @retry_decorator()
    def click_one_topic(self, topic_url):
        new_page = self.browser.new_tab()
        try:
            # 使用 track_visit=true 标记已读(和真实浏览器一致)
            if '?' in topic_url:
                nav_url = topic_url + '&track_visit=true&forceLoad=true'
            else:
                nav_url = topic_url + '?track_visit=true&forceLoad=true'
            new_page.get(nav_url)
            if random.random() < 0.3:  # 0.3 * 30 = 9
                self.click_like(new_page)
            self.browse_post(new_page)
        finally:
            try:
                new_page.close()
            except Exception:
                pass

    def browse_post(self, page):
        # 从URL中提取topic_id和标题
        import re as _re
        m = _re.search(r'/t/[^/]+/(\d+)', page.url)
        topic_id = int(m.group(1)) if m else None
        # 提取帖子标题
        try:
            title = page.ele("tag:h1", timeout=2).text.strip()
            if len(title) > 30:
                title = title[:30] + "..."
        except Exception:
            title = f"帖子#{topic_id}" if topic_id else "未知帖子"

        prev_url = page.url
        total_time = 0
        post_num = 0
        max_scrolls = random.randint(5, 10)

        logger.info(f"📖 开始浏览: {title}")

        for i in range(max_scrolls):
            scroll_dist = random.randint(550, 650)
            page.run_js(f"window.scrollBy(0, {scroll_dist})")

            at_bottom = page.run_js(
                "window.scrollY + window.innerHeight >= document.body.scrollHeight"
            )

            post_num += 1
            reading_time = random.randint(900, 1100)  # 每条帖子阅读~1秒
            total_time += reading_time
            logger.info(f"  📜 滚动 {i+1}/{max_scrolls} | 楼层{post_num} | 阅读{(reading_time/1000):.1f}s")

            # 发送阅读时长到 topics/timings (和真实浏览器行为一致)
            if topic_id:
                try:
                    self.session.post(
                        f"https://linux.do/topics/timings",
                        data=f"timings%5B{post_num}%5D={reading_time}&topic_time={total_time}&topic_id={topic_id}",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        impersonate="firefox135",
                        timeout=5,
                    )
                except Exception:
                    pass

            time.sleep(random.uniform(2, 4))

            cur_url = page.url
            if cur_url != prev_url:
                prev_url = cur_url
            elif at_bottom:
                logger.info(f"  ✅ 已到底部，浏览了{post_num}个楼层")
                break
        else:
            logger.info(f"  ✅ 浏览完成，共{post_num}个楼层，总时长{(total_time/1000):.0f}s")

    def run(self):
        try:
            # Cookie 登录
            if COOKIES:
                login_res = self.login_with_cookies(COOKIES)
                if not login_res:
                    logger.error("Cookie 登录失败")
                    return
            else:
                logger.error("未设置 LINUXDO_COOKIES 环境变量")
                return

            if BROWSE_ENABLED:
                click_topic_res = self.click_topic()  # 点击主题
                if not click_topic_res:
                    logger.error("点击主题失败，程序终止")
                    return
                logger.info("完成浏览任务")
            self.print_connect_info()  # 打印连接信息
            self.send_notifications(BROWSE_ENABLED)  # 发送通知
        finally:
            try:
                self.page.close()
            except Exception:
                pass
            try:
                self.browser.quit()
            except Exception:
                pass

    def click_like(self, page):
        try:
            # 专门查找未点赞的按钮
            like_button = page.ele(".discourse-reactions-reaction-button")
            if like_button:
                logger.info("找到未点赞的帖子，准备点赞")
                like_button.click()
                logger.info("点赞成功")
                time.sleep(random.uniform(1, 2))
            else:
                logger.info("帖子可能已经点过赞了")
        except Exception as e:
            logger.error(f"点赞失败: {str(e)}")

    def print_connect_info(self):
        logger.info("获取连接信息")
        try:
            info = []

            # 方案1: 在当前已登录页面用JS fetch connect子域(浏览器自动带cookie)
            try:
                html = self.page.run_js("""
                    return fetch('https://connect.linux.do/')
                        .then(r => r.ok ? r.text() : '')
                        .catch(() => '');
                """)
            except Exception:
                html = ""

            if html and "login" not in html[:500].lower():
                # 解析HTML表格
                soup = BeautifulSoup(html, "html.parser")
                rows = soup.select("table tr")
                for row in rows:
                    cells = row.select("td")
                    if len(cells) >= 3:
                        project = cells[0].text.strip()
                        current = cells[1].text.strip() or "0"
                        requirement = cells[2].text.strip() or "0"
                        info.append([project, current, requirement])

                # 如果没有table，尝试preloaded JSON
                if not info:
                    try:
                        import html as html_mod
                        preloaded_match = re.search(r'data-preloaded="([^"]*)"', html)
                        if preloaded_match:
                            decoded = html_mod.unescape(html_mod.unescape(preloaded_match.group(1)))
                            preloaded = json.loads(decoded)
                            for key in preloaded:
                                if "connect" in key.lower() or "requirement" in key.lower():
                                    data = preloaded[key]
                                    if isinstance(data, str):
                                        data = json.loads(data)
                                    if isinstance(data, list):
                                        for item in data:
                                            if isinstance(item, dict):
                                                name = item.get("name", item.get("title", ""))
                                                cur = item.get("current", item.get("value", "0"))
                                                req = item.get("requirement", item.get("required", "0"))
                                                if name:
                                                    info.append([name, str(cur), str(req)])
                    except Exception as e:
                        logger.debug(f"解析preloaded失败: {e}")

            # 方案2: 打开connect标签页等JS渲染
            if not info:
                logger.info("JS fetch未获取到connect表格，尝试新标签页渲染...")
                try:
                    connect_tab = self.browser.new_tab("https://connect.linux.do/")
                    time.sleep(8)
                    connect_tab.wait.ele("table", timeout=10)
                    html2 = connect_tab.html
                    connect_tab.close()
                    soup = BeautifulSoup(html2, "html.parser")
                    rows = soup.select("table tr")
                    for row in rows:
                        cells = row.select("td")
                        if len(cells) >= 3:
                            project = cells[0].text.strip()
                            current = cells[1].text.strip() or "0"
                            requirement = cells[2].text.strip() or "0"
                            info.append([project, current, requirement])
                except Exception:
                    pass

            logger.info("--------------Connect Info-----------------")
            if info:
                logger.info("\n" + tabulate(info, headers=["项目", "当前", "要求"], tablefmt="pretty"))
            else:
                logger.warning("Connect信息为空，connect.linux.do可能需要JS渲染或cookie未生效")
        except Exception as e:
            logger.error(f"获取连接信息失败: {str(e)}")

    def send_notifications(self, browse_enabled):
        """发送签到通知"""
        status_msg = "✅每日登录成功"
        if browse_enabled:
            status_msg += " + 浏览任务完成"
        
        # 使用通知管理器发送所有通知
        self.notifier.send_all("LINUX DO", status_msg)


if __name__ == "__main__":
    if not COOKIES:
        print("请设置 LINUXDO_COOKIES 环境变量")
        exit(1)
    browser = LinuxDoBrowser()
    browser.run()
