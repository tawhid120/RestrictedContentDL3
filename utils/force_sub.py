# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
# Force Subscribe Middleware

from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, ChannelPrivate, PeerIdInvalid
from utils.logging_setup import LOGGER

# ─── Force Subscribe Channel ───────────────────────────────────────────────────
FORCE_SUB_CHANNEL = "@juktijol"   # Change this if needed
# ───────────────────────────────────────────────────────────────────────────────

FORCE_SUB_MESSAGE = """
╔══════════════════════════╗
║   🔐  Access Restricted   ║
╚══════════════════════════╝

Hey {name}! 👋

To use this bot, you **must join** our official channel first.

📢 **Why?**
We share important updates, tips, and announcements there. It takes just one tap!

👇 **Click the button below to join:**
"""


async def check_force_sub(client: Client, user_id: int) -> bool:
    """
    Returns True if the user is subscribed to FORCE_SUB_CHANNEL, False otherwise.
    """
    try:
        member = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        # Allow all statuses except banned/kicked
        from pyrogram.enums import ChatMemberStatus
        if member.status in (
            ChatMemberStatus.BANNED,
            ChatMemberStatus.LEFT,
            ChatMemberStatus.RESTRICTED,
        ):
            return False
        return True
    except UserNotParticipant:
        return False
    except (ChatAdminRequired, ChannelPrivate, PeerIdInvalid):
        # If bot can't check (not admin or channel inaccessible), allow user through
        LOGGER.warning(f"Could not verify force-sub for user {user_id}. Allowing through.")
        return True
    except Exception as e:
        LOGGER.error(f"Force sub check error for user {user_id}: {e}")
        return True   # Fail open so bot stays usable if channel check breaks


async def send_force_sub_message(client: Client, message: Message) -> None:
    """
    Sends the force-subscribe prompt to the user.
    """
    user = message.from_user
    name = user.first_name or "there"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton("✅ I've Joined – Check Again", callback_data="check_sub")],
    ])

    await message.reply_text(
        FORCE_SUB_MESSAGE.format(name=name),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


async def force_sub_callback(client: Client, callback_query: CallbackQuery) -> bool:
    """
    Handles the 'Check Again' callback. Returns True if now subscribed.
    """
    user_id = callback_query.from_user.id
    is_subbed = await check_force_sub(client, user_id)

    if is_subbed:
        await callback_query.message.delete()
        await callback_query.answer("✅ Verified! You're all set.", show_alert=False)
        return True
    else:
        await callback_query.answer(
            "❌ You haven't joined yet! Please join the channel first.",
            show_alert=True,
        )
        return False
