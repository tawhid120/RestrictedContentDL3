# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from utils.logging_setup import LOGGER

# Callbacks handled here are the legacy ones that may arrive from old messages.
# New menu callbacks are all handled inside core/start.py.
# This file is intentionally kept thin — it just re-exports the single entry
# point that main.py wires up.

async def handle_callback_query(client: Client, callback_query: CallbackQuery):
    """
    Catch-all for callback queries not claimed by a more specific handler.
    Most callbacks are now handled in core/start.py and plugins/plan.py.
    """
    data = callback_query.data or ""
    LOGGER.debug(f"Unhandled callback '{data}' from user {callback_query.from_user.id}")
    # Silently acknowledge to avoid the Telegram "loading" spinner
    await callback_query.answer()
