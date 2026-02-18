# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
import sys

# ── uvloop: asyncio event loop 2-4x দ্রুত করে (Linux only) ──
try:
    import uvloop
    uvloop.install()  # MUST be called before any asyncio/pyrogram usage
    print("✅ uvloop installed — event loop boosted!")
except ImportError:
    print("⚠️ uvloop not available (Windows?), using default asyncio loop")

from utils import LOGGER
from auth import setup_auth_handlers
from plugins import setup_plugins_handlers
from core import setup_start_handler
from misc import handle_callback_query
from app import app  

setup_plugins_handlers(app)
setup_auth_handlers(app)
setup_start_handler(app)

@app.on_callback_query()
async def handle_callback(client, callback_query):
    await handle_callback_query(client, callback_query)

LOGGER.info("Bot Successfully Started! 💥")
app.run()
