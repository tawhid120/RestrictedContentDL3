# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
import os, shutil, asyncio, subprocess
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from config import DEVELOPER_USER_ID, COMMAND_PREFIX
from utils.logging_setup import LOGGER


def _floodwait(coro):
    """Tiny helper: run coro, retry once on FloodWait."""
    async def wrapper(*args, **kwargs):
        try:
            return await coro(*args, **kwargs)
        except FloodWait as e:
            LOGGER.warning(f"FloodWait {e.value}s")
            await asyncio.sleep(e.value + 5)
            return await coro(*args, **kwargs)
    return wrapper


def setup_restart_handler(app: Client):

    @app.on_message(
        filters.command(["restart", "reboot", "reload"], prefixes=COMMAND_PREFIX)
        & (filters.private | filters.group)
    )
    async def restart(client: Client, message):
        user_id = message.from_user.id
        resp = await client.send_message(
            message.chat.id,
            "🔄 **Restarting…**",
            parse_mode=ParseMode.MARKDOWN,
        )

        if user_id != DEVELOPER_USER_ID:
            await client.edit_message_text(
                message.chat.id, resp.id,
                "🔒 **Access Denied**\n\nOnly the bot owner can restart the bot.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 Updates", url="https://t.me/TheSmartDevs"),
                ]]),
            )
            return

        # Clean temp files
        for d in ("downloads", "Assets"):
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)
        if os.path.exists("botlog.txt"):
            try: os.remove("botlog.txt")
            except: pass

        if not os.path.exists("start.sh"):
            await client.edit_message_text(
                message.chat.id, resp.id,
                "❌ **Restart failed** — `start.sh` not found.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        await asyncio.sleep(3)
        await client.edit_message_text(
            message.chat.id, resp.id,
            "✅ **Restarted successfully!**\n\nThe bot will be back online in a few seconds.",
            parse_mode=ParseMode.MARKDOWN,
        )

        try:
            subprocess.run(["bash", "start.sh"], check=True)
            os._exit(0)
        except Exception as e:
            LOGGER.error(f"Restart failed: {e}")
            await client.edit_message_text(
                message.chat.id, resp.id,
                "❌ **Restart failed.** Please restart manually.",
                parse_mode=ParseMode.MARKDOWN,
            )

    @app.on_message(
        filters.command(["stop", "kill", "off"], prefixes=COMMAND_PREFIX)
        & (filters.private | filters.group)
    )
    async def stop(client: Client, message):
        user_id = message.from_user.id
        resp = await client.send_message(
            message.chat.id, "🛑 **Stopping…**", parse_mode=ParseMode.MARKDOWN
        )

        if user_id != DEVELOPER_USER_ID:
            await client.edit_message_text(
                message.chat.id, resp.id,
                "🔒 **Access Denied** — Only the bot owner can stop the bot.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        for d in ("downloads", "Assets"):
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)

        await client.edit_message_text(
            message.chat.id, resp.id,
            "✅ **Bot stopped.** Goodbye! 👋",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            subprocess.run(["pkill", "-f", "main.py"], check=True)
            os._exit(0)
        except Exception as e:
            LOGGER.error(f"Stop failed: {e}")
