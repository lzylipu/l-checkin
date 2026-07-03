# 🐧 L站签到

> 自动登录 L站，随机浏览帖子 + 点赞，实现每日签到与活跃度提升

[**English**](#user-content-english) | [**中文**](#user-content-chinese)

---

<a id="chinese"></a>
## 中文

### ✨ 功能

- 🔐 Cookie 自动登录
- 📖 随机浏览帖子（滚动阅读 + 计时上报 /topics/timings）
- ❤️ 自动点赞
- 🔄 滚动加载更多帖子（最多50个候选，浏览20个）
- 🌐 Connect 信息获取（trust level 等）
- 📬 多渠道通知（Telegram / Gotify / Server酱³ / wxpush）
- ⏰ GitHub Actions + 青龙面板支持

### 🔧 环境变量

| 变量 | 说明 | 必填 | 默认 |
|------|------|:----:|------|
| `LINUXDO_COOKIES` | L站浏览器 Cookie 字符串 | ✅ | — |
| `TOPIC_LIMIT` | 发现帖子上限（滚动加载） | ❌ | `50` |
| `BROWSE_COUNT` | 每次浏览帖子数量 | ❌ | `20` |
| `BROWSE_ENABLED` | 是否浏览帖子 | ❌ | `true` |
| `GOTIFY_URL` + `GOTIFY_TOKEN` | Gotify 通知 | ❌ | — |
| `SC3_PUSH_KEY` | Server酱³ 通知 | ❌ | — |
| `WXPUSH_URL` + `WXPUSH_TOKEN` | wxpush 通知 | ❌ | — |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram 通知 | ❌ | — |

> 🍪 Cookie 获取：浏览器登录 → F12 → Application → Cookies → 全选复制

### 🚀 使用方法

#### GitHub Actions

1. 🍴 Fork 本项目
2. ⚙️ Settings → Secrets → Actions → 添加 `LINUXDO_COOKIES`
3. 🤖 Actions 每5小时自动运行

#### 青龙面板

1. 📦 Python3 依赖：`DrissionPage==4.1.0.18 wcwidth==0.2.13 tabulate==0.9.0 loguru==0.7.2 curl-cffi beautifulsoup4`
2. 🐧 Linux 依赖：`chromium`
3. 🔑 环境变量：`LINUXDO_COOKIES`（必填）

#### ⏰ 定时规则

| 任务 | Cron 表达式 | 说明 |
|------|-----------|------|
| 🐧 L站签到 | `5 */5 * * *` | 每5小时第5分 |

> 🐳 Docker 青龙须使用 `whyour/qinglong:debian` 镜像

### 📁 文件结构

```
main.py              # 🐧 L站签到主脚本
notify.py            # 📬 通知模块
requirements.txt     # 📦 Python 依赖
.github/workflows/   # ⚙️ GitHub Actions CI/CD
```

### 🔄 自动更新

- **GitHub Actions**：`sync.yml` 每天自动同步上游
- **青龙面板**：按仓库定时规则拉取

---

<a id="english"></a>
## English

### ✨ Features

- 🔐 Auto login via Cookie
- 📖 Browse topics with scroll reading & timing reports (`/topics/timings`)
- ❤️ Auto like posts
- 🔄 Scroll to load more topics (up to 50 candidates, browse 20)
- 🌐 Fetch Connect info (trust levels, etc.)
- 📬 Multi-channel notifications (Telegram / Gotify / ServerChan³ / wxpush)
- ⏰ GitHub Actions & Qinglong panel support

### 🔧 Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|:--------:|---------|
| `LINUXDO_COOKIES` | L Site browser Cookie string | ✅ | — |
| `TOPIC_LIMIT` | Max topics to discover (scroll loading) | ❌ | `50` |
| `BROWSE_COUNT` | Number of topics to browse per run | ❌ | `20` |
| `BROWSE_ENABLED` | Enable topic browsing | ❌ | `true` |
| `GOTIFY_URL` + `GOTIFY_TOKEN` | Gotify notifications | ❌ | — |
| `SC3_PUSH_KEY` | ServerChan³ notifications | ❌ | — |
| `WXPUSH_URL` + `WXPUSH_TOKEN` | wxpush notifications | ❌ | — |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram notifications | ❌ | — |

> 🍪 Cookie extraction: Browser → F12 → Application → Cookies → Copy all

### 🚀 Usage

#### GitHub Actions

1. 🍴 Fork this repo
2. ⚙️ Settings → Secrets → Actions → Add `LINUXDO_COOKIES`
3. 🤖 Actions runs every 5 hours automatically

#### Qinglong Panel

1. 📦 Python3 deps: `DrissionPage==4.1.0.18 wcwidth==0.2.13 tabulate==0.9.0 loguru==0.7.2 curl-cffi beautifulsoup4`
2. 🐧 Linux deps: `chromium`
3. 🔑 Env vars: `LINUXDO_COOKIES` (required)

#### ⏰ Cron Schedule

| Task | Cron Expression | Description |
|------|----------------|-------------|
| 🐧 L Site Check-in | `5 */5 * * *` | Every 5 hours at :05 |

> 🐳 Docker Qinglong must use `whyour/qinglong:debian` image

### 📁 File Structure

```
main.py              # 🐧 L Site check-in main script
notify.py            # 📬 Notification module
requirements.txt     # 📦 Python dependencies
.github/workflows/   # ⚙️ GitHub Actions CI/CD
```

### 🔄 Auto Update

- **GitHub Actions**: `sync.yml` auto syncs upstream daily
- **Qinglong Panel**: Pull by repo schedule rules
