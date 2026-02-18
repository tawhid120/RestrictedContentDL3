# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatType
from pyrogram.handlers import MessageHandler
from pyrogram.errors import ChannelInvalid, ChannelPrivate, PeerIdInvalid, FileReferenceExpired
from config import COMMAND_PREFIX
from utils.logging_setup import LOGGER
from utils.force_sub import check_force_sub, send_force_sub_message
from core import daily_limit, prem_plan1, prem_plan2, prem_plan3, user_activity_collection
from datetime import datetime
import re, asyncio


def setup_public_handler(app: Client):

    async def dl_command(client: Client, message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        # Force-sub gate
        if not await check_force_sub(client, user_id):
            await send_force_sub_message(client, message)
            return

        if len(message.command) < 2:
            await message.reply_text(
                "⚠️ **No link provided!**\n\n"
                "**Usage:** `/dl <telegram_message_link>`\n"
                "**Example:** `/dl https://t.me/channel/123`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        url       = message.command[1]
        match     = re.match(r"(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?([a-zA-Z0-9_]+)/(\d+)", url)
        if not match:
            await message.reply_text(
                "❌ **Invalid link!**\n\nPlease send a valid Telegram message link.\n"
                "Example: `https://t.me/channelname/123`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        channel_username, message_id = match.groups()
        message_id = int(message_id)
        is_private = "c/" in url

        if is_private:
            await message.reply_text(
                "🔐 **Private Link Detected**\n\n"
                "This link is from a private channel. You need a **premium plan** and a "
                "logged-in account to download it.\n\n"
                "👉 Use `/plans` to upgrade, then `/login` to add your account.\n"
                "Then use `/pdl` instead of `/dl`.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 View Plans", callback_data="menu_plans")
                ]]),
            )
            return

        if not channel_username.startswith("@"):
            channel_username = f"@{channel_username}"

        is_premium = any(col.find_one({"user_id": user_id}) for col in (prem_plan1, prem_plan2, prem_plan3))

        processing_msg = await message.reply_text(
            "⏳ **Fetching your content…** Please wait a moment.",
            parse_mode=ParseMode.MARKDOWN,
        )
        await asyncio.sleep(0.1)

        # Verify channel
        try:
            chat = await client.get_chat(channel_username)
            if chat.type not in (ChatType.CHANNEL, ChatType.SUPERGROUP):
                await processing_msg.edit_text(
                    "❌ **Unsupported source.**\nThis bot only supports channels and supergroups.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
        except (ChannelInvalid, PeerIdInvalid):
            await processing_msg.edit_text(
                "❌ **Channel not found!**\nMake sure the channel is public and the link is correct.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        except ChannelPrivate:
            if not is_premium:
                await processing_msg.edit_text(
                    "🔐 **Private Channel**\n\nThis channel is private. "
                    "Upgrade to premium and use `/pdl` with a logged-in account.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💎 View Plans", callback_data="menu_plans")
                    ]]),
                )
                return
        except Exception as e:
            await processing_msg.edit_text(
                "❌ **Could not access the channel.** Please check the link and try again.",
                parse_mode=ParseMode.MARKDOWN,
            )
            LOGGER.error(f"Failed to fetch chat {channel_username}: {e}")
            return

        # Daily limit check (free users)
        if not is_premium:
            today      = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            user_limit = daily_limit.find_one({"user_id": user_id})
            downloads  = user_limit.get("downloads", 0) if user_limit and user_limit.get("date", datetime.min) >= today else 0
            if downloads >= 10:
                await processing_msg.edit_text(
                    "🚫 **Daily limit reached!**\n\n"
                    "Free users can download up to **10 files per day**.\n"
                    "Upgrade to premium for unlimited downloads!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💎 Upgrade Now", callback_data="menu_plans")
                    ]]),
                )
                return
            daily_limit.update_one(
                {"user_id": user_id},
                {"$set": {"downloads": downloads + 1, "date": today}, "$inc": {"total_downloads": 1}},
                upsert=True,
            )
            remaining = 10 - (downloads + 1)
        else:
            daily_limit.update_one({"user_id": user_id}, {"$inc": {"total_downloads": 1}}, upsert=True)
            remaining = None

        # Download & send
        try:
            source_msg = await client.get_messages(channel_username, message_id)
            if not source_msg:
                await processing_msg.edit_text(
                    "❌ **Message not found.** It may have been deleted.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            if source_msg.video:
                user_data         = user_activity_collection.find_one({"user_id": user_id})
                thumbnail_file_id = user_data.get("thumbnail_file_id") if user_data else None
                try:
                    if thumbnail_file_id:
                        try:
                            tp = await client.send_photo(chat_id=user_id, photo=thumbnail_file_id, caption="…")
                            await tp.delete()
                        except Exception:
                            thumbnail_file_id = None

                    await client.send_video(
                        chat_id=chat_id,
                        video=source_msg.video.file_id,
                        caption=source_msg.caption or "",
                        parse_mode=ParseMode.MARKDOWN if source_msg.caption else None,
                        thumb=thumbnail_file_id,
                    )
                except FileReferenceExpired:
                    await client.send_video(chat_id=chat_id, video=source_msg.video.file_id,
                                            caption=source_msg.caption or "")
                except Exception as e:
                    LOGGER.error(f"Video send error: {e}")
                    await client.send_video(chat_id=chat_id, video=source_msg.video.file_id,
                                            caption=source_msg.caption or "")
            else:
                await client.copy_message(chat_id=chat_id, from_chat_id=channel_username, message_id=message_id)

            # Success message
            if is_premium:
                done_text = (
                    "✅ **Done!** Your content has been delivered.\n\n"
                    "As a premium member you have **unlimited downloads**. Enjoy! 🚀"
                )
            else:
                done_text = (
                    f"✅ **Done!** Your content has been delivered.\n\n"
                    f"📊 You have **{remaining}/10** free downloads left today.\n"
                    f"💎 Upgrade to premium for unlimited access!"
                )

            await processing_msg.edit_text(
                done_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 Get Premium", callback_data="menu_plans")
                ]]) if not is_premium else None,
            )

        except Exception as e:
            await processing_msg.edit_text(
                f"❌ **Download failed.**\n\n`{str(e)}`\n\nPlease try again.",
                parse_mode=ParseMode.MARKDOWN,
            )
            LOGGER.error(f"dl_command error for user {user_id}: {e}")

    app.add_handler(
        MessageHandler(
            dl_command,
            filters=filters.command("dl", prefixes=COMMAND_PREFIX) & (filters.private | filters.group),
        ),
        group=1,
    )
