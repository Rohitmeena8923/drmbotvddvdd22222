# 🛡️ DRM Video Downloader Telegram Bot

A powerful all-in-one Telegram bot to download DRM-protected videos using DragoAPI and stream-sniffing style logic (like 1DM). This bot supports batch downloading, PDF handling, and automatic captioning with an interactive UI.

---

## ✨ Features

- Upload `.txt` file containing `Title:URL` pairs
- Auto-link conversion using DragoAPI
- Ask user for:
  - Starting index
  - Video quality (360p, 480p, 720p, 1080p)
  - Batch name (or use filename)
  - Extracted by (default: Jaat)
- Show download/upload progress
- Skip PDFs and upload them with captions
- Handle large videos (split >1.5 GB into parts)
- Emoji-enhanced captions:
  ```
  🔢 Index: 1
  🎯 Topic: L-1 Constitution
  🗂️ Batch: Target_2025
  ✍️ Extracted by: Jaat
  ```
- `/stop` command to stop next videos in queue

---

## 📁 Folder Structure

```
drm-downloader-bot/
├── main.py
├── config.py
├── requirements.txt
├── utils.py
└── plugins/
    └── drm_handler.py
```

---

## ⚙️ Setup Instructions

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/drm-downloader-bot.git
cd drm-downloader-bot
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Set Your Config

Update `config.py` or set as environment variables:
- `API_ID`
- `API_HASH`
- `BOT_TOKEN`
- `auth_users = [123456789]`

### 4. Run the Bot

```bash
python main.py
```

---

## 🧪 Example .txt File Format

```
L-1 Constitution:https://media-cdn.classplusapp.com/xyz/playlist.m3u8
L-2 Rights:https://media-cdn.classplusapp.com/abc/playlist.m3u8
PDF Chapter:https://example.com/chapter.pdf
```

---

## ✅ Credits

Built with ❤️ by **Pradeep**  
Bot powered by [Pyrogram](https://docs.pyrogram.org) and [DragoAPI](https://dragoapi.vercel.app/video/)