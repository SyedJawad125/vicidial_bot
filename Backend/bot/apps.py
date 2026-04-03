"""
apps.py — Django AppConfig.
Starts the VICIBot in a background thread when Django is ready.
"""
import logging

log = logging.getLogger("vicidial_bot")

_bot_instance = None


def get_bot_instance():
    global _bot_instance
    if _bot_instance is None:
        raise RuntimeError(
            "Bot not started. Run: python manage.py run_bot  "
            "or set AUTOSTART_BOT=True in settings."
        )
    return _bot_instance


class VICIdialBotConfig:
    name         = "vicidial_bot"
    verbose_name = "VICIdial Bot"

    def ready(self):
        from django.conf import settings
        if getattr(settings, "AUTOSTART_BOT", False):
            self._start_bot()

    def _start_bot(self):
        global _bot_instance
        from django.conf import settings
        from bot.vici_bot import VICIBot, BotConfig

        cfg = BotConfig(
            ami_host=settings.VICIDIAL_AMI_HOST,
            ami_port=settings.VICIDIAL_AMI_PORT,
            ami_user=settings.VICIDIAL_AMI_USER,
            ami_secret=settings.VICIDIAL_AMI_SECRET,
            vicidial_url=settings.VICIDIAL_URL,
            vicidial_api_user=settings.VICIDIAL_API_USER,
            vicidial_api_pass=settings.VICIDIAL_API_PASS,
            log_all_events=settings.BOT_LOG_ALL_EVENTS,
            auto_dnc=settings.BOT_AUTO_DNC,
        )

        _bot_instance = VICIBot(cfg)
        _bot_instance.start()
        log.info("VICIBot auto-started via AppConfig.ready()")
