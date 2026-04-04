"""
apps/voice/urls.py
"""
from django.urls import path
from . import views
 
urlpatterns = [
    path("v1/sessions/",   views.VoiceSessionView.as_view(),  name="voice-sessions"),
    path("v1/transcripts/",views.TranscriptLogView.as_view(), name="voice-transcripts"),
    path("v1/test/tts/",   views.TTSTestView.as_view(),       name="voice-test-tts"),
    path("v1/test/stt/",   views.STTTestView.as_view(),       name="voice-test-stt"),
    path("v1/health/",     views.VoiceHealthView.as_view(),   name="voice-health"),
]