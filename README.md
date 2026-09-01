![Banner](cleanerBanner.png)
# 🧹 Discord Cleaner

> Bulk delete messages from any user in any channel — with style, speed, and sanity.

---

## ⚠️ Legal & Discord ToS

**Use at your own risk.**  
This tool interacts with Discord's API using your personal token.  
Automated deletion may violate Discord's Terms of Service if misused.  
**We are not responsible for any account suspension or data loss.**  
Always respect server rules and use responsibly.

---

## 🐍 Python vs 🖥️ JavaScript – Which one should you use?

| Feature | Python (CLI) | JavaScript (Console) |
|---------|--------------|----------------------|
| **Setup** | Requires Python + `aiohttp` | Zero setup – copy/paste into F12 console |
| **Speed** | Faster (async) | Slightly slower (browser limits) |
| **Rate‑limit handling** | ✅ Advanced (auto‑adjust) | ✅ Basic (manual cooldown) |
| **Dry‑run (preview)** | ✅ Yes | ❌ No |
| **Security** | Token stored in memory only | Token visible in console (be careful!) |
| **Batch size control** | ✅ Configurable | Fixed (3 per batch) |
| **Reporting** | Detailed stats + JSON export (planned) | Console logs only |
| **Recommended for** | **Heavy cleaning (1000+ messages)** | Quick fixes, small channels |

> 🔥 **Our recommendation:** Use the **Python version** for serious cleanup – it's safer, faster, and gives you full control.  
> The JS version is great for a quick one‑off job when you're already in the browser.

---

## ✨ Features (both versions)

- 🗑️ Delete all messages from a **specific user** in a **specific channel**
- 🛡️ Smart **rate‑limit handling** – automatically slows down when Discord says so
- 📦 **Batch processing** – delete messages in chunks to avoid timeouts
- 📊 **Real‑time stats** – see deleted, failed, skipped, speed, and elapsed time
- ⏸️ **Graceful stop** – press `Ctrl+C` (Python) or type `stopDeleting()` (JS)
- 🔍 **Optional filters** – content text, links only, files only
- 🧪 **Dry‑run mode** (Python only) – see what would be deleted without actually doing it

---

## 🐍 Python Version (Recommended)

### Installation

```bash
pip install aiohttp
```

### Usage

```bash
python cleaner.py --token "YOUR_TOKEN" \
                   --author-id "USER_ID" \
                   --channel-id "CHANNEL_ID" \
                   --content "spam" \
                   --dry-run
```

#### Interactive mode (easiest)

```bash
python cleaner.py --interactive
```

### All arguments

| Argument | Description |
|----------|-------------|
| `--token` | Your Discord token (keep it secret!) |
| `--author-id` | User ID to delete messages from |
| `--channel-id` | Channel ID to clean |
| `--content` | Only delete messages containing this text |
| `--has-link` | Only delete messages with links |
| `--has-file` | Only delete messages with attachments |
| `--batch-size` | Messages per batch (default: 3) |
| `--delete-delay` | Delay between deletions in ms (default: 1000) |
| `--search-delay` | Delay between API requests (default: 2000) |
| `--dry-run` | Preview without actually deleting |
| `--verbose` | Show debug logs |

---

## 🖥️ JavaScript Version (Console)

Perfect for a **quick cleanup** without installing anything.

### How to use

1. Open Discord in your browser (web version)
2. Press **F12** (or `Ctrl+Shift+I`) to open Developer Tools
3. Go to the **Console** tab
4. Copy the entire JavaScript code from [`discord-cleaner.js`](./discord-cleaner.js)
5. Paste it into the console and press **Enter**
6. Follow the interactive prompts (token, user ID, channel ID)

### Stop the script

Type this in the console at any time:

```javascript
stopDeleting()
```

### Important notes

- Your token is **visible** in the console – clear your history afterwards!
- The script runs in your browser, so it's limited by your browser's performance.
- For **large channels**, the Python version is **much more reliable**.

### Advanced: Tampermonkey / Greasemonkey

You can also wrap the script in a userscript header to run it automatically on Discord pages:

```javascript
// ==UserScript==
// @name         Discord Cleaner
// @namespace    http://tampermonkey.net/
// @version      iLove2319
// @match        https://discord.com/*
// @grant        none
// ==/UserScript==
// Paste the whole script here
```



