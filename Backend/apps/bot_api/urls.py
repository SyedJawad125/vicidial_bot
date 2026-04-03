# """api/urls.py"""
# from django.urls import path
# from . import views

# urlpatterns = [
#     # ── Bot status & logs ──────────────────────────────
#     path("v1/status/",           views.BotStatusView.as_view()),
#     path("v1/events/",           views.EventLogView.as_view()),
#     path("v1/calls/",            views.CallLogView.as_view()),
#     path("v1/commands/",         views.CommandLogView.as_view()),

#     # ── Bot commands ───────────────────────────────────
#     path("v1/commands/originate/", views.OriginateView.as_view()),
#     path("v1/commands/hangup/",    views.HangupView.as_view()),
#     path("v1/commands/transfer/",  views.TransferView.as_view()),
#     path("v1/commands/dtmf/",      views.DTMFView.as_view()),
#     path("v1/commands/dnc/",       views.DNCView.as_view()),
#     path("v1/commands/ping/",      views.PingView.as_view()),

#     # ── VICIdial API proxy ─────────────────────────────
#     path("v1/vicidial/campaigns/",                         views.VICICampaignsView.as_view()),
#     path("v1/vicidial/agents/",                            views.VICIAgentsView.as_view()),
#     path("v1/vicidial/active_calls/",                      views.VICIActiveCallsView.as_view()),
#     path("v1/vicidial/add_lead/",                          views.VICIAddLeadView.as_view()),
#     path("v1/vicidial/update_lead/",                       views.VICIUpdateLeadView.as_view()),
#     path("v1/vicidial/campaign/<str:campaign_id>/<str:action>/",
#                                                         views.VICICampaignControlView.as_view()),
# ]


"""
apps/bot_api/urls.py
=====================
URL routing for the VICIdial Bot API.
Mount this under a prefix in your root urls.py:

    path("api/bot/", include("apps.bot_api.urls")),
"""

from django.urls import path
from . import views

urlpatterns = [

    # ── Bot status & audit logs ────────────────────────────────────
    path("v1/status/",   views.BotStatusView.as_view(),  name="bot-status"),
    path("v1/events/",   views.EventLogView.as_view(),   name="bot-events"),
    path("v1/calls/",    views.CallLogView.as_view(),    name="bot-calls"),
    path("v1/commands/", views.CommandLogView.as_view(), name="bot-commands"),

    # ── Bot action commands ────────────────────────────────────────
    path("v1/commands/originate/", views.OriginateView.as_view(), name="bot-originate"),
    path("v1/commands/hangup/",    views.HangupView.as_view(),    name="bot-hangup"),
    path("v1/commands/transfer/",  views.TransferView.as_view(),  name="bot-transfer"),
    path("v1/commands/dtmf/",      views.DTMFView.as_view(),      name="bot-dtmf"),
    path("v1/commands/dnc/",       views.DNCView.as_view(),       name="bot-dnc"),
    path("v1/commands/ping/",      views.PingView.as_view(),      name="bot-ping"),

    # ── VICIdial API proxy ─────────────────────────────────────────
    path("v1/vicidial/campaigns/",    views.VICICampaignsView.as_view(),   name="vici-campaigns"),
    path("v1/vicidial/agents/",       views.VICIAgentsView.as_view(),      name="vici-agents"),
    path("v1/vicidial/active_calls/", views.VICIActiveCallsView.as_view(), name="vici-active-calls"),
    path("v1/vicidial/add_lead/",     views.VICIAddLeadView.as_view(),     name="vici-add-lead"),
    path("v1/vicidial/update_lead/",  views.VICIUpdateLeadView.as_view(),  name="vici-update-lead"),

    path(
        "v1/vicidial/campaign/<str:campaign_id>/<str:action>/",
        views.VICICampaignControlView.as_view(),
        name="vici-campaign-control",
    ),
]