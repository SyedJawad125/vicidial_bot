"""
management/commands/run_bot.py
==============================
Django management command to run the VICIdial Bot.

Usage:
    python manage.py run_bot
    python manage.py run_bot --no-api   (AMI only, no HTTP API polling)
    python manage.py run_bot --verbose  (print every AMI event)
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

log = logging.getLogger("vicidial_bot")


class Command(BaseCommand):
    help = "Start the VICIdial Bot (AMI listener + API integration)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose", action="store_true",
            help="Print every raw AMI event to console"
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Connect to AMI but do not write to database"
        )

    def handle(self, *args, **options):
        from bot.vici_bot import VICIBot, BotConfig
        from apps import _set_bot_instance

        verbose = options.get("verbose", False)
        dry_run = options.get("dry_run", False)

        if verbose:
            logging.getLogger("vicidial_bot").setLevel(logging.DEBUG)
            logging.getLogger("vicidial_bot.ami").setLevel(logging.DEBUG)

        self.stdout.write(self.style.SUCCESS(
            "\n╔══════════════════════════════════════╗\n"
            "║       VICIdial Bot — Starting        ║\n"
            "╚══════════════════════════════════════╝"
        ))

        cfg = BotConfig(
            ami_host   = settings.VICIDIAL_AMI_HOST,
            ami_port   = settings.VICIDIAL_AMI_PORT,
            ami_user   = settings.VICIDIAL_AMI_USER,
            ami_secret = settings.VICIDIAL_AMI_SECRET,
            vicidial_url      = settings.VICIDIAL_URL,
            vicidial_api_user = settings.VICIDIAL_API_USER,
            vicidial_api_pass = settings.VICIDIAL_API_PASS,
            log_all_events = not dry_run,
            auto_dnc       = not dry_run,
        )

        self.stdout.write(f"  AMI Host  : {cfg.ami_host}:{cfg.ami_port}")
        self.stdout.write(f"  AMI User  : {cfg.ami_user}")
        self.stdout.write(f"  VICIdial  : {cfg.vicidial_url}")
        self.stdout.write(f"  Dry Run   : {dry_run}")
        self.stdout.write("")

        bot = VICIBot(cfg)

        # Register it globally so API views can reach it
        import apps as app_module
        app_module._bot_instance = bot

        bot.start()

        self.stdout.write(self.style.SUCCESS("  Bot started. Waiting for AMI connection…"))

        if not bot.ami.wait_until_connected(timeout=15):
            self.stdout.write(self.style.WARNING(
                "  ⚠ AMI not connected yet — check host/port/credentials.\n"
                "    Bot is running and will keep retrying."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "  ✓ AMI connected to VICIdial!\n"
                "  ✓ Listening for events…\n"
                "  Press Ctrl+C to stop.\n"
            ))

        # Status ticker every 60 seconds
        try:
            tick = 0
            while True:
                time.sleep(10)
                tick += 1
                if tick % 6 == 0:   # every 60 seconds
                    state = bot.state.snapshot()
                    self.stdout.write(
                        f"  [tick] connected={state['connected']} "
                        f"events={state['event_count']} "
                        f"active_calls={state['active_calls']} "
                        f"last={state['last_event']}"
                    )

        except KeyboardInterrupt:
            self.stdout.write("\n  Stopping bot…")
            bot.stop()
            self.stdout.write(self.style.SUCCESS("  Bot stopped. Bye!"))
