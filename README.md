# L站 每日签到

## 项目描述

自动登录 L站 并随机浏览帖子，实现每日签到 + 活跃度。

## 功能

- 自动 Cookie 登录
- 自动浏览帖子（随机选择10个，模拟滚动阅读）
- 每天 GitHub Actions 自动运行
- 支持青龙面板运行
- 可选通知: Telegram / Gotify / Server酱³ / wxpush

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `LINUXDO_COOKIES` | 浏览器 Cookie 字符串（必填） | `_t=xxx; _forum_session=yyy` |
| `BROWSE_ENABLED` | 是否浏览帖子 | `true`（默认） |
| `GOTIFY_URL` + `GOTIFY_TOKEN` | Gotify 通知（可选） | |
| `SC3_PUSH_KEY` | Server酱³ 通知（可选） | `sctpxxxxt` |
| `WXPUSH_URL` + `WXPUSH_TOKEN` | wxpush 通知（可选） | |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram 通知（可选） | |

Cookie 获取: 浏览器登录站点 → F12 → Application → Cookies → 全选复制

## 使用方法

### GitHub Actions

1. Fork 本项目
2. Settings → Secrets → Actions → 添加 `LINUXDO_COOKIES`
3. Actions 每12小时自动运行

### 青龙面板

1. Python3 依赖: `DrissionPage==4.1.0.18 wcwidth==0.2.13 tabulate==0.9.0 loguru==0.7.2 curl-cffi bs4`
2. Linux 依赖: `chromium`
3. 环境变量: `LINUXDO_COOKIES`
4. 定时: `0 */6 * * *`

> Docker青龙须使用 `whyour/qinglong:debian` 镜像

## 文件结构

```
main.py          # 签到主脚本
notify.py        # 通知模块
requirements.txt # Python 依赖
.github/workflows/  # GitHub Actions
```

## 自动更新

GitHub Actions: sync.yml 每天自动同步上游。青龙面板: 按仓库定时规则拉取。
