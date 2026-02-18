# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
# Shared helper so both the /info command and the menu callback
# can render the same profile card without importing each other.

from datetime import datetime


async def get_profile_text(user_id: int) -> str:
    """Return an HTML profile card for the given user_id."""
    # Import here to avoid circular imports at module load time
    from core.database import prem_plan1, prem_plan2, prem_plan3, user_sessions
    from core.db import daily_limit

    plan1 = prem_plan1.find_one({"user_id": user_id})
    plan2 = prem_plan2.find_one({"user_id": user_id})
    plan3 = prem_plan3.find_one({"user_id": user_id})

    if plan3:
        plan_name = "💎 Plan 3 — Unlimited"
        expiry    = plan3.get("expiry_date")
    elif plan2:
        plan_name = "🥇 Plan 2 — 2 000 downloads"
        expiry    = plan2.get("expiry_date")
    elif plan1:
        plan_name = "🥈 Plan 1 — 1 000 downloads"
        expiry    = plan1.get("expiry_date")
    else:
        plan_name = "🆓 Free"
        expiry    = None

    expiry_str = expiry.strftime("%d %b %Y") if expiry else "—"

    session    = user_sessions.find_one({"user_id": user_id})
    num_accs   = len(session.get("sessions", [])) if session else 0

    daily_rec  = daily_limit.find_one({"user_id": user_id})
    total_dl   = daily_rec.get("total_downloads", 0) if daily_rec else 0

    today      = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_used = 0
    if daily_rec and daily_rec.get("date") and daily_rec["date"] >= today:
        daily_used = daily_rec.get("downloads", 0)

    return (
        "<b>👤 Your Profile</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>🆔 User ID:</b> <code>{user_id}</code>\n"
        f"<b>🎖️ Plan:</b> <code>{plan_name}</code>\n"
        f"<b>📅 Expires:</b> <code>{expiry_str}</code>\n"
        f"<b>🔗 Linked Accounts:</b> <code>{num_accs}</code>\n"
        f"<b>📥 Today's Downloads:</b> <code>{daily_used}</code>\n"
        f"<b>📊 Total Downloads:</b> <code>{total_dl}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Use /plans to upgrade your plan.</i>"
    )
