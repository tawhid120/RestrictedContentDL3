# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from config import COMMAND_PREFIX
from utils.logging_setup import LOGGER
from utils.force_sub import check_force_sub, send_force_sub_message
from core import user_activity_collection


def setup_thumb_handler(app: Client):

    async def setthumb_command(client: Client, message: Message):
        user_id = message.from_user.id
        if not await check_force_sub(client, user_id):
            await send_force_sub_message(client, message)
            return

        if not message.reply_to_message or not message.reply_to_message.photo:
            await message.reply_text(
                "📸 **How to set a thumbnail:**\n\n"
                "1. Send any photo to this chat\n"
                "2. Reply to that photo with `/setthumb`\n\n"
                "💡 Best results: **1280 × 720 px** JPEG image (16:9 ratio).",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        photo = message.reply_to_message.photo
        os.makedirs("Assets", exist_ok=True)
        thumb_path = f"Assets/{user_id}_thumb.jpg"
        try:
            await client.download_media(photo.file_id, file_name=thumb_path)
            user_activity_collection.update_one(
                {"user_id": user_id},
                {"$set": {"thumbnail_path": thumb_path}},
                upsert=True,
            )
            await message.reply_text(
                "✅ **Thumbnail saved!**\n\n"
                "Your custom thumbnail will now be applied to all future video downloads.\n"
                "Use `/rmthumb` to remove it or `/getthumb` to preview it.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👁️ Preview Thumbnail", callback_data="noop_preview_thumb")
                ]]),
            )
            LOGGER.info(f"Thumbnail set for user {user_id}")
        except Exception as e:
            await message.reply_text(
                "❌ **Failed to save thumbnail.** Please try again.",
                parse_mode=ParseMode.MARKDOWN,
            )
            LOGGER.error(f"setthumb error for user {user_id}: {e}")

    async def rmthumb_command(client: Client, message: Message):
        user_id   = message.from_user.id
        user_data = user_activity_collection.find_one({"user_id": user_id})

        if not user_data or "thumbnail_path" not in user_data:
            await message.reply_text(
                "⚠️ **You don't have a custom thumbnail set.**\n\n"
                "Use `/setthumb` (reply to a photo) to set one.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        thumb_path = user_data["thumbnail_path"]
        try:
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            user_activity_collection.update_one({"user_id": user_id}, {"$unset": {"thumbnail_path": ""}})
            await message.reply_text(
                "🗑️ **Thumbnail removed.**\n\nYour downloads will now use the default thumbnail.",
                parse_mode=ParseMode.MARKDOWN,
            )
            LOGGER.info(f"Thumbnail removed for user {user_id}")
        except Exception as e:
            await message.reply_text("❌ **Failed to remove thumbnail.** Please try again.",
                                     parse_mode=ParseMode.MARKDOWN)
            LOGGER.error(f"rmthumb error for user {user_id}: {e}")

    async def getthumb_command(client: Client, message: Message):
        user_id   = message.from_user.id
        user_data = user_activity_collection.find_one({"user_id": user_id})

        if not user_data or "thumbnail_path" not in user_data:
            await message.reply_text(
                "⚠️ **No thumbnail set yet.**\n\n"
                "Reply to any photo with `/setthumb` to set your custom video thumbnail.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        thumb_path = user_data["thumbnail_path"]
        if os.path.exists(thumb_path):
            try:
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=thumb_path,
                    caption=(
                        "🖼️ **Your current thumbnail**\n\n"
                        "This image is applied to all your video downloads.\n"
                        "Use `/rmthumb` to remove it."
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as e:
                await message.reply_text("❌ **Error retrieving thumbnail.**", parse_mode=ParseMode.MARKDOWN)
                LOGGER.error(f"getthumb error for user {user_id}: {e}")
        else:
            user_activity_collection.update_one({"user_id": user_id}, {"$unset": {"thumbnail_path": ""}})
            await message.reply_text(
                "⚠️ **Thumbnail file is missing.**\n\nPlease set a new one with `/setthumb`.",
                parse_mode=ParseMode.MARKDOWN,
            )

    for cmd, fn in [("setthumb", setthumb_command), ("rmthumb", rmthumb_command), ("getthumb", getthumb_command)]:
        app.add_handler(
            MessageHandler(fn, filters=filters.command(cmd, prefixes=COMMAND_PREFIX)
                           & (filters.private | filters.group)),
            group=1,
        )
