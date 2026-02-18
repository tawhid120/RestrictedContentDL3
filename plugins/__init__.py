# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
from .plan import setup_plan_handler
from .public import setup_public_handler
from .info import setup_info_handler
from .thumb import setup_thumb_handler
from .pvt import setup_pvt_handler
from .login import setup_login_handler
from .pbatch import setup_pbatch_handler
from .pvdl import setup_pvdl_handler


def setup_plugins_handlers(app):
    setup_plan_handler(app)
    setup_public_handler(app)
    setup_info_handler(app)
    setup_thumb_handler(app)
    setup_pvt_handler(app)
    setup_login_handler(app)
    setup_pbatch_handler(app)
    setup_pvdl_handler(app)
