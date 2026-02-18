# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from pyrogram.enums import ParseMode
from utils.logging_setup import LOGGER
from utils.force_sub import check_force_sub, send_force_sub_message, force_sub_callback

# ─────────────────────────────────────────────────────────────────────────────
#  Text constants
# ─────────────────────────────────────────────────────────────────────────────

WELCOME_TEXT = """
✨ **Welcome, {name}!** ✨

I'm **RestrictedContentDL** — your all-in-one toolkit for downloading \
restricted Telegram content from public *and* private channels, groups, and \
supergroups.

━━━━━━━━━━━━━━━━━━━━━━
🚀 **What can I do?**
━━━━━━━━━━━━━━━━━━━━━━
📥 Download media from **public** restricted sources
🔐 Download media from **private** sources *(Premium)*
📦 **Batch download** hundreds of files at once *(Premium)*
🖼️ Apply your own custom **thumbnails** to videos
⭐ Flexible **premium plans** starting from just 150 Stars

━━━━━━━━━━━━━━━━━━━━━━
👇 **Tap a button below to get started!**
"""

HELP_TEXT = """
📚 **Help & Tutorial**

━━━━━━━━━━━━━━━━━━━━━━
**Step 1 — Copy a Telegram message link**

Open any Telegram channel or group, long-press a message and tap \
**"Copy Link"** (or use the share icon). You'll get a URL like:
  • `https://t.me/channelname/123`
  • `https://t.me/c/1234567890/456` *(private)*

━━━━━━━━━━━━━━━━━━━━━━
**Step 2 — Send the link to me**

Use one of these commands:
  • `/dl <link>` — single file from a **public** source
  • `/bdl <link>` — batch from a **public** source
  • `/pdl <link>` — single file from a **private** source 🔐
  • `/pbdl <link>` — batch from a **private** source 🔐

━━━━━━━━━━━━━━━━━━━━━━
**Step 3 — Enjoy your content!**

I'll download and forward the file straight to our chat. \
Premium users get faster speeds, higher limits, and private-source access.

━━━━━━━━━━━━━━━━━━━━━━
**🖼️ Custom Thumbnails (Optional)**

Reply to any photo and type `/setthumb` to set it as your default video \
thumbnail. Use `/rmthumb` to remove it and `/getthumb` to preview it.

━━━━━━━━━━━━━━━━━━━━━━
**🔐 Private Sources — How to log in**

1. Purchase a premium plan via `/plans`
2. Type `/login` and follow the prompts
3. Use `/pdl` or `/pbdl` with private links!

━━━━━━━━━━━━━━━━━━━━━━
💡 **Tip:** Commands also work with these prefixes: `!` `.` `#` `,` `/`
"""

PLANS_PREVIEW_TEXT = """
💎 **Premium Plans**

━━━━━━━━━━━━━━━━━━━━━━
🥈 **Plan 1 — 150 ⭐**
  • 1 account login
  • Up to 1 000 downloads / month
  • Public & private channel access ✅

🥇 **Plan 2 — 500 ⭐**
  • 5 account logins
  • Up to 2 000 downloads / month
  • Private inbox / bot access ✅

💎 **Plan 3 — 1 000 ⭐**
  • 10 account logins
  • **Unlimited** downloads
  • All features unlocked ✅

━━━━━━━━━━━━━━━━━━━━━━
Tap **Buy a Plan** to proceed with purchase.
"""

DOWNLOAD_GUIDE_TEXT = """
📥 **Download Guide**

━━━━━━━━━━━━━━━━━━━━━━
**Public Source (Free)**
• Copy the public message link
• Send: `/dl https://t.me/channel/123`

**Private Source (Premium)**
• Log in first with `/login`
• Send: `/pdl https://t.me/c/123456/789`

**Batch Download (up to 10 000 messages)**
• `/bdl <link>` — public batch
• `/pbdl <link>` — private batch

━━━━━━━━━━━━━━━━━━━━━━
⚠️ **Note:** Private downloads require an active premium plan and a \
logged-in user session.
"""

THUMBNAIL_GUIDE_TEXT = """
🖼️ **Custom Thumbnail Guide**

━━━━━━━━━━━━━━━━━━━━━━
Your custom thumbnail is applied automatically to every video you download!

**Set a thumbnail**
  1. Send any photo to me
  2. Reply to it with `/setthumb`
  3. Done — future downloads will use it ✅

**Remove your thumbnail**
  → `/rmthumb`

**Preview your current thumbnail**
  → `/getthumb`

━━━━━━━━━━━━━━━━━━━━━━
💡 Best results: use a **16:9** JPEG image (1280 × 720 px).
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Keyboard helpers
# ─────────────────────────────────────────────────────────────────────────────

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📥 Download Guide", callback_data="menu_download"),
            InlineKeyboardButton("💎 Premium Plans",  callback_data="menu_plans"),
        ],
        [
            InlineKeyboardButton("🖼️ Thumbnails",     callback_data="menu_thumb"),
            InlineKeyboardButton("📚 Help & Tutorial", callback_data="menu_help"),
        ],
        [
            InlineKeyboardButton("👤 My Profile",     callback_data="menu_profile"),
            InlineKeyboardButton("🔐 Login / Logout", callback_data="menu_login"),
        ],
        [
            InlineKeyboardButton("📢 Updates Channel", url="https://t.me/TheSmartDev"),
            InlineKeyboardButton("💻 Source Code",    url="https://github.com/TheSmartDevs/RestrictedContentDL"),
        ],
    ])


def back_keyboard(target: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data=target)],
    ])


def plans_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥈 Buy Plan 1 — 150 ⭐", callback_data="buy_plan1")],
        [InlineKeyboardButton("🥇 Buy Plan 2 — 500 ⭐", callback_data="buy_plan2")],
        [InlineKeyboardButton("💎 Buy Plan 3 — 1000 ⭐", callback_data="buy_plan3")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")],
    ])


def login_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Login to Account",   callback_data="do_login")],
        [InlineKeyboardButton("🚪 Logout from Account", callback_data="do_logout")],
        [InlineKeyboardButton("⬅️ Back to Menu",       callback_data="main_menu")],
    ])


# ─────────────────────────────────────────────────────────────────────────────
#  Handler setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_start_handler(app: Client):

    # ── /start ───────────────────────────────────────────────────────────────
    @app.on_message(filters.command("start") & filters.private)
    async def start(client: Client, message: Message):
        user = message.from_user
        name = user.first_name or "there"
        user_id = user.id

        LOGGER.info(f"Start command from user {user_id}")

        # Force-subscribe gate
        if not await check_force_sub(client, user_id):
            await send_force_sub_message(client, message)
            return

        await message.reply_text(
            WELCOME_TEXT.format(name=name),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(),
            disable_web_page_preview=True,
        )

    # ── /help ────────────────────────────────────────────────────────────────
    @app.on_message(filters.command("help") & filters.private)
    async def help_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        if not await check_force_sub(client, user_id):
            await send_force_sub_message(client, message)
            return

        await message.reply_text(
            HELP_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard(),
        )

    # ── "Check Again" callback (force-sub) ───────────────────────────────────
    @app.on_callback_query(filters.regex("^check_sub$"))
    async def check_sub_callback(client: Client, callback_query: CallbackQuery):
        verified = await force_sub_callback(client, callback_query)
        if verified:
            user = callback_query.from_user
            name = user.first_name or "there"
            await client.send_message(
                chat_id=callback_query.message.chat.id,
                text=WELCOME_TEXT.format(name=name),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard(),
                disable_web_page_preview=True,
            )

    # ── Main menu callbacks ───────────────────────────────────────────────────
    @app.on_callback_query(filters.regex("^main_menu$"))
    async def cb_main_menu(client: Client, callback_query: CallbackQuery):
        user = callback_query.from_user
        name = user.first_name or "there"
        await callback_query.message.edit_text(
            WELCOME_TEXT.format(name=name),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(),
            disable_web_page_preview=True,
        )
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^menu_download$"))
    async def cb_download(client: Client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            DOWNLOAD_GUIDE_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard(),
        )
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^menu_plans$"))
    async def cb_plans(client: Client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            PLANS_PREVIEW_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=plans_keyboard(),
        )
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^menu_thumb$"))
    async def cb_thumb(client: Client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            THUMBNAIL_GUIDE_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard(),
        )
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^menu_help$"))
    async def cb_help(client: Client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            HELP_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard(),
        )
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^menu_profile$"))
    async def cb_profile(client: Client, callback_query: CallbackQuery):
        # Trigger the info/profile command response inline
        from core.profile_helper import get_profile_text
        text = await get_profile_text(callback_query.from_user.id)
        await callback_query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^menu_login$"))
    async def cb_login(client: Client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            "🔐 **Login / Logout Manager**\n\n"
            "Use the buttons below to manage your Telegram account sessions.\n\n"
            "• **Login** — Add a Telegram account for private downloads\n"
            "• **Logout** — Remove a saved session\n\n"
            "_Your session is stored securely and only used for downloading._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=login_keyboard(),
        )
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^do_login$"))
    async def cb_do_login(client: Client, callback_query: CallbackQuery):
        await callback_query.answer()
        await callback_query.message.delete()
        # Fake a /login message so the login handler picks it up
        await client.send_message(
            chat_id=callback_query.message.chat.id,
            text="Please use the /login command to start the login process.",
            parse_mode=ParseMode.MARKDOWN,
        )

    @app.on_callback_query(filters.regex("^do_logout$"))
    async def cb_do_logout(client: Client, callback_query: CallbackQuery):
        await callback_query.answer()
        await callback_query.message.delete()
        await client.send_message(
            chat_id=callback_query.message.chat.id,
            text="Please use the /logout command to log out of a saved session.",
            parse_mode=ParseMode.MARKDOWN,
        )
