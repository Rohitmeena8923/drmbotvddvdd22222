import os
import re
import math
import requests
import time

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyromod.exceptions import ListenerTimeout

# Shared stop set from main.py
STOP_DOWNLOADS = set()

async def process_drm(bot: Client, m, user_id: int):
    chat_id = m.chat.id

    # 1. Ask for .txt file with links
    prompt = "📄 **कृपया .txt फ़ाइल भेजें (प्रारूप: Title:URL)**"
    try:
        sent = await m.reply_text(prompt, quote=True)
    except Exception:
        sent = await bot.send_message(chat_id, prompt)

    # Listen for document
    try:
        file_msg = await bot.listen(chat_id=chat_id, filters=filters.document, timeout=120)
        if not file_msg.document.file_name.lower().endswith(".txt"):
            await sent.edit_text("**त्रुटि:** फ़ाइल .txt प्रारूप में नहीं है। कृपया पुनः प्रयास करें।")
            return
        await file_msg.delete(True)
    except ListenerTimeout:
        await sent.edit_text("**समय समाप्त! बहुत देर हो गई है।**")
        return
    except Exception as e:
        await sent.edit_text(f"**त्रुटि:** {e}")
        return

    # Download the .txt file
    try:
        file_path = await bot.download_media(file_msg, file_name="links.txt")
    except Exception as e:
        await sent.edit_text(f"**फ़ाइल डाउनलोड करते समय त्रुटि:** {e}")
        return

    # 2. Parse links
    links = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line or ':' not in line:
                continue
            title, url = line.split(':', 1)
            title = title.strip()
            url = url.strip()
            if title and url:
                links.append((title, url))
    except Exception as e:
        await sent.edit_text(f"**फ़ाइल पार्स करते समय त्रुटि:** {e}")
        return
    finally:
        # Clean up the uploaded file
        try:
            os.remove(file_path)
        except Exception:
            pass

    if not links:
        await sent.edit_text("**त्रुटि:** फ़ाइल में कोई वैध लिंक नहीं मिला।")
        return

    total = len(links)
    video_count = sum(1 for t, u in links if not u.lower().endswith('.pdf'))
    pdf_count = total - video_count

    overview = f"🔢 **कुल लिंक्स**: {total}\n🎯 **वीडियो**: {video_count}\n📄 **PDF**: {pdf_count}"
    await sent.edit_text(overview)

    # 3. Ask for starting index
    prompt_idx = "**कृपया शुरूआती इंडेक्स नंबर बताएं (उदाहरण: 3)**"
    try:
        msg_idx = await sent.reply_text(prompt_idx)
    except Exception:
        msg_idx = await bot.send_message(chat_id, prompt_idx)
    try:
        idx_msg = await bot.listen(chat_id=chat_id, filters=filters.user(user_id), timeout=120)
        await idx_msg.delete(True)
    except ListenerTimeout:
        await msg_idx.edit_text("**समय समाप्त! बहुत देर हो गई है।**")
        return

    try:
        start_index = int(idx_msg.text.strip())
        if start_index < 1 or start_index > total:
            raise ValueError
    except Exception:
        await msg_idx.edit_text("**गलत इंडेक्स! कृपया पुनः /start करके सही इंडेक्स बताएं।**")
        return
    start_index -= 1  # zero-based

    # 4. Ask for quality
    prompt_q = "**कृपया एक क्वालिटी चुनें:**"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("360p", callback_data="drm_quality_360p")],
        [InlineKeyboardButton("480p", callback_data="drm_quality_480p")],
        [InlineKeyboardButton("720p", callback_data="drm_quality_720p")],
        [InlineKeyboardButton("1080p", callback_data="drm_quality_1080p")]
    ])
    try:
        msg_q = await bot.send_message(chat_id, prompt_q, reply_markup=keyboard)
    except Exception:
        msg_q = await sent.edit_text(prompt_q, reply_markup=keyboard)

    try:
        callback: CallbackQuery = await bot.listen(chat_id=chat_id, filters=filters.user(user_id) & filters.regex("^drm_quality_"))
        await callback.answer()
        quality = callback.data.split("_")[-1]  # e.g. '720p'
        await callback.message.delete()
    except ListenerTimeout:
        await msg_q.edit_text("**समय समाप्त! बहुत देर हो गई है।**", reply_markup=None)
        return
    except Exception as e:
        await msg_q.edit_text(f"**त्रुटि:** {e}", reply_markup=None)
        return

    # 5. Ask for batch name
    prompt_batch = "**बैच का नाम दर्ज करें (या 'C' टाइप करें .txt फ़ाइल नाम उपयोग करने के लिए)**"
    try:
        msg_batch = await bot.send_message(chat_id, prompt_batch)
    except Exception:
        msg_batch = await sent.edit_text(prompt_batch)
    try:
        batch_msg = await bot.listen(chat_id=chat_id, filters=filters.user(user_id), timeout=120)
        await batch_msg.delete(True)
    except ListenerTimeout:
        await msg_batch.edit_text("**समय समाप्त! बहुत देर हो गई है।**")
        return

    batch_text = batch_msg.text.strip()
    if batch_text.lower() == 'c':
        # Use the .txt filename (without extension) as batch name
        batch_name = os.path.splitext(os.path.basename(file_msg.document.file_name))[0]
    else:
        batch_name = batch_text

    # 6. Ask for 'Extracted by' text
    prompt_ext = "**Extracted by टेक्स्ट दर्ज करें (छोड़ने पर डिफ़ॉल्ट 'Jaat')**"
    try:
        msg_ext = await bot.send_message(chat_id, prompt_ext)
    except Exception:
        msg_ext = await sent.edit_text(prompt_ext)
    try:
        ext_msg = await bot.listen(chat_id=chat_id, filters=filters.user(user_id), timeout=120)
        await ext_msg.delete(True)
    except ListenerTimeout:
        await msg_ext.edit_text("**समय समाप्त! बहुत देर हो गई है।**")
        return

    extracted_by = ext_msg.text.strip() or "Jaat"

    # 7. Process each link starting from the chosen index
    start_time = time.time()
    for idx, (title, url) in enumerate(links[start_index:], start_index+1):
        # Check if /stop was issued
        if user_id in STOP_DOWNLOADS:
            break

        # Prepare caption (with emojis)
        topic_short = title[:20] + ("..." if len(title) > 20 else "")
        caption = (
            f"🔢 Index: {idx}\n"
            f"🎯 Topic: {topic_short}\n"
            f"🗂️ Batch: {batch_name}\n"
            f"✍️ Extracted by: {extracted_by}"
        )

        # Determine if link is PDF or video
        if url.lower().endswith('.pdf'):
            # PDF: download and send
            dl_msg = await bot.send_message(chat_id, f"📥 डाउनलोड हो रहा है: {topic_short}")
            try:
                res = requests.get(url, stream=True)
                file_name = f"{idx}_{re.sub(r'[^0-9a-zA-Z]+', '_', title)}.pdf"
                with open(file_name, 'wb') as f:
                    f.write(res.content)
                await dl_msg.edit_text(f"✅ डाउनलोड पूरा: {topic_short}")
            except Exception as e:
                await dl_msg.edit_text(f"**डाउनलोड त्रुटि:** {e}")
                continue

            ul_msg = await bot.send_message(chat_id, f"📤 अपलोड हो रहा है: {topic_short}")
            try:
                await bot.send_document(chat_id, file_name, caption=caption)
                await ul_msg.edit_text(f"✅ अपलोड पूरा: {topic_short}")
            except Exception as e:
                await ul_msg.edit_text(f"**अपलोड त्रुटि:** {e}")
            os.remove(file_name)

        else:
            # Video: use dragoapi prefix and download
            drm_url = f"https://dragoapi.vercel.app/video/{url}"
            dl_msg = await bot.send_message(chat_id, f"📥 डाउनलोड हो रहा है: {topic_short}")
            try:
                res = requests.get(drm_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
                total_length = res.headers.get('content-length')
                base_name = re.sub(r'[^0-9a-zA-Z]+', '_', title)
                file_name = f"{idx}_{base_name}.mp4"
                if total_length is None:
                    # Unknown size
                    with open(file_name, 'wb') as f:
                        f.write(res.content)
                else:
                    dl = 0
                    total_length = int(total_length)
                    with open(file_name, 'wb') as f:
                        for data in res.iter_content(chunk_size=4096):
                            if not data:
                                break
                            f.write(data)
                            dl += len(data)
                            percent = (dl / total_length) * 100
                            # Update every ~10%
                            if percent % 10 < 1:
                                await dl_msg.edit_text(f"📥 डाउनलोड हो रहा है: {percent:.0f}%")
                await dl_msg.edit_text(f"✅ डाउनलोड पूरा: {topic_short}")
            except Exception as e:
                await dl_msg.edit_text(f"**डाउनलोड त्रुटि:** {e}")
                continue

            # Check file size and split if needed (>1.5GB)
            try:
                size_bytes = os.path.getsize(file_name)
                max_bytes = 1.5 * 1024**3
                if size_bytes > max_bytes:
                    parts = math.ceil(size_bytes / max_bytes)
                    with open(file_name, 'rb') as f:
                        for part in range(1, int(parts) + 1):
                            part_file = f"{base_name}_part{part}.mp4"
                            with open(part_file, 'wb') as pf:
                                pf.write(f.read(int(max_bytes)))
                            ul_msg = await bot.send_message(chat_id, f"📤 अपलोड हो रहा है (भाग {part}/{int(parts)}): {topic_short}")
                            try:
                                part_caption = f"{caption}\n(Part {part}/{int(parts)})"
                                await bot.send_video(chat_id, part_file, caption=part_caption)
                                await ul_msg.edit_text(f"✅ अपलोड पूरा (भाग {part}/{int(parts)}): {topic_short}")
                            except Exception as e:
                                await ul_msg.edit_text(f"**अपलोड त्रुटि:** {e}")
                            os.remove(part_file)
                    os.remove(file_name)
                else:
                    ul_msg = await bot.send_message(chat_id, f"📤 अपलोड हो रहा है: {topic_short}")
                    try:
                        await bot.send_video(chat_id, file_name, caption=caption)
                        await ul_msg.edit_text(f"✅ अपलोड पूरा: {topic_short}")
                    except Exception as e:
                        await ul_msg.edit_text(f"**अपलोड त्रुटि:** {e}")
                    os.remove(file_name)
            except Exception as e:
                # If splitting or uploading fails
                await bot.send_message(chat_id, f"**प्रसंस्करण त्रुटि:** {e}")

    # Remove stop flag if set
    if user_id in STOP_DOWNLOADS:
        STOP_DOWNLOADS.remove(user_id)

    # Final summary
    elapsed = int(time.time() - start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    summary = f"🏁 प्रक्रिया पूरी हुई!\n⏱ कुल समय लिया: {minutes} मिनट {seconds} सेकंड"
    await bot.send_message(chat_id, summary)
