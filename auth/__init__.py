# Copyright @ISmartDevs
# Channel t.me/TheSmartDev
from .logs.logs import setup_logs_handler
from .restart.restart import setup_restart_handler
from .speedtest.speedtest import setup_speed_handler
from .sudo.sudo import setup_sudo_handler
from .set.set import setup_set_handler


def setup_auth_handlers(app):
    setup_sudo_handler(app)
    setup_restart_handler(app)
    setup_speed_handler(app)
    setup_logs_handler(app)
    setup_set_handler(app)
