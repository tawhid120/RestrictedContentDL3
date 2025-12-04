# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode, ChatType
from pyrogram.handlers import MessageHandler
from pyrogram.errors import ChannelInvalid, ChannelPrivate, PeerIdInvalid, FileReferenceExpired
from config import COMMAND_PREFIX
from utils import LOGGER
from core import daily_limit, prem_plan1, prem_plan2, prem_plan3, user_activity_collection
from datetime import datetime, timedelta
import re
import asyncio

def setup_public_handler(app: Client):
    async def dl_command(client: Client, message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        # লজিক ১: ইউজার কি কমান্ড (/dl) দিয়েছে নাকি সরাসরি লিংক দিয়েছে?
        url = ""
        
        # যদি কমান্ড (/dl) ব্যবহার করা হয়
        if getattr(message, "command", None):
            if len(message.command) < 2:
                await message.reply_text(
                    "**Please provide a valid URL! Usage: /dl {url}**",
                    parse_mode=ParseMode.MARKDOWN
                )
                LOGGER.warning(f"No URL provided in /dl command by user {user_id}")
                return
            url = message.command[1]
        
        # যদি সরাসরি লিংক (Text) দেওয়া হয়
        else:
            url = message.text.strip()

        # Handle t.me and telegram.me URLs, including private links (t.me/c/)
        match = re.match(r"(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?([a-zA-Z0-9_]+)/(\d+)", url)
        if not match:
            # যদি লিংক ভ্যালিড না হয় এবং ইউজার সরাসরি টেক্সট দিয়ে থাকে, তাহলে আমরা সাইলেন্ট থাকতে পারি বা এরর দিতে পারি।
            # তবে ইউজার যেহেতু এক্সপেক্ট করছে লিংক দিলে কাজ হবে, তাই এরর দেওয়া ভালো।
            await message.reply_text(
                "**Invalid URL! Please use a valid Telegram message link**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.warning(f"Invalid URL format: {url} by user {user_id}")
            return

        channel_username, message_id = match.groups()
        message_id = int(message_id)
        is_private = "c/" in url

        # Check if it's a private link
        if is_private:
            await message.reply_text(
                "**Private links require a premium plan and login! Use /login and upgrade: /plans**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.warning(f"Private link {url} attempted by user {user_id} without login")
            return

        # Handle public links
        if not channel_username.startswith("@"):
            channel_username = f"@{channel_username}"

        # Check if user has a premium plan
        is_premium = (
            prem_plan1.find_one({"user_id": user_id}) or
            prem_plan2.find_one({"user_id": user_id}) or
            prem_plan3.find_one({"user_id": user_id})
        )

        # Send processing message
        processing_msg = await message.reply_text(
            "**Downloading restricted media ⏳**",
            parse_mode=ParseMode.MARKDOWN
        )
        await asyncio.sleep(0.1)  # Small delay to prevent rate-limiting

        # Check channel accessibility
        try:
            chat = await client.get_chat(channel_username)
            if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
                await client.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.id,
                    text="**This command only supports channels or supergroups!**",
                    parse_mode=ParseMode.MARKDOWN
                )
                LOGGER.error(f"Invalid chat type for {channel_username}: {chat.type}")
                return

        except (ChannelInvalid, PeerIdInvalid):
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.id,
                text="**Invalid channel or group! Ensure it's public and accessible.**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"Invalid channel or group: {channel_username}")
            return
        except ChannelPrivate:
            if not is_premium:
                await client.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.id,
                    text="**This channel is private! Upgrade to premium and use /login: /plans**",
                    parse_mode=ParseMode.MARKDOWN
                )
                LOGGER.error(f"Private channel {channel_username} attempted by free user {user_id}")
                return
        except Exception as e:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.id,
                text="**Error accessing the channel! Ensure the link is correct and the channel is accessible.**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"Failed to fetch chat {channel_username}: {e}")
            return

        # Check daily limit for free users
        if not is_premium:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            user_limit = daily_limit.find_one({"user_id": user_id})
            if user_limit and user_limit.get("date") >= today:
                downloads = user_limit.get("downloads", 0)
                if downloads >= 10:
                    await client.edit_message_text(
                        chat_id=chat_id,
                        message_id=processing_msg.id,
                        text="**Daily limit of 10 downloads reached! Upgrade to premium for more: /plans**",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    LOGGER.info(f"Daily limit reached for user {user_id}")
                    return
                daily_limit.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {"downloads": downloads + 1, "date": today},
                        "$inc": {"total_downloads": 1}
                    },
                    upsert=True
                )
            else:
                daily_limit.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {"downloads": 1, "date": today},
                        "$inc": {"total_downloads": 1}
                    },
                    upsert=True
                )
            remaining = 10 - (user_limit.get("downloads", 0) + 1 if user_limit else 1)
        else:
            daily_limit.update_one(
                {"user_id": user_id},
                {"$inc": {"total_downloads": 1}},
                upsert=True
            )
            remaining = None  # No limit for premium users

        # Fetch and copy the message
        try:
            source_message = await client.get_messages(channel_username, message_id)
            if not source_message:
                await client.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.id,
                    text="Message not found or deleted!",
                    parse_mode=ParseMode.MARKDOWN
                )
                LOGGER.error(f"Message {message_id} not found in {channel_username}")
                return

            # Check if the message contains a video
            if source_message.video:
                user_data = user_activity_collection.find_one({"user_id": user_id})
                thumbnail_file_id = user_data.get("thumbnail_file_id") if user_data else None
                try:
                    if thumbnail_file_id:
                        # Validate thumbnail by sending it as a photo
                        try:
                            test_photo = await client.send_photo(
                                chat_id=user_id,
                                photo=thumbnail_file_id,
                                caption="Validating thumbnail...",
                                parse_mode=ParseMode.MARKDOWN
                            )
                            await test_photo.delete()  # Clean up test message
                        except Exception as e:
                            thumbnail_file_id = None
                            LOGGER.warning(f"Invalid thumbnail file_id for user {user_id}: {e}")
                            await message.reply_text(
                                "**Invalid or expired thumbnail! Please set a new one with /setthumb.**",
                                parse_mode=ParseMode.MARKDOWN
                            )

                    await client.send_video(
                        chat_id=chat_id,
                        video=source_message.video.file_id,
                        caption=source_message.caption or "",
                        parse_mode=ParseMode.MARKDOWN if source_message.caption else None,
                        thumb=thumbnail_file_id if thumbnail_file_id else None
                    )
                    LOGGER.info(f"Sent video with {'custom' if thumbnail_file_id else 'default'} thumbnail for user {user_id}")
                except FileReferenceExpired:
                    LOGGER.error(f"Thumbnail file reference expired for user {user_id}")
                    await client.send_video(
                        chat_id=chat_id,
                        video=source_message.video.file_id,
                        caption=source_message.caption or "",
                        parse_mode=ParseMode.MARKDOWN if source_message.caption else None
                    )
                    await message.reply_text(
                        "Custom thumbnail expired! Please set a new one with /setthumb.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    LOGGER.info(f"Sent video with default thumbnail for user {user_id} due to expired thumbnail")
                except Exception as e:
                    LOGGER.error(f"Failed to send video with thumbnail for user {user_id}: {e}")
                    await client.send_video(
                        chat_id=chat_id,
                        video=source_message.video.file_id,
                        caption=source_message.caption or "",
                        parse_mode=ParseMode.MARKDOWN if source_message.caption else None
                    )
                    await message.reply_text(
                        "Error applying thumbnail! Using default thumbnail.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    LOGGER.info(f"Sent video with default thumbnail for user {user_id} due to error")
            else:
                # Copy non-video messages directly
                await client.copy_message(
                    chat_id=chat_id,
                    from_chat_id=channel_username,
                    message_id=message_id
                )

            reminder_text = (
                f"**Congratulations 🎉 You have received the content ✅**\n\n"
                f"**Download from private channel/group in premium plan, check /plans 😍**\n\n"
                f"**Daily limit left: {remaining}/10**"
            ) if not is_premium else (
                "**Congratulations 🎉 You have received the content ✅**\n\n"
                "**As a premium user, enjoy unlimited downloads!**"
            )
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.id,
                text=reminder_text,
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.info(f"Successfully copied message {message_id} from {channel_username} for user {user_id}")

        except ChannelInvalid:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.id,
                text="Invalid channel or group! Ensure it's public and accessible.",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"Invalid channel: {channel_username}")
        except ChannelPrivate:
            if not is_premium:
                await client.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.id,
                    text="This channel is private! Upgrade to premium and use /login: /plans",
                    parse_mode=ParseMode.MARKDOWN
                )
                LOGGER.error(f"Private channel {channel_username} attempted by free user {user_id}")
        except PeerIdInvalid:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.id,
                text="Invalid chat ID! Please check the URL and try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"Invalid chat ID: {channel_username}")
        except Exception as e:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.id,
                text=f"Error copying the message: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.error(f"Failed to copy message {message_id} from {channel_username}: {e}")

    # ১. পুরাতন কমান্ড হ্যান্ডলার (/dl)
    app.add_handler(
        MessageHandler(
            dl_command,
            filters=filters.command("dl", prefixes=COMMAND_PREFIX) & (filters.private | filters.group)
        ),
        group=1
    )

    # ২. নতুন লজিক: সরাসরি টেলিগ্রাম লিংক হ্যান্ডলার
    # এটি যেকোনো t.me বা telegram.me লিংক ডিটেক্ট করবে
    app.add_handler(
        MessageHandler(
            dl_command,
            filters=filters.regex(r"(?:https?://)?(?:t\.me|telegram\.me)/") & (filters.private | filters.group)
        ),
        group=1
    )
