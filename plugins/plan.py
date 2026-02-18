# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
import uuid, hashlib, time
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from pyrogram.raw.functions.messages import SendMedia, SetBotPrecheckoutResults
from pyrogram.raw.types import (
    InputMediaInvoice, Invoice, DataJSON, LabeledPrice,
    UpdateBotPrecheckoutQuery, UpdateNewMessage, MessageService,
    MessageActionPaymentSentMe, PeerUser, PeerChat, PeerChannel,
    ReplyInlineMarkup, KeyboardButtonRow, KeyboardButtonBuy,
)
from pyrogram.handlers import MessageHandler, CallbackQueryHandler, RawUpdateHandler
from pyrogram.enums import ParseMode
from pyrogram.errors import UserIdInvalid, UsernameInvalid, PeerIdInvalid
from config import COMMAND_PREFIX, DEVELOPER_USER_ID
from utils.logging_setup import LOGGER
from utils.force_sub import check_force_sub, send_force_sub_message
from core import prem_plan1, prem_plan2, prem_plan3, daily_limit

# ─── Plan definitions ──────────────────────────────────────────────────────────
PLANS = {
    "plan1": {"stars": 150,  "name": "Plan Premium 1", "accounts": 1,  "max_downloads": 1000,       "private_support": True, "inbox_support": False},
    "plan2": {"stars": 500,  "name": "Plan Premium 2", "accounts": 5,  "max_downloads": 2000,       "private_support": True, "inbox_support": True},
    "plan3": {"stars": 1000, "name": "Plan Premium 3", "accounts": 10, "max_downloads": "unlimited","private_support": True, "inbox_support": True},
}

active_invoices: dict = {}

# ─────────────────────────────────────────────────────────────────────────────

PLAN_OPTIONS_TEXT = """
💎 **Choose Your Premium Plan**

━━━━━━━━━━━━━━━━━━━━━━
🥈 **Plan 1 — 150 ⭐**
  • 1 account login
  • 1 000 downloads / month
  • Private channel/group access ✅
  • Private inbox/bot access ❌

🥇 **Plan 2 — 500 ⭐**
  • 5 account logins
  • 2 000 downloads / month
  • Private channel/group access ✅
  • Private inbox/bot access ✅

💎 **Plan 3 — 1 000 ⭐**
  • 10 account logins
  • **Unlimited** downloads
  • All private sources ✅
  • Priority support ✅

━━━━━━━━━━━━━━━━━━━━━━
👇 Select a plan to generate your invoice:
"""

PAYMENT_SUCCESS_TEXT = """
🎉 **Payment Successful!**

━━━━━━━━━━━━━━━━━━━━━━
Thank you, **{name}**! Your purchase is confirmed.

  • **Plan:** {plan}
  • **Amount paid:** {amount} ⭐
  • **Valid for:** 30 days
  • **Transaction ID:** `{txn_id}`

━━━━━━━━━━━━━━━━━━━━━━
You can now use `/login` to add a Telegram account and \
start downloading private content. Enjoy! 🚀
"""

ADMIN_NOTIFICATION_TEXT = """
🛒 **New Purchase!**

  • **User:** {name}
  • **ID:** `{uid}`
  • **Username:** {uname}
  • **Plan:** {plan}
  • **Stars:** {amount}
  • **Txn ID:** `{txn_id}`
"""


def get_plan_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥈 Plan 1 — 150 ⭐",  callback_data="buy_plan1"),
         InlineKeyboardButton("🥇 Plan 2 — 500 ⭐",  callback_data="buy_plan2")],
        [InlineKeyboardButton("💎 Plan 3 — 1000 ⭐", callback_data="buy_plan3")],
        [InlineKeyboardButton("⬅️ Back to Menu",     callback_data="main_menu")],
    ])


def setup_plan_handler(app: Client):

    async def generate_invoice(client: Client, chat_id: int, user_id: int, plan_key: str):
        if active_invoices.get(user_id):
            await client.send_message(
                chat_id,
                "⏳ **A purchase is already in progress.** Please complete or cancel it first.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        plan   = PLANS[plan_key]
        amount = plan["stars"]

        loading_msg = await client.send_message(
            chat_id,
            f"⏳ **Generating your invoice for {amount} ⭐ — please wait…**",
            parse_mode=ParseMode.MARKDOWN,
        )
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="show_plan_options")]])

        try:
            active_invoices[user_id] = True
            ts       = int(time.time())
            uid8     = str(uuid.uuid4())[:8]
            payload  = f"plan_{plan_key}_{user_id}_{amount}_{ts}_{uid8}"
            rand_id  = int(hashlib.sha256(payload.encode()).hexdigest(), 16) % (2**63)

            invoice = Invoice(
                currency="XTR",
                prices=[LabeledPrice(label=f"⭐ {amount} Stars", amount=amount)],
                max_tip_amount=0,
                suggested_tip_amounts=[],
                recurring=False, test=False,
                name_requested=False, phone_requested=False,
                email_requested=False, shipping_address_requested=False,
                flexible=False,
            )
            media = InputMediaInvoice(
                title=f"Purchase {plan['name']}",
                description=(
                    f"Unlock {plan['name']}: {plan['accounts']} account(s), "
                    f"{plan['max_downloads']} downloads, private access."
                ),
                invoice=invoice,
                payload=payload.encode(),
                provider="STARS",
                provider_data=DataJSON(data="{}"),
            )
            markup = ReplyInlineMarkup(rows=[
                KeyboardButtonRow(buttons=[KeyboardButtonBuy(text=f"Pay {amount} ⭐")])
            ])
            peer = await client.resolve_peer(chat_id)
            await client.invoke(SendMedia(peer=peer, media=media, message="", random_id=rand_id, reply_markup=markup))
            await client.edit_message_text(
                chat_id, loading_msg.id,
                f"✅ **Invoice ready!** Tap the button above to pay **{amount} ⭐**.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_btn,
            )
            LOGGER.info(f"Invoice sent for {plan['name']} to user {user_id}")
        except Exception as e:
            LOGGER.error(f"Invoice generation failed for user {user_id}: {e}")
            await client.edit_message_text(
                chat_id, loading_msg.id,
                "❌ **Failed to generate invoice.** Please try again in a moment.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_btn,
            )
        finally:
            active_invoices.pop(user_id, None)

    # ── /plans & /buy ─────────────────────────────────────────────────────────
    async def plans_command(client: Client, message: Message):
        user_id = message.from_user.id
        if not await check_force_sub(client, user_id):
            await send_force_sub_message(client, message)
            return
        await client.send_message(
            message.chat.id,
            PLAN_OPTIONS_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_plan_buttons(),
        )

    # ── /add (admin) ──────────────────────────────────────────────────────────
    async def add_premium_command(client: Client, message: Message):
        if message.from_user.id != DEVELOPER_USER_ID:
            await message.reply_text("❌ **Admin only command.**", parse_mode=ParseMode.MARKDOWN)
            return

        if len(message.command) != 3 or message.command[2] not in ("1", "2", "3"):
            await message.reply_text(
                "❌ **Usage:** `/add {username_or_id} {1|2|3}`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        identifier = message.command[1]
        plan_key   = f"plan{message.command[2]}"
        try:
            target_id = int(identifier)
        except ValueError:
            ident = identifier.lstrip("@")
            user  = await client.get_users(ident)
            target_id = user.id

        plan_map = {"plan1": prem_plan1, "plan2": prem_plan2, "plan3": prem_plan3}
        plan     = PLANS[plan_key]
        expiry   = datetime.utcnow() + timedelta(days=30)

        for k, col in plan_map.items():
            if k != plan_key:
                col.delete_one({"user_id": target_id})

        plan_map[plan_key].update_one(
            {"user_id": target_id},
            {"$set": {
                "user_id": target_id, "plan": plan_key, "plan_name": plan["name"],
                "accounts": plan["accounts"], "max_downloads": plan["max_downloads"],
                "private_support": plan["private_support"],
                "inbox_support": plan["inbox_support"], "expiry_date": expiry,
            }},
            upsert=True,
        )
        await message.reply_text(
            f"✅ **Promoted** `{identifier}` (ID: `{target_id}`) to **{plan['name']}** for 30 days.",
            parse_mode=ParseMode.MARKDOWN,
        )

    # ── /rm (admin) ───────────────────────────────────────────────────────────
    async def remove_premium_command(client: Client, message: Message):
        if message.from_user.id != DEVELOPER_USER_ID:
            await message.reply_text("❌ **Admin only command.**", parse_mode=ParseMode.MARKDOWN)
            return
        if len(message.command) != 2:
            await message.reply_text("❌ **Usage:** `/rm {username_or_id}`", parse_mode=ParseMode.MARKDOWN)
            return

        identifier = message.command[1]
        try:
            target_id = int(identifier)
        except ValueError:
            user = await client.get_users(identifier.lstrip("@"))
            target_id = user.id

        removed = any(
            col.delete_one({"user_id": target_id}).deleted_count > 0
            for col in (prem_plan1, prem_plan2, prem_plan3)
        )
        if removed:
            await message.reply_text(
                f"✅ **Removed** `{identifier}` (ID: `{target_id}`) from all premium plans.",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await message.reply_text(
                f"⚠️ `{identifier}` doesn't have an active premium plan.",
                parse_mode=ParseMode.MARKDOWN,
            )

    # ── Plan selection callbacks ───────────────────────────────────────────────
    async def handle_plan_callback(client: Client, callback_query: CallbackQuery):
        data    = callback_query.data
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id

        plan_map = {"buy_plan1": "plan1", "buy_plan2": "plan2", "buy_plan3": "plan3"}
        if data in plan_map:
            await generate_invoice(client, chat_id, user_id, plan_map[data])
            await callback_query.answer(f"✅ Generating invoice for {PLANS[plan_map[data]]['name']}…")
        elif data == "show_plan_options":
            await client.edit_message_text(
                chat_id, callback_query.message.id,
                PLAN_OPTIONS_TEXT,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_plan_buttons(),
            )
            await callback_query.answer()

    # ── Raw update handler (payments) ─────────────────────────────────────────
    async def raw_update_handler(client: Client, update, users, chats):
        if isinstance(update, UpdateBotPrecheckoutQuery):
            try:
                await client.invoke(SetBotPrecheckoutResults(query_id=update.query_id, success=True))
            except Exception as e:
                LOGGER.error(f"Pre-checkout failed: {e}")
                await client.invoke(SetBotPrecheckoutResults(
                    query_id=update.query_id, success=False, error="Processing error."))

        elif (isinstance(update, UpdateNewMessage)
              and isinstance(update.message, MessageService)
              and isinstance(update.message.action, MessageActionPaymentSentMe)):
            payment = update.message.action
            try:
                user_id = (
                    update.message.from_id.user_id
                    if update.message.from_id and hasattr(update.message.from_id, "user_id")
                    else next((uid for uid in users if uid > 0), None)
                )
                peer = update.message.peer_id
                if isinstance(peer, PeerUser):   chat_id = peer.user_id
                elif isinstance(peer, PeerChat):    chat_id = peer.chat_id
                elif isinstance(peer, PeerChannel): chat_id = peer.channel_id
                else: raise ValueError("Unknown peer type")

                user      = users.get(user_id)
                full_name = (f"{user.first_name} {getattr(user,'last_name','') or ''}".strip()
                             if user else "Unknown")
                username  = f"@{user.username}" if user and user.username else "—"

                payload   = payment.payload.decode()
                plan_key  = payload.split("_")[1]
                plan      = PLANS[plan_key]
                expiry    = datetime.utcnow() + timedelta(days=30)
                plan_map  = {"plan1": prem_plan1, "plan2": prem_plan2, "plan3": prem_plan3}

                for k, col in plan_map.items():
                    if k != plan_key:
                        col.delete_one({"user_id": user_id})

                plan_map[plan_key].update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "user_id": user_id, "plan": plan_key, "plan_name": plan["name"],
                        "accounts": plan["accounts"], "max_downloads": plan["max_downloads"],
                        "private_support": plan["private_support"],
                        "inbox_support": plan["inbox_support"], "expiry_date": expiry,
                    }},
                    upsert=True,
                )
                await client.send_message(
                    chat_id,
                    PAYMENT_SUCCESS_TEXT.format(
                        name=full_name, plan=plan["name"],
                        amount=payment.total_amount, txn_id=payment.charge.id,
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                admin_ids = [DEVELOPER_USER_ID] if isinstance(DEVELOPER_USER_ID, int) else DEVELOPER_USER_ID
                for aid in admin_ids:
                    try:
                        await client.send_message(
                            aid,
                            ADMIN_NOTIFICATION_TEXT.format(
                                name=full_name, uid=user_id, uname=username,
                                plan=plan["name"], amount=payment.total_amount,
                                txn_id=payment.charge.id,
                            ),
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except Exception as e:
                        LOGGER.error(f"Admin notify failed for {aid}: {e}")
            except Exception as e:
                LOGGER.error(f"Payment processing error: {e}")

    # ── Register handlers ─────────────────────────────────────────────────────
    app.add_handler(
        MessageHandler(plans_command,
                       filters.command(["plans", "buy"], prefixes=COMMAND_PREFIX)
                       & (filters.private | filters.group)),
        group=1,
    )
    app.add_handler(
        MessageHandler(add_premium_command,
                       filters.command("add", prefixes=COMMAND_PREFIX) & filters.private),
        group=1,
    )
    app.add_handler(
        MessageHandler(remove_premium_command,
                       filters.command("rm", prefixes=COMMAND_PREFIX) & filters.private),
        group=1,
    )
    app.add_handler(
        CallbackQueryHandler(handle_plan_callback,
                             filters.regex(r"^(buy_plan[1-3]|show_plan_options)$")),
        group=2,
    )
    app.add_handler(RawUpdateHandler(raw_update_handler), group=3)
