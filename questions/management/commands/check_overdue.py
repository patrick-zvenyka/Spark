from django.core.management.base import BaseCommand

from questions.services import notify_overdue


class Command(BaseCommand):
    help = (
        "Notify departments about questions that have passed their agreed response time. "
        "Schedule this with cron, e.g. every hour: `0 * * * * python manage.py check_overdue`."
    )

    def handle(self, *args, **options):
        count = notify_overdue()
        self.stdout.write(self.style.SUCCESS(f"Sent overdue alerts for {count} question(s)."))
