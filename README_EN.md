# 🐧 L-Checkin — L Site Auto Check-in

**🔐 Cookie Login · 📖 Topic Browsing · ❤️ Auto Like · 📬 Multi-channel Notify · ⏰ Fully Automated**

**English | [简体中文](./README.md)**

---

> 🐧 Automated daily check-in for the L Site (LINUX DO forum): random topic browsing with scroll-reading timing reports, auto liking, Connect info fetching, and multi-channel push notifications. Runs on GitHub Actions or a Qinglong panel — set it and forget it.

---

## ✨ Features

- 🔐 **Auto login via Cookie** — no password handling, just paste your browser Cookie
- 📖 **Topic browsing with real reading behavior** — scroll reading with timing reports to `/topics/timings`
- ❤️ **Auto like posts** — keeps your account active
- 🔄 **Scroll-to-load** — up to 50 candidate topics, browses 20 per run (configurable)
- 🌐 **Connect info fetching** — trust level and other account stats
- 📬 **Multi-channel notifications** — Telegram / Gotify / ServerChan³ / wxpush
- ⏰ **Two runtimes** — GitHub Actions (recommended) or Qinglong panel

## 🔧 Environment Variables

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

> 🍪 **Cookie extraction**: log in via browser → F12 → Application → Cookies → copy all.

## 🚀 Usage

### GitHub Actions (recommended)

1. 🍴 Fork this repo
2. ⚙️ Settings → Secrets and variables → Actions → add `LINUXDO_COOKIES`
3. 🤖 The workflow runs automatically every 5 hours

### Qinglong Panel

1. 📦 Python3 dependencies: `DrissionPage==4.1.0.18 wcwidth==0.2.13 tabulate==0.9.0 loguru==0.7.2 curl-cffi beautifulsoup4`
2. 🐧 System dependency: `chromium`
3. 🔑 Environment variable: `LINUXDO_COOKIES` (required)

> 🐳 Docker-based Qinglong must use the `whyour/qinglong:debian` image.

### ⏰ Schedule

| Task | Cron | Description |
|------|------|-------------|
| 🐧 L Site Check-in | `5 */5 * * *` | Every 5 hours at :05 |

## 📁 File Structure

```
main.py              # 🐧 Main check-in script
notify.py            # 📬 Notification module
requirements.txt     # 📦 Python dependencies
.github/workflows/   # ⚙️ GitHub Actions CI
```

## 🔄 Auto Update

- **GitHub Actions**: `sync.yml` syncs upstream daily
- **Qinglong Panel**: pull by your own schedule

## 📄 License

[MIT](./LICENSE) License
