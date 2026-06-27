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
        browse_count = random.randint(6, 12)  # 随机浏览6-12个帖子
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
        # 从URL中提取topic_id
        import re as _re
        m = _re.search(r'/t/[^/]+/(\d+)', page.url)
        topic_id = int(m.group(1)) if m else None
        prev_url = page.url
        total_time = 0
        post_num = 0

        for _ in range(random.randint(5, 10)):
            scroll_dist = random.randint(550, 650)
            page.run_js(f"window.scrollBy(0, {scroll_dist})")

            if random.random() < 0.03:
                logger.success("随机退出浏览")
                break

            at_bottom = page.run_js(
                "window.scrollY + window.innerHeight >= document.body.scrollHeight"
            )

            post_num += 1
            reading_time = random.randint(900, 1100)  # 每条帖子阅读~1秒
            total_time += reading_time

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
                logger.success("已到底部，退出浏览")
                break

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
        # Use browser (DrissionPage) which has login session
        # curl_cffi session can't access connect.linux.do (sub-domain cookie issue)
        try:
            connect_tab = self.browser.new_tab("https://connect.linux.do/")
            time.sleep(3)
            html = connect_tab.html
            connect_tab.close()

            soup = BeautifulSoup(html, "html.parser")
            rows = soup.select("table tr")
            info = []

            for row in rows:
                cells = row.select("td")
                if len(cells) >= 3:
                    project = cells[0].text.strip()
                    current = cells[1].text.strip() if cells[1].text.strip() else "0"
                    requirement = cells[2].text.strip() if cells[2].text.strip() else "0"
                    info.append([project, current, requirement])

            if not info:
                # Fallback: try curl_cffi with explicit cookie forwarding
                cookie_header = "; ".join(f"{c.name}={c.value}" for c in self.session.cookies)
                resp = self.session.get(
                    "https://connect.linux.do/",
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Cookie": cookie_header,
                    },
                    impersonate="firefox135",
                )
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table tr")
                for row in rows:
                    cells = row.select("td")
                    if len(cells) >= 3:
                        project = cells[0].text.strip()
                        current = cells[1].text.strip() if cells[1].text.strip() else "0"
                        requirement = cells[2].text.strip() if cells[2].text.strip() else "0"
                        info.append([project, current, requirement])

            logger.info("--------------Connect Info-----------------")
            logger.info("\n" + tabulate(info, headers=["项目", "当前", "要求"], tablefmt="pretty"))
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
