# from django.apps import AppConfig


# class VoiceConfig(AppConfig):
#     default_auto_field = "django.db.models.BigAutoField"
#     name = "apps.voice"



"""
apps/voice/apps.py
"""
import logging
from django.apps import AppConfig
 
logger = logging.getLogger(__name__)
 
 
class VoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "apps.voice"
    verbose_name       = "Voice Layer (STT + TTS)"
 
    def ready(self):
        # Pre-load engines in background so first call is instant
        import threading
        def _preload():
            try:
                from apps.voice.engines.stt_vosk import get_stt_engine
                from apps.voice.engines.tts_melo import get_tts_engine
                get_stt_engine("en")
                get_tts_engine("en")
                logger.info("Voice engines pre-loaded successfully")
            except Exception as exc:
                logger.warning("Voice engine pre-load failed: %s", exc)
        threading.Thread(target=_preload, daemon=True).start()