# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import ChatWriteForbidden, UserIsBlocked, InputUserDeactivated, FloodWait
from datetime import datetime, timedelta
import asyncio
from config import COMMAND_PREFIX, DEVELOPER_USER_ID
from utils.logging_setup import LOGGER
from core import total_users


def setup_sudo_handler(app: Client):

    async def update_user_activity(user_id: int):
        total_users.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "last_active": datetime.utcnow()}},
            upsert=True,
        )

    async def get_active_users():
        now = datetime.utcnow()
        return (
            total_users.count_documents({"last_active": {"$gte": now - timedelta(days=1)}}),
            total_users.count_documents({"last_active": {"$gte": now - timedelta(days=7)}}),
            total_users.count_documents({"last_active": {"$gte": now - timedelta(days=30)}}),
            total_users.count_documents({"last_active": {"$gte": now - timedelta(days=365)}}),
            total_users.count_documents({}),
        )

    @app.on_message(filters.command("stats", prefixes=COMMAND_PREFIX) & filters.private)
    async def stats_command(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id != DEVELOPER_USER_ID:
            return
        await update_user_activity(user_id)
        daily, weekly, monthly, annual, total = await get_active_users()
        await message.reply_text(
            "📊 **Bot Statistics**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 **Daily active:** `{daily}`\n"
            f"📅 **Weekly active:** `{weekly}`\n"
            f"🗓️ **Monthly active:** `{monthly}`\n"
            f"📆 **Annual active:** `{annual}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 **Total users:** `{total}`",
            parse_mode=ParseMode.MARKDOWN,
        )

    @app.on_message(filters.command("gcast", prefixes=COMMAND_PREFIX) & filters.private)
    async def gcast_command(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id != DEVELOPER_USER_ID:
            return
        await update_user_activity(user_id)
        if not message.reply_to_message:
            await message.reply_text("❌ **Reply to a message to broadcast it.**", parse_mode=ParseMode.MARKDOWN)
            return

        bm = message.reply_to_message
        start = datetime.utcnow()
        success = blocked = failed = deactivated = floods = 0
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Updates", url="https://t.me/TheSmartDev")]])
        ids = [u["user_id"] for u in total_users.find({}, {"user_id": 1})]

        for uid in ids:
            while True:
                try:
                    sent = await client.copy_message(uid, user_id, bm.id, reply_markup=buttons)
                    try: await client.pin_chat_message(uid, sent.id, both_sides=True)
                    except: pass
                    success += 1
                    await asyncio.sleep(0.5)
                    break
                except FloodWait as e:
                    floods += 1
                    await asyncio.sleep(e.value + 5)
                except UserIsBlocked:      blocked += 1;     break
                except InputUserDeactivated: deactivated += 1; break
                except Exception:          failed += 1;      break

        elapsed = int((datetime.utcnow() - start).total_seconds())
        await client.send_message(
            user_id,
            f"📢 **Broadcast Complete**\n━━━━━━━━━━━━\n"
            f"✅ Sent: `{success}` | ❌ Failed: `{failed}`\n"
            f"🚫 Blocked: `{blocked}` | 💤 Deactivated: `{deactivated}`\n"
            f"⚡ Flood waits: `{floods}` | ⏱ Time: `{elapsed}s`",
            parse_mode=ParseMode.MARKDOWN,
        )

    @app.on_message(filters.command("acast", prefixes=COMMAND_PREFIX) & filters.private)
    async def acast_command(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id != DEVELOPER_USER_ID:
            return
        await update_user_activity(user_id)
        if not message.reply_to_message:
            await message.reply_text("❌ **Reply to a message to broadcast it.**", parse_mode=ParseMode.MARKDOWN)
            return

        bm = message.reply_to_message
        start = datetime.utcnow()
        success = blocked = failed = deactivated = floods = 0
        ids = [u["user_id"] for u in total_users.find({}, {"user_id": 1})]

        for uid in ids:
            while True:
                try:
                    sent = await client.forward_messages(uid, user_id, bm.id)
                    try: await client.pin_chat_message(uid, sent.id, both_sides=True)
                    except: pass
                    success += 1
                    await asyncio.sleep(0.5)
                    break
                except FloodWait as e:
                    floods += 1
                    await asyncio.sleep(e.value + 5)
                except UserIsBlocked:      blocked += 1;     break
                except InputUserDeactivated: deactivated += 1; break
                except Exception:          failed += 1;      break

        elapsed = int((datetime.utcnow() - start).total_seconds())
        await client.send_message(
            user_id,
            f"📢 **Forward Broadcast Complete**\n━━━━━━━━━━━━\n"
            f"✅ Sent: `{success}` | ❌ Failed: `{failed}`\n"
            f"🚫 Blocked: `{blocked}` | 💤 Deactivated: `{deactivated}`\n"
            f"⚡ Flood waits: `{floods}` | ⏱ Time: `{elapsed}s`",
            parse_mode=ParseMode.MARKDOWN,
        )
