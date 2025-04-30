import os
import re
import math
import requests
import time

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyromod.exceptions import ListenerTimeout

STOP_DOWNLOADS = set()

async def process_drm(bot: Client, m, user_id: int):
    chat_id = m.chat.id

    await m.reply_text("📄 कृपया .txt फ़ाइल भेजें (प्रारूप: Title:URL per line)")
    try:
        file_msg = await bot.listen(chat_id, filters=filters.document, timeout=120)
        if not file_msg.document.file_name.endswith(".txt"):
            await m.reply("❌ केवल .txt फ़ाइल स्वीकार है")
            return
    except ListenerTimeout:
        await m.reply("⏰ समय समाप्त हो गया, कृपया फिर से कोशिश करें")
        return

    file_path = await bot.download_media(file_msg)
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if ':' in line]
        links = [(line.split(":", 1)[0].strip(), line.split(":", 1)[1].strip()) for line in lines]

    if not links:
        await m.reply("❌ कोई वैध लिंक नहीं मिला")
        return

    total = len(links)
    pdf_count = sum(1 for _, url in links if url.lower().endswith(".pdf"))
    video_count = total - pdf_count
    await m.reply(f"🔢 कुल लिंक: {total}\n🎞️ वीडियो: {video_count}\n📚 PDF: {pdf_count}")

    # Index input
    await m.reply("🔢 किस Index से शुरू करना है? (उदाहरण: 1)")
    idx_msg = await bot.listen(chat_id, filters.user(user_id), timeout=60)
    try:
        start_index = int(idx_msg.text.strip()) - 1
    except:
        await m.reply("❌ गलत Index")
        return

    # Quality
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("360p", callback_data="q360")],
        [InlineKeyboardButton("480p", callback_data="q480")],
        [InlineKeyboardButton("720p", callback_data="q720")],
        [InlineKeyboardButton("1080p", callback_data="q1080")]
    ])
    msg = await m.reply("🎚️ एक क्वालिटी चुनें:", reply_markup=keyboard)
    cb = await bot.listen(chat_id, filters.user(user_id) & filters.regex("^q"))
    await cb.answer()
    quality = cb.data.replace("q", "")

    # Batch name
    await m.reply("🗂️ Batch Name डालें (या 'C' भेजें फ़ाइल नाम का उपयोग करने के लिए)")
    batch_msg = await bot.listen(chat_id, filters.user(user_id), timeout=60)
    batch_name = batch_msg.text.strip()
    if batch_name.lower() == 'c':
        batch_name = os.path.splitext(os.path.basename(file_msg.document.file_name))[0]

    # Extracted by
    await m.reply("✍️ Extracted by में क्या लिखना है? (छोड़ने पर 'Jaat')")
    ext_msg = await bot.listen(chat_id, filters.user(user_id), timeout=60)
    extracted_by = ext_msg.text.strip() or "Jaat"

    # Download loop
    start_time = time.time()
    for idx, (title, url) in enumerate(links[start_index:], start=start_index + 1):
        if user_id in STOP_DOWNLOADS:
            break

        topic = title.strip()[:30]
        caption = f"🔢 Index: {idx}\n🎯 Topic: {topic}\n🗂️ Batch: {batch_name}\n✍️ Extracted by: {extracted_by}"

        file_name = f"{idx}_{re.sub(r'[^0-9a-zA-Z]+', '_', topic)}"
        if url.lower().endswith(".pdf"):
            res = requests.get(url)
            pdf_file = file_name + ".pdf"
            with open(pdf_file, "wb") as f:
                f.write(res.content)
            await bot.send_document(chat_id, pdf_file, caption=caption)
            os.remove(pdf_file)
        else:
            drm_url = f"https://dragoapi.vercel.app/video/{url}"
            r = requests.get(drm_url, stream=True, headers={"User-Agent": "Mozilla/5.0"})
            video_path = file_name + ".mp4"
            with open(video_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            size = os.path.getsize(video_path)
            if size > 1.5 * 1024**3:
                await bot.send_message(chat_id, "⚠️ वीडियो बड़ा है, स्प्लिट किया जाएगा")
                with open(video_path, 'rb') as f:
                    part = 1
                    while chunk := f.read(int(1.5 * 1024**3)):
                        part_file = f"{file_name}_part{part}.mp4"
                        with open(part_file, "wb") as pf:
                            pf.write(chunk)
                        await bot.send_video(chat_id, part_file, caption=f"{caption}\n📦 Part {part}")
                        os.remove(part_file)
                        part += 1
                os.remove(video_path)
            else:
                await bot.send_video(chat_id, video_path, caption=caption)
                os.remove(video_path)

    elapsed = int(time.time() - start_time)
    await bot.send_message(chat_id, f"✅ Done!⏱️ Total Time: {elapsed // 60}m {elapsed % 60}s")
    if user_id in STOP_DOWNLOADS:
        STOP_DOWNLOADS.remove(user_id)
