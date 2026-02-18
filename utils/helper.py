# Copyright @TheSmartBisnu
# Channel t.me/ItsSmartDev
# Update Author @ISmartDevs
# Channel t.me/TheSmartDev
from asyncio.subprocess import PIPE
import os
from time import time
from typing import Optional
from asyncio import create_subprocess_exec, create_subprocess_shell, wait_for
from PIL import Image
from pyleaves import Leaves
from pyrogram.parser import Parser
from pyrogram.utils import get_channel_id
from pyrogram.types import (
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    InputMediaAudio,
    Voice,
)

from .logging_setup import LOGGER

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]

def get_readable_file_size(size_in_bytes: Optional[float]) -> str:
    if size_in_bytes is None or size_in_bytes < 0:
        return "0B"
    for unit in SIZE_UNITS:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return "File too large"

def get_readable_time(seconds: int) -> str:
    result = ""
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f"{days}d"
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f"{hours}h"
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f"{minutes}m"
    seconds = int(seconds)
    result += f"{seconds}s"
    return result

async def fileSizeLimit(file_size, message, action_type="download", is_premium=False):
    MAX_FILE_SIZE = 2 * 2097152000 if is_premium else 2097152000
    if file_size > MAX_FILE_SIZE:
        await message.reply(
            f"The file size exceeds the {get_readable_file_size(MAX_FILE_SIZE)} limit and cannot be {action_type}ed."
        )
        return False
    return True

async def get_parsed_msg(text, entities):
    return Parser.unparse(text, entities or [], is_html=False)

PROGRESS_BAR = """
Percentage: {percentage:.2f}% | {current}/{total}
Speed: {speed}/s
Estimated Time Left: {est_time} seconds
"""

def getChatMsgID(link: str):
    linkps = link.split("/")
    chat_id, message_thread_id, message_id = None, None, None

    try:
        if len(linkps) == 7 and linkps[3] == "c":
            chat_id = get_channel_id(int(linkps[4]))
            message_thread_id = int(linkps[5])
            message_id = int(linkps[6])
        elif len(linkps) == 6:
            if linkps[3] == "c":
                chat_id = get_channel_id(int(linkps[4]))
                message_id = int(linkps[5])
            else:
                chat_id = linkps[3]
                message_thread_id = int(linkps[4])
                message_id = int(linkps[5])
        elif len(linkps) == 5:
            chat_id = linkps[3]
            if chat_id == "m":
                raise ValueError("Invalid ClientType used to parse this message link")
            message_id = int(linkps[4])
    except (ValueError, TypeError):
        raise ValueError("Invalid post URL. Must end with a numeric ID.")

    if not chat_id or not message_id:
        raise ValueError("Please send a valid Telegram post URL.")

    return chat_id, message_id

async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    try:
        stdout = stdout.decode().strip()
    except:
        stdout = "Unable to decode the response!"
    try:
        stderr = stderr.decode().strip()
    except:
        stderr = "Unable to decode the error!"
    return stdout, stderr, proc.returncode

async def get_media_info(path):
    try:
        result = await cmd_exec([
            "ffprobe", "-hide_banner", "-loglevel", "error",
            "-print_format", "json", "-show_format", path,
        ])
    except Exception as e:
        LOGGER.error(f"Get Media Info: {e}. Mostly File not found! - File: {path}")
        return 0, None, None
    if result[0] and result[2] == 0:
        fields = eval(result[0]).get("format")
        if fields is None:
            LOGGER.error(f"get_media_info: {result}")
            return 0, None, None
        duration = round(float(fields.get("duration", 0)))
        tags = fields.get("tags", {})
        artist = tags.get("artist") or tags.get("ARTIST") or tags.get("Artist")
        title = tags.get("title") or tags.get("TITLE") or tags.get("Title")
        return duration, artist, title
    return 0, None, None

async def get_video_thumbnail(video_file, duration):
    output = os.path.join("Assets", "video_thumb.jpg")
    if duration is None:
        duration = (await get_media_info(video_file))[0]
    if duration == 0:
        duration = 3
    timestamp = 2
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-ss", f"{timestamp}", "-i", video_file,
        "-vf", "thumbnail", "-q:v", "1", "-frames:v", "1",
        "-threads", f"{os.cpu_count() // 2}", output,
    ]
    try:
        _, err, code = await wait_for(cmd_exec(cmd), timeout=60)
        if code != 0 or not os.path.exists(output):
            LOGGER.error(f"Error extracting thumbnail. Name: {video_file} stderr: {err}")
            return None
    except Exception as e:
        LOGGER.error(f"Error extracting thumbnail. Name: {video_file}. Error: {e}")
        return None
    return output

def progressArgs(action: str, progress_message, start_time):
    return (action, progress_message, start_time, PROGRESS_BAR, "▓", "░")


# ═══════════════════════════════════════════════════════════════════════════
# OPTIMIZED: User Client initialize করার helper
# max_concurrent_transmissions বাড়িয়ে স্পিড boost করা হয়েছে
# ═══════════════════════════════════════════════════════════════════════════

def create_optimized_user_client(session_name: str, session_string: str):
    """
    Optimized user client তৈরি করে।
    - workers=500: parallel task handling
    - max_concurrent_transmissions=5: একসাথে ৫টা upload/download চলতে পারবে
    """
    from pyrogram import Client as PyroClient
    return PyroClient(
        session_name,
        session_string=session_string,
        workers=500,
        max_concurrent_transmissions=5,  # ← এটাই upload স্পিড বাড়ানোর মূল চাবিকাঠি
    )


# ═══════════════════════════════════════════════════════════════════════════
# NEW CORE FUNCTION: User Client দিয়ে Saved Messages-এ পাঠানো
# ─────────────────────────────────────────────────────────────────────────
# Bot কোনো media file পাঠাবে না।
# সব upload হবে user-এর নিজের logged-in account দিয়ে,
# তার নিজের "Saved Messages" ফোল্ডারে।
# Bot শুধু notification message পাঠাবে (text only)।
# ═══════════════════════════════════════════════════════════════════════════

async def send_media_to_saved(
    user_client,         # Logged-in pyrogram user Client
    bot,                 # Bot client - শুধু text notification-এর জন্য
    message,             # Original bot chat message
    media_path,          # Downloaded file-এর local path
    media_type,          # "photo" / "video" / "audio" / "document"
    caption,             # Caption text
    progress_message,    # Progress message (bot chat-এ)
    start_time,          # Upload progress start time
    thumbnail_path=None  # Custom thumbnail path (optional)
):
    """
    User Client দিয়ে ফাইল নিজের Saved Messages-এ আপলোড করে।

    ✅ Bot ব্যান হওয়ার ঝুঁকি নেই কারণ:
       - Bot কোনো media পাঠায় না
       - User নিজের account থেকে নিজেই upload করে
       - Telegram-এর দৃষ্টিতে এটা normal user activity
    
    🚀 স্পিড অপ্টিমাইজেশন:
       - tgcrypto-pyrofork: C-level encryption (Python-এর চেয়ে অনেক দ্রুত)
       - uvloop: event loop 2-4x দ্রুত
       - max_concurrent_transmissions=5: parallel chunks
    """
    file_size = os.path.getsize(media_path)

    if not await fileSizeLimit(file_size, message, "upload"):
        await progress_message.delete()
        return False

    # User-এর Saved Messages = "me"
    saved_messages_chat = "me"
    progress_args = progressArgs("📤 Uploading to Saved Messages", progress_message, start_time)
    LOGGER.info(f"[USER CLIENT] Uploading to Saved Messages: {media_path} ({media_type})")

    try:
        if media_type == "photo":
            await user_client.send_photo(
                chat_id=saved_messages_chat,
                photo=media_path,
                caption=caption or "",
                progress=Leaves.progress_for_pyrogram,
                progress_args=progress_args,
            )

        elif media_type == "video":
            duration = (await get_media_info(media_path))[0]
            thumb = thumbnail_path
            width, height = 480, 320

            if thumb is None:
                if os.path.exists("Assets/video_thumb.jpg"):
                    os.remove("Assets/video_thumb.jpg")
                thumb = await get_video_thumbnail(media_path, duration)

            if thumb and os.path.exists(thumb):
                with Image.open(thumb) as img:
                    width, height = img.size
            else:
                thumb = None

            await user_client.send_video(
                chat_id=saved_messages_chat,
                video=media_path,
                duration=duration,
                width=width,
                height=height,
                thumb=thumb,
                caption=caption or "",
                progress=Leaves.progress_for_pyrogram,
                progress_args=progress_args,
            )

        elif media_type == "audio":
            duration, artist, title = await get_media_info(media_path)
            await user_client.send_audio(
                chat_id=saved_messages_chat,
                audio=media_path,
                duration=duration,
                performer=artist,
                title=title,
                thumb=thumbnail_path,
                caption=caption or "",
                progress=Leaves.progress_for_pyrogram,
                progress_args=progress_args,
            )

        elif media_type == "document":
            await user_client.send_document(
                chat_id=saved_messages_chat,
                document=media_path,
                thumb=thumbnail_path,
                caption=caption or "",
                progress=Leaves.progress_for_pyrogram,
                progress_args=progress_args,
            )

        else:
            LOGGER.error(f"Unknown media_type: {media_type}")
            await progress_message.delete()
            return False

        # Progress message delete করো
        await progress_message.delete()

        # Bot শুধু text notification পাঠাবে — কোনো file নয়
        await bot.send_message(
            chat_id=message.chat.id,
            text=(
                "**✅ ফাইল সফলভাবে আপনার Saved Messages-এ পাঠানো হয়েছে! 🚀**\n\n"
                "📂 **Telegram খুলুন → Saved Messages** — ফাইলটি সেখানে পাবেন।\n\n"
                "_(Bot কোনো file পাঠায় না, তাই আপনার privacy সুরক্ষিত)_"
            )
        )

        LOGGER.info(f"[USER CLIENT] Upload successful to Saved Messages for user {message.from_user.id}")
        return True

    except Exception as e:
        LOGGER.error(f"[USER CLIENT] Error uploading to Saved Messages: {e}")
        try:
            await progress_message.delete()
        except:
            pass
        raise


# ═══════════════════════════════════════════════════════════════════════════
# processMediaGroup: Media group-ও User Client দিয়ে Saved Messages-এ যাবে
# ═══════════════════════════════════════════════════════════════════════════

async def processMediaGroup(chat_message, bot, message, user_client=None):
    """
    Media group download করে User Client দিয়ে Saved Messages-এ পাঠায়।
    user_client না দিলে bot দিয়ে পাঠানোর চেষ্টা করবে (fallback)।
    """
    media_group_messages = await chat_message.get_media_group()
    valid_media = []
    temp_paths = []
    invalid_paths = []

    start_time = time()
    progress_message = await message.reply("**📥 Downloading media group...**")
    LOGGER.info(f"Downloading media group with {len(media_group_messages)} items...")

    for msg in media_group_messages:
        if msg.photo or msg.video or msg.document or msg.audio:
            media_path = None
            try:
                media_path = await msg.download(
                    progress=Leaves.progress_for_pyrogram,
                    progress_args=progressArgs("📥 Downloading", progress_message, start_time),
                )
                temp_paths.append(media_path)

                caption_text = await get_parsed_msg(msg.caption or "", msg.caption_entities)

                if msg.photo:
                    valid_media.append(InputMediaPhoto(media=media_path, caption=caption_text))
                elif msg.video:
                    valid_media.append(InputMediaVideo(media=media_path, caption=caption_text))
                elif msg.document:
                    valid_media.append(InputMediaDocument(media=media_path, caption=caption_text))
                elif msg.audio:
                    valid_media.append(InputMediaAudio(media=media_path, caption=caption_text))

            except Exception as e:
                LOGGER.info(f"Error downloading media: {e}")
                if media_path and os.path.exists(media_path):
                    invalid_paths.append(media_path)
                continue

    LOGGER.info(f"Valid media count: {len(valid_media)}")

    if valid_media:
        # User client থাকলে Saved Messages-এ পাঠাও, না হলে bot দিয়ে চেষ্টা
        upload_client = user_client if user_client else bot
        upload_target = "me" if user_client else message.chat.id

        try:
            await upload_client.send_media_group(chat_id=upload_target, media=valid_media)
            await progress_message.delete()

            if user_client:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        "**✅ Media group আপনার Saved Messages-এ পাঠানো হয়েছে! 🚀**\n\n"
                        "📂 **Telegram → Saved Messages** খুলুন।"
                    )
                )
        except Exception:
            await message.reply("**❌ Media group একসাথে পাঠানো যায়নি। আলাদা করে চেষ্টা করা হচ্ছে...**")
            for media in valid_media:
                try:
                    if isinstance(media, InputMediaPhoto):
                        await upload_client.send_photo(chat_id=upload_target, photo=media.media, caption=media.caption)
                    elif isinstance(media, InputMediaVideo):
                        await upload_client.send_video(chat_id=upload_target, video=media.media, caption=media.caption)
                    elif isinstance(media, InputMediaDocument):
                        await upload_client.send_document(chat_id=upload_target, document=media.media, caption=media.caption)
                    elif isinstance(media, InputMediaAudio):
                        await upload_client.send_audio(chat_id=upload_target, audio=media.media, caption=media.caption)
                except Exception as individual_e:
                    await message.reply(f"**❌ Failed to upload: {individual_e}**")
            await progress_message.delete()

        # Cleanup temp files
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)
        for path in invalid_paths:
            if os.path.exists(path):
                os.remove(path)

        return True

    await progress_message.delete()
    await message.reply("**❌ No valid media found in the media group.**")
    for path in invalid_paths:
        if os.path.exists(path):
            os.remove(path)
    return False


# ═══════════════════════════════════════════════════════════════════════════
# LEGACY: পুরানো send_media — এখন deprecated, নতুন code ব্যবহার করুন
# ═══════════════════════════════════════════════════════════════════════════

async def send_media(
    bot, message, media_path, media_type, caption, progress_message, start_time, thumbnail_path=None
):
    """
    DEPRECATED: Bot দিয়ে file পাঠানো বন্ধ।
    send_media_to_saved(user_client, bot, ...) ব্যবহার করুন।
    """
    LOGGER.warning("send_media() is deprecated. Use send_media_to_saved() with user_client.")
    await progress_message.edit_text(
        "**⚠️ System error: Please contact support.**"
    )
    await progress_message.delete()
