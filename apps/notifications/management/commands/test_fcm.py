# apps/notifications/management/commands/test_fcm.py
from django.core.management.base import BaseCommand
from notifications.services import NotificationService

class Command(BaseCommand):
    help = 'Sends a test push notification to a topic'

    def add_arguments(self, parser):
        parser.add_argument('topic', type=str, help='The topic to send to (e.g., system_health)')

    def handle(self, *args, **options):
        topic = options['topic']
        self.stdout.write(f"Sending test notification to topic: {topic}...")

        success = NotificationService.send_push_to_topic(
            topic=topic,
            title="Test Notification 🔔",
            body="If you read this, Firebase is working!",
            data={"click_action": "FLUTTER_NOTIFICATION_CLICK"}
        )

        if success:
            self.stdout.write(self.style.SUCCESS("Success! Check your device or Django Admin logs."))
        else:
            self.stdout.write(self.style.ERROR("Failed. Check console output for errors."))