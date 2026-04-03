# # from django.apps import AppConfig


# # class BotApiConfig(AppConfig):
# #     default_auto_field = "django.db.models.BigAutoField"
# #     name = "apps.bot_api"



# from django.apps import AppConfig
# import logging

# logger = logging.getLogger(__name__)

# # Global bot instance placeholder
# _bot_instance = None

# def get_bot_instance():
#     """Get the running bot instance."""
#     global _bot_instance
#     return _bot_instance

# def set_bot_instance(bot):
#     """Set the bot instance (called during startup)."""
#     global _bot_instance
#     _bot_instance = bot
#     logger.info("Bot instance registered")

# class BotApiConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'apps.bot_api'
    
#     def ready(self):
#         # Import signals or startup code here if needed
#         pass





"""
apps/bot_api/apps.py
=====================
AppConfig for the VICIdial Bot API app.

The global `_bot_instance` is set once during server startup via
`set_bot_instance(bot)` and retrieved anywhere with `get_bot_instance()`.
"""

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)

# ── Global bot instance placeholder ──────────────────────────────
_bot_instance = None


def get_bot_instance():
    """Return the running bot instance (or None if not started yet)."""
    global _bot_instance
    return _bot_instance


def set_bot_instance(bot) -> None:
    """
    Register the bot instance.
    Call this from your bot startup routine (e.g. management command / WSGI ready hook).
    """
    global _bot_instance
    _bot_instance = bot
    logger.info("VICIdial bot instance registered successfully.")


# ── AppConfig ─────────────────────────────────────────────────────

class BotApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "apps.bot_api"
    verbose_name       = "VICIdial Bot API"

    def ready(self):
        # Signals or one-time startup imports go here.
        # Example: import apps.bot_api.signals  # noqa: F401
        pass