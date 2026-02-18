# Copyright @juktijol
# Channel t.me/juktijol
# Auto Link Detector - Detects Telegram links and routes to correct handler

import os
import re
from time import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatType
from pyrogram.errors import ChannelInvalid, ChannelPrivate, PeerIdInvalid, FileReferenceExpired, BadRequest
from pyleaves import Leaves
from utils import (
    getChatMsgID,
    processMediaGroup,
    get_parsed_msg,
    fileSizeLimit,
    progressArgs,
    send_media,
    LOGGER
)
from core import (
    daily_limit,
    prem_plan1,
    prem_plan2,
    prem_plan3,
    user_sessions,
    user_activity_collection
)

# ─────────────────────────────────────────────
# Telegram লিংক detect করার Regex
# ─────────────────────────────────────────────
TELEGRAM_LINK_PATTERN = re.compile(
    r"(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?([a-zA-Z0-9_]+|\d+)/(\d+)(?:/\d+)?"
)


def is_private_link(url: str) -> bool:
    """
    লিংকটা private কিনা check করে।
    t.me/c/  → private
    t.me/username/ → public
    """
    return bool(re.search(r"(?:t\.me|telegram\.me)/c/", url))


def setup_autolink_handler(app: Client):

    # ──────────────────────────────────────────
    # Helper: Premium check
    # ──────────────────────────────────────────
    async def is_premium_user(user_id: int) -> bool:
        current_time = datetime.utcnow()
        for plan_collection in [prem_plan1, prem_plan2, prem_plan3]:
            plan = plan_collection.find_one({"user_id": user_id})
            if plan and plan.get("expiry_date", current_time) > current_time:
                return True
        return False

    # ──────────────────────────────────────────
    # Helper: User client initialize
    # ──────────────────────────────────────────
    async def get_user_client(user_id: int, session_id: str) -> Client:
        user_session = user_sessions.find_one({"user_id": user_id})
        if not user_session or not user_session.get("sessions"):
            return None
        session = next(
            (s for s in user_session["sessions"] if s["session_id"] == session_id), None
        )
        if not session:
            return None
        try:
            user_client = Client(
                f"user_session_{user_id}_{session_id}",
                workers=100,
                session_string=session["session_string"]
            )
            await user_client.start()
            return user_client
        except Exception as e:
            LOGGER.error(f"Failed to initialize user client for user {user_id}: {e}")
            return None

    # ──────────────────────────────────────────
    # PUBLIC লিংক handle করা
    # ──────────────────────────────────────────
    async def handle_public_link(client: Client, message: Message, url: str):
        user_id = message.from_user.id
        chat_id = message.chat.id

        match = re.match(
            r"(?:https?://)?(?:t\.me|telegram\.me)/([a-zA-Z0-9_]+)/(\d+)", url
        )
        if not match:
            await message.reply_text(
                "**❌ Invalid public Telegram link!**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        channel_username = f"@{match.group(1)}"
        msg_id = int(match.group(2))

        is_premium = await is_premium_user(user_id)

        processing_msg = await message.reply_text(
            "**🔍 Link detected! Downloading restricted media ⏳**",
            parse_mode=ParseMode.MARKDOWN
        )

        # Channel accessibility check
        try:
            chat = await client.get_chat(channel_username)
            if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
                await processing_msg.edit_text(
                    "**❌ This command only supports channels or supergroups!**",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        except (ChannelInvalid, PeerIdInvalid):
            await processing_msg.edit_text(
                "**❌ Invalid channel or group! Ensure it's public and accessible.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        except ChannelPrivate:
            await processing_msg.edit_text(
                "**🔒 This channel is private! Please use a private link (t.me/c/...) or upgrade: /plans**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        except Exception as e:
            await processing_msg.edit_text(
                "**❌ Error accessing the channel!**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"Failed to fetch chat {channel_username}: {e}")
            return

        # Daily limit check (free users)
        if not is_premium:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            user_limit = daily_limit.find_one({"user_id": user_id})
            downloads = 0
            if user_limit and user_limit.get("date") and user_limit["date"] >= today:
                downloads = user_limit.get("downloads", 0)
            if downloads >= 10:
                await processing_msg.edit_text(
                    "**🚫 Daily limit of 10 downloads reached! Upgrade: /plans**",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            daily_limit.update_one(
                {"user_id": user_id},
                {"$set": {"downloads": downloads + 1, "date": today}, "$inc": {"total_downloads": 1}},
                upsert=True
            )
            remaining = 10 - (downloads + 1)
        else:
            daily_limit.update_one(
                {"user_id": user_id},
                {"$inc": {"total_downloads": 1}},
                upsert=True
            )
            remaining = None

        # Media fetch & send
        try:
            source_message = await client.get_messages(channel_username, msg_id)
            if not source_message:
                await processing_msg.edit_text(
                    "**❌ Message not found or deleted!**",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            if source_message.video:
                user_data = user_activity_collection.find_one({"user_id": user_id})
                thumbnail_file_id = user_data.get("thumbnail_file_id") if user_data else None
                try:
                    await client.send_video(
                        chat_id=chat_id,
                        video=source_message.video.file_id,
                        caption=source_message.caption or "",
                        parse_mode=ParseMode.MARKDOWN if source_message.caption else None,
                        thumb=thumbnail_file_id if thumbnail_file_id else None
                    )
                except FileReferenceExpired:
                    await client.send_video(
                        chat_id=chat_id,
                        video=source_message.video.file_id,
                        caption=source_message.caption or "",
                    )
            else:
                await client.copy_message(
                    chat_id=chat_id,
                    from_chat_id=channel_username,
                    message_id=msg_id
                )

            reminder = (
                f"**✅ Content received!\n\n📥 Daily limit left: {remaining}/10\n\nUpgrade for unlimited: /plans**"
                if not is_premium else
                "**✅ Content received! Enjoy unlimited downloads as a premium user! 🚀**"
            )
            await processing_msg.edit_text(reminder, parse_mode=ParseMode.MARKDOWN)
            LOGGER.info(f"Auto public DL: message {msg_id} from {channel_username} for user {user_id}")

        except Exception as e:
            await processing_msg.edit_text(
                f"**❌ Error: {str(e)}**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"Auto public DL failed for user {user_id}: {e}")

    # ──────────────────────────────────────────
    # PRIVATE লিংক handle করা
    # ──────────────────────────────────────────
    async def handle_private_link(client: Client, message: Message, url: str):
        user_id = message.from_user.id
        chat_id = message.chat.id

        # Premium check
        if not await is_premium_user(user_id):
            await message.reply_text(
                "**🔒 Private link detected!\n\n❌ Only premium users can download from private sources.\nUpgrade now: /plans**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Login check
        user_session = user_sessions.find_one({"user_id": user_id})
        if not user_session or not user_session.get("sessions"):
            await message.reply_text(
                "**🔒 Private link detected!\n\n❌ You must log in first with /login to download from private sources.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        sessions = user_session.get("sessions", [])

        # Multiple accounts → show selection
        if len(sessions) > 1:
            buttons = []
            for i in range(0, len(sessions), 2):
                row = []
                for sess in sessions[i:i+2]:
                    row.append(InlineKeyboardButton(
                        sess["account_name"],
                        callback_data=f"auto_pvt_select_{sess['session_id']}|{url}"
                    ))
                buttons.append(row)
            buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="auto_pvt_cancel")])
            await message.reply_text(
                "**🔒 Private link detected!\n\n📤 Select an account to download:**",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Single account → auto select
        session_id = sessions[0]["session_id"]
        await process_private_download(client, message, session_id, url)

    # ──────────────────────────────────────────
    # PRIVATE download process
    # ──────────────────────────────────────────
    async def process_private_download(bot: Client, message: Message, session_id: str, url: str):
        user_id = message.from_user.id
        chat_id = message.chat.id

        user_client = await get_user_client(user_id, session_id)
        if user_client is None:
            await message.reply_text(
                "**❌ Failed to initialize user client! Please try /login again.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        processing_msg = await message.reply_text(
            "**🔒 Private link detected! Downloading... ⏳**",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            url_clean = url.split("?")[0]
            pvt_chat_id, msg_id = getChatMsgID(url_clean)
            chat_message = await user_client.get_messages(chat_id=pvt_chat_id, message_ids=msg_id)

            if not chat_message:
                await processing_msg.edit_text(
                    "**❌ Message not found!**",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # File size check
            if chat_message.document or chat_message.video or chat_message.audio:
                file_size = (
                    chat_message.document.file_size if chat_message.document else
                    chat_message.video.file_size if chat_message.video else
                    chat_message.audio.file_size
                )
                if not await fileSizeLimit(file_size, message, "download", True):
                    await processing_msg.delete()
                    return

            parsed_caption = await get_parsed_msg(
                chat_message.caption or "", chat_message.caption_entities
            )
            parsed_text = await get_parsed_msg(
                chat_message.text or "", chat_message.entities
            )

            # Media group
            if chat_message.media_group_id:
                await processing_msg.delete()
                if not await processMediaGroup(chat_message, bot, message):
                    await message.reply_text(
                        "**❌ Could not extract media from the media group.**",
                        parse_mode=ParseMode.MARKDOWN
                    )
                return

            elif chat_message.media:
                start_time = time()
                await processing_msg.edit_text(
                    "**📥 Downloading Progress...**",
                    parse_mode=ParseMode.MARKDOWN
                )
                media_path = await chat_message.download(
                    progress=Leaves.progress_for_pyrogram,
                    progress_args=progressArgs("📥 Downloading Progress", processing_msg, start_time)
                )

                user_data = user_activity_collection.find_one({"user_id": user_id})
                thumbnail_path = user_data.get("thumbnail_path") if user_data else None

                media_type = (
                    "photo" if chat_message.photo else
                    "video" if chat_message.video else
                    "audio" if chat_message.audio else
                    "document"
                )
                await send_media(
                    bot, message, media_path, media_type,
                    parsed_caption, processing_msg, start_time,
                    thumbnail_path=thumbnail_path
                )

                if os.path.exists(media_path):
                    os.remove(media_path)
                await processing_msg.delete()

                await message.reply_text(
                    "**✅ Private content downloaded successfully! 🚀**",
                    parse_mode=ParseMode.MARKDOWN
                )

            elif chat_message.text or chat_message.caption:
                await processing_msg.delete()
                await message.reply_text(
                    parsed_text or parsed_caption,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await processing_msg.edit_text(
                    "**❌ No media or text found in this link.**",
                    parse_mode=ParseMode.MARKDOWN
                )

            LOGGER.info(f"Auto private DL: msg {msg_id} from {pvt_chat_id} for user {user_id}")

        except (PeerIdInvalid, BadRequest):
            await processing_msg.edit_text(
                "**❌ Make sure the logged-in account is a member of that channel/group.**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"User {user_id} not part of chat for URL: {url}")
        except Exception as e:
            await processing_msg.edit_text(
                f"**❌ Error: {str(e)}**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"Auto private DL failed for user {user_id}: {e}")
        finally:
            try:
                await user_client.stop()
            except Exception:
                pass

    # ──────────────────────────────────────────
    # Callback: Account selection (private link)
    # ──────────────────────────────────────────
    @app.on_callback_query(filters.regex(r"^auto_pvt_(select_|cancel)"))
    async def auto_pvt_callback(client, callback_query):
        data = callback_query.data
        user_id = callback_query.from_user.id

        if data == "auto_pvt_cancel":
            await callback_query.message.edit_text(
                "**❌ Download cancelled.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        if data.startswith("auto_pvt_select_"):
            # Format: auto_pvt_select_{session_id}|{url}
            payload = data[len("auto_pvt_select_"):]
            parts = payload.split("|", 1)
            if len(parts) != 2:
                await callback_query.message.edit_text(
                    "**❌ Invalid session data. Please try again.**",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            session_id, url = parts
            await callback_query.message.delete()
            await process_private_download(client, callback_query.message, session_id, url)

    # ──────────────────────────────────────────
    # MAIN HANDLER: যেকোনো message-এ Telegram লিংক detect
    # ──────────────────────────────────────────
    @app.on_message(
        filters.text &
        (filters.private | filters.group) &
        filters.create(lambda _, __, msg: bool(
            msg.text and TELEGRAM_LINK_PATTERN.search(msg.text)
        ))
    )
    async def auto_link_detector(client: Client, message: Message):
        """
        যদি কোনো message-এ Telegram লিংক থাকে কিন্তু কোনো command না থাকে,
        তাহলে এই handler সেটা detect করে public/private check করবে।
        """
        # Command দিয়ে পাঠালে ignore করব (dl, pdl ইত্যাদি already handle করছে)
        if message.text and message.text.startswith(("/", "!", ".", "#", ",")):
            return

        text = message.text or ""
        match = TELEGRAM_LINK_PATTERN.search(text)
        if not match:
            return

        # Full URL extract
        url_start = match.start()
        url_end = match.end()
        url = text[url_start:url_end]

        # http/https না থাকলে add করা
        if not url.startswith("http"):
            url = "https://" + url

        LOGGER.info(f"Auto link detected from user {message.from_user.id}: {url}")

        if is_private_link(url):
            LOGGER.info(f"Routing to PRIVATE handler for user {message.from_user.id}")
            await handle_private_link(client, message, url)
        else:
            LOGGER.info(f"Routing to PUBLIC handler for user {message.from_user.id}")
            await handle_public_link(client, message, url)
