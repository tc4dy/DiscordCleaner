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

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🗑️ **Bulk Delete** | Delete all messages from any user in any channel |
| 🛡️ **Smart Rate-Limiting** | Auto-adjusts speed when Discord rate-limits you |
| 📦 **Batch Processing** | Deletes 3 messages at a time to avoid timeouts |
| 📊 **Live Stats** | Real-time counter for deleted, failed, skipped, speed & time |
| ⏹️ **Stop Anytime** | Type `stopDeleting()` in console or CTRL+R to stop safely |
| 🎯 **Target Specific User** | Only deletes messages from the user ID you specify |
| ⚡ **Zero Setup** | No installation needed — copy, paste, run |
| 🔄 **Auto-Retry** | Automatically retries failed requests |
| 📱 **Works Anywhere** | Browser console — works on Chrome, Firefox, Edge |
| ⏱️ **Speed Stats** | See messages per second and total time elapsed |

---

## 🎯 Quick Comparison

| Feature | JavaScript Version |
|---------|-------------------|
| Setup | ⚡ Zero — just copy & paste |
| Speed | 🐢 Respects Discord limits |
| Filters | ✅ Text, links, files |
| Stop | ✅ `stopDeleting()` |
| Stats | ✅ Live console output |
| Platform | 🌐 Any browser & Discord Console |

---

## ❓ FAQ

### Where do I find my Discord token?
1. Press **F12** to open Developer Tools
2. Go to **Network** tab
3. Send a message or reload the page
4. Click any request starting with `science` or `messages`
5. Scroll to **Request Headers** → copy the `authorization` value

> ⚠️ **Never share your token with anyone!**

---

### Where do I get User ID and Channel ID?
1. Enable **Developer Mode** in Discord Settings → Advanced
2. **User ID:** Right-click any user → Copy ID
3. **Channel ID:** Right-click the channel → Copy ID

---

### How to open Discord console?
Open Discord in your browser, press **F12** (or `Ctrl+Shift+I`), and click the **Console** tab — paste the script there or by opening the console in the browser.

---

### Can I delete messages from other users?
No. You can only delete messages from your own account. The script filters by the user ID you provide, but it still uses your token — so only your messages get deleted.

---

### Does it work on mobile?
Yes, but it's complicated. You'd need to use a browser with developer tools (like Kiwi Browser) or use desktop mode. For best results, use a desktop browser.

---

### How many messages can I delete at once?
Unlimited. The script fetches 100 messages at a time and deletes them in batches of 3. It will continue until all messages are deleted or you stop it.

---

## 🖥️ Script Usage

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



