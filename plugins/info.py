# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from config import COMMAND_PREFIX
from utils.logging_setup import LOGGER
from utils.force_sub import check_force_sub, send_force_sub_message
from core import prem_plan1, prem_plan2, prem_plan3, user_sessions, daily_limit
from core.profile_helper import get_profile_text


def setup_info_handler(app: Client):

    async def info_command(client: Client, message: Message):
        user_id = message.from_user.id
        user    = message.from_user

        if not await check_force_sub(client, user_id):
            await send_force_sub_message(client, message)
            return

        text = await get_profile_text(user_id)

        # Enrich with name / username (not in the helper since helper has no User object)
        full_name = f"{user.first_name} {getattr(user, 'last_name', '') or ''}".strip() or "Unknown"
        username  = f"@{user.username}" if user.username else "—"

        text = (
            "<b>👤 Your Profile</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>🆔 User ID:</b>   <code>{user_id}</code>\n"
            f"<b>📛 Name:</b>     <code>{full_name}</code>\n"
            f"<b>🔖 Username:</b> <code>{username}</code>\n"
        ) + "\n".join(text.splitlines()[2:])   # skip the duplicate header lines

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Upgrade Plan", callback_data="menu_plans")],
            [InlineKeyboardButton("🏠 Main Menu",    callback_data="main_menu")],
        ])

        await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        LOGGER.info(f"Info command by user {user_id}")

    async def help_command(client: Client, message: Message):
        user_id = message.from_user.id

        if not await check_force_sub(client, user_id):
            await send_force_sub_message(client, message)
            return

        from core.start import HELP_TEXT, back_keyboard
        await message.reply_text(
            HELP_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard(),
        )
        LOGGER.info(f"Help command by user {user_id}")

    app.add_handler(
        MessageHandler(
            info_command,
            filters=filters.command(["info", "profile"], prefixes=COMMAND_PREFIX)
                    & (filters.private | filters.group),
        ),
        group=1,
    )
    app.add_handler(
        MessageHandler(
            help_command,
            filters=filters.command("help", prefixes=COMMAND_PREFIX)
                    & (filters.private | filters.group),
        ),
        group=1,
    )
