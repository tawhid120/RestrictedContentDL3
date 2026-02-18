# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
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
    """
    Catch-all — only fires for callbacks not claimed by a more specific handler
    registered with a lower group number.
    """
    await handle_callback_query(client, callback_query)


LOGGER.info("✅ RestrictedContentDL started successfully!")
app.run()
