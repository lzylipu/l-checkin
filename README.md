# 🐧 L站签到 / LinuxDo Daily Check-in

> 自动登录 L站(linux.do)，随机浏览帖子 + 点赞，实现每日签到与活跃度提升。  
> Auto login, browse topics, like posts on linux.do for daily check-in & activity.

---

## ✨ 功能 / Features

| 🇨🇳 中文 | 🇺🇸 English |
|---------|----------|
| 🔐 Cookie 自动登录 | 🔐 Auto login via Cookie |
| 📖 随机浏览帖子（滚动阅读 + 计时上报） | 📖 Browse topics with scroll reading & timing reports |
| ❤️ 自动点赞 | ❤️ Auto like posts |
| 🔄 滚动加载更多帖子（最多50个候选） | 🔄 Scroll to load more topics (up to 50 candidates) |
| 🌐 Connect 信息获取（trust level 等） | 🌐 Fetch connect info (trust levels, etc.) |
| 👴 老王论坛签到 | 👴 Laowang forum check-in |
| 📬 多渠道通知（TG / Gotify / SC³ / wxpush） | 📬 Multi-channel notifications |
| ⏰ GitHub Actions + 青龙面板支持 | ⏰ GitHub Actions & Qinglong panel support |

---

## 🔧 环境变量 / Environment Variables

| 变量 / Variable | 说明 / Description | 必填 / Required | 默认 / Default |
|---------|------|:---:|------|
| `LINUXDO_COOKIES` | L站浏览器 Cookie 字符串 | ✅ | — |
| `LAOWANG_COOKIE` | 老王论坛 Cookie | ❌ | — |
| `TOPIC_LIMIT` | 发现帖子上限（滚动加载） | ❌ | `50` |
| `BROWSE_COUNT` | 每次浏览帖子数量 | ❌ | `20` |
| `BROWSE_ENABLED` | 是否浏览帖子 | ❌ | `true` |
| `GOTIFY_URL` + `GOTIFY_TOKEN` | Gotify 通知 | ❌ | — |
| `SC3_PUSH_KEY` | Server酱³ 通知 | ❌ | — |
| `WXPUSH_URL` + `WXPUSH_TOKEN` | wxpush 通知 | ❌ | — |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram 通知 | ❌ | — |

> 🍪 Cookie 获取：浏览器登录 → F12 → Application → Cookies → 全选复制  
> 🍪 Cookie extraction: Browser → F12 → Application → Cookies → Copy all

---

## 🚀 使用方法 / Usage

### GitHub Actions

1. 🍴 Fork 本项目 / Fork this repo
2. ⚙️ Settings → Secrets → Actions → 添加 `LINUXDO_COOKIES` / Add `LINUXDO_COOKIES`
3. 🤖 Actions 每5小时自动运行 / Runs every 5 hours automatically

### 青龙面板 / Qinglong Panel

1. 📦 Python3 依赖 / Python3 deps:  
   `DrissionPage==4.1.0.18 wcwidth==0.2.13 tabulate==0.9.0 loguru==0.7.2 curl-cffi beautifulsoup4`
2. 🐧 Linux 依赖 / Linux deps: `chromium`
3. 🔑 环境变量 / Env vars: `LINUXDO_COOKIES`（必填），`LAOWANG_COOKIE`（可选）
4. ⏰ 定时规则 / Cron:

| 任务 / Task | Cron 表达式 | 说明 / Description |
|------------|-----------|------|
| 🐧 L站签到 | `5 */5 * * *` | 每5小时第5分 / Every 5h at :05 |
| 👴 老王签到 | `17 1,17 * * *` | 每天 1:17 和 17:17 / Daily 1:17 & 17:17 |

> 🐳 Docker 青龙须使用 `whyour/qinglong:debian` 镜像  
> 🐳 Docker Qinglong must use `whyour/qinglong:debian` image

---

## 📁 文件结构 / File Structure

```
main.py              # 🐧 L站签到主脚本 / Main check-in script
laowang_checkin.py   # 👴 老王论坛签到 / Laowang forum check-in
notify.py            # 📬 通知模块 / Notification module
requirements.txt     # 📦 Python 依赖 / Python dependencies
.github/workflows/   # ⚥ GitHub Actions CI/CD
```

---

## 🔄 自动更新 / Auto Update

- **GitHub Actions**: `sync.yml` 每天自动同步上游 / Auto sync upstream daily
- **青龙面板**: 按仓库定时规则拉取 / Pull by repo schedule
