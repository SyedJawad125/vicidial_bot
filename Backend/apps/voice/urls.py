"""
apps/voice/urls.py
"""
from django.urls import path
from . import views
 
urlpatterns = [
    path("sessions/",   views.VoiceSessionView.as_view(),  name="voice-sessions"),
    path("transcripts/",views.TranscriptLogView.as_view(), name="voice-transcripts"),
    path("test/tts/",   views.TTSTestView.as_view(),       name="voice-test-tts"),
    path("test/stt/",   views.STTTestView.as_view(),       name="voice-test-stt"),
    path("health/",     views.VoiceHealthView.as_view(),   name="voice-health"),
]