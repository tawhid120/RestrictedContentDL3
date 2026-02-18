# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
import os
from time import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import PeerIdInvalid, BadRequest
from pyleaves import Leaves
from datetime import datetime
from utils import (
    getChatMsgID,
    processMediaGroup,
    get_parsed_msg,
    fileSizeLimit,
    progressArgs,
    send_media_to_saved,   # ← Bot দিয়ে নয়, User Client দিয়ে Saved Messages-এ
    get_readable_file_size,
    get_readable_time,
)
from utils.logging_setup import LOGGER
from config import COMMAND_PREFIX
from core import prem_plan1, prem_plan2, prem_plan3, user_sessions, user_activity_collection

user = None
pdl_data = {}

def setup_pvt_handler(app: Client):

    async def is_premium_user(user_id: int) -> bool:
        current_time = datetime.utcnow()
        for plan_collection in [prem_plan1, prem_plan2, prem_plan3]:
            plan = plan_collection.find_one({"user_id": user_id})
            if plan and plan.get("expiry_date", current_time) > current_time:
                return True
        return False

    async def get_user_client(user_id: int, session_id: str) -> Client:
        global user
        user_session = user_sessions.find_one({"user_id": user_id})
        if not user_session or not user_session.get("sessions"):
            return None
        session = next((s for s in user_session["sessions"] if s["session_id"] == session_id), None)
        if not session:
            return None
        if user is not None:
            try:
                await user.stop()
            except Exception as e:
                LOGGER.error(f"Error stopping existing user client: {e}")
            user = None
        try:
            user = Client(
                f"user_session_{user_id}_{session_id}",
                workers=1000,
                session_string=session["session_string"]
            )
            await user.start()
            return user
        except Exception as e:
            LOGGER.error(f"Failed to initialize user client for user {user_id}: {e}")
            return None

    async def show_account_selection(client: Client, message: Message, post_url: str = None):
        user_id = message.from_user.id
        user_session = user_sessions.find_one({"user_id": user_id})
        if not user_session or not user_session.get("sessions"):
            return None

        sessions = user_session.get("sessions", [])
        if len(sessions) == 1:
            return sessions[0]["session_id"]

        pdl_data[message.chat.id] = {"post_url": post_url, "message_id": message.id}

        buttons = []
        for i in range(0, len(sessions), 2):
            row = []
            for session in sessions[i:i+2]:
                row.append(InlineKeyboardButton(
                    session["account_name"],
                    callback_data=f"pdl_select_{session['session_id']}"
                ))
            buttons.append(row)
        buttons.append([InlineKeyboardButton("Cancel", callback_data="pdl_cancel")])

        await message.reply_text(
            "**📤 কোন account দিয়ে download করবেন?**\n"
            "_(এই account-এর Saved Messages-এ file যাবে)_",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN
        )
        return None

    @app.on_message(filters.command("pdl", prefixes=COMMAND_PREFIX) & filters.private)
    async def handle_pdl(bot: Client, message: Message):
        user_id = message.from_user.id

        if not await is_premium_user(user_id):
            LOGGER.warning(f"Non-premium user {user_id} attempted /pdl")
            await message.reply_text(
                "**❌ Only premium users can use /pdl! Please upgrade: /plans**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        user_session = user_sessions.find_one({"user_id": user_id})
        if not user_session or not user_session.get("sessions"):
            await message.reply_text(
                "**❌ You must log in with /login to use /pdl!**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        post_url = message.command[1] if len(message.command) > 1 else None
        if post_url and "?" in post_url:
            post_url = post_url.split("?", 1)[0]

        selected_session_id = await show_account_selection(bot, message, post_url)
        if selected_session_id:
            await process_pdl(bot, message, selected_session_id, post_url)

    @app.on_callback_query(filters.regex(r"^(pdl_select_|pdl_cancel)"))
    async def pdl_callback_handler(client, callback_query):
        data = callback_query.data
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id

        if data == "pdl_cancel":
            await callback_query.message.edit_text(
                "**❌ Private download cancelled.**",
                parse_mode=ParseMode.MARKDOWN
            )
            if chat_id in pdl_data:
                del pdl_data[chat_id]
            return

        if data.startswith("pdl_select_"):
            session_id = data.split("_", 2)[2]
            pdl_info = pdl_data.get(chat_id, {})
            post_url = pdl_info.get("post_url")
            original_message_id = pdl_info.get("message_id")

            original_message = await client.get_messages(chat_id, original_message_id)
            await callback_query.message.delete()

            await process_pdl(client, original_message, session_id, post_url)
            if chat_id in pdl_data:
                del pdl_data[chat_id]

    async def process_pdl(bot: Client, message: Message, session_id: str, post_url: str):
        user_id = message.from_user.id

        # ── User Client initialize করো ──
        user_client = await get_user_client(user_id, session_id)
        if user_client is None:
            await message.reply_text(
                "**❌ Failed to initialize user client! Please try logging in again.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        if not post_url:
            await message.reply_text(
                "**❌ Invalid format! Usage: /pdl {post_url}**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Bot-এ শুধু status message
        status_msg = await message.reply_text(
            "**🔍 Link processing... ⏳**\n"
            "_(ফাইল আপনার Saved Messages-এ যাবে, bot-এ নয়)_",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            chat_id, message_id = getChatMsgID(post_url)
            # User client দিয়ে message fetch করো
            chat_message = await user_client.get_messages(chat_id=chat_id, message_ids=message_id)

            LOGGER.info(f"Downloading media from URL: {post_url} for user {user_id}")

            # File size check
            if chat_message.document or chat_message.video or chat_message.audio:
                file_size = (
                    chat_message.document.file_size if chat_message.document else
                    chat_message.video.file_size if chat_message.video else
                    chat_message.audio.file_size
                )
                if not await fileSizeLimit(file_size, message, "download", await is_premium_user(user_id)):
                    await status_msg.delete()
                    return

            parsed_caption = await get_parsed_msg(chat_message.caption or "", chat_message.caption_entities)
            parsed_text = await get_parsed_msg(chat_message.text or "", chat_message.entities)

            # Media group হলে
            if chat_message.media_group_id:
                await status_msg.delete()
                if not await processMediaGroup(chat_message, bot, message, user_client=user_client):
                    await message.reply_text(
                        "**❌ Could not extract any valid media from the media group.**",
                        parse_mode=ParseMode.MARKDOWN
                    )
                return

            # Single media হলে
            elif chat_message.media:
                start_time = time()
                progress_message = await message.reply_text(
                    "**📥 Downloading...**",
                    parse_mode=ParseMode.MARKDOWN
                )
                await status_msg.delete()

                # User client দিয়ে download
                media_path = await chat_message.download(
                    progress=Leaves.progress_for_pyrogram,
                    progress_args=progressArgs("📥 Downloading", progress_message, start_time),
                )

                LOGGER.info(f"Downloaded: {media_path}")

                # User-এর thumbnail
                user_data = user_activity_collection.find_one({"user_id": user_id})
                thumbnail_path = user_data.get("thumbnail_path") if user_data else None

                media_type = (
                    "photo" if chat_message.photo else
                    "video" if chat_message.video else
                    "audio" if chat_message.audio else
                    "document"
                )

                # ── KEY CHANGE: User Client দিয়ে Saved Messages-এ upload ──
                await send_media_to_saved(
                    user_client=user_client,
                    bot=bot,
                    message=message,
                    media_path=media_path,
                    media_type=media_type,
                    caption=parsed_caption,
                    progress_message=progress_message,
                    start_time=start_time,
                    thumbnail_path=thumbnail_path
                )

                # Local file cleanup
                if os.path.exists(media_path):
                    os.remove(media_path)

            # Text only message হলে
            elif chat_message.text or chat_message.caption:
                await status_msg.delete()
                await message.reply_text(parsed_text or parsed_caption, parse_mode=ParseMode.MARKDOWN)

            else:
                await status_msg.delete()
                await message.reply_text(
                    "**❌ No media or text found in the post URL.**",
                    parse_mode=ParseMode.MARKDOWN
                )

        except (PeerIdInvalid, BadRequest):
            try:
                await status_msg.delete()
            except:
                pass
            await message.reply_text(
                "**❌ Make sure the user client is part of the chat.**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"User {user_id} not part of chat for URL: {post_url}")

        except Exception as e:
            try:
                await status_msg.delete()
            except:
                pass
            await message.reply_text(
                f"**❌ {str(e)}**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"Error in /pdl for user {user_id}: {e}")

        finally:
            if user:
                try:
                    await user.stop()
                except Exception as e:
                    LOGGER.error(f"Error stopping user client: {e}")

    app.add_handler(app.on_message, group=1)
    app.add_handler(app.on_callback_query, group=2)
