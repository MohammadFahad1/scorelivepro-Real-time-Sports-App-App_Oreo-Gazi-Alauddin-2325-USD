import os
import django
from django.core.mail import send_mail
from django.conf import settings
 
# Step 1: Point Django to your settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
 
# Step 2: Initialize Django
django.setup()
 
# Step 3: Now Django knows how to send mail using your configured settings
subject = "Test Email from Django"
message = "This is a test email sent from your Django application."
from_email = settings.DEFAULT_FROM_EMAIL
recipient_list = ["abdullah.al.fahad@outlook.com"]
# recipient_list = ["test-ry6n05gjm@srv1.mail-tester.com"]
 
print(f"Attempting to send email from: {from_email} to: {recipient_list}")
 
try:
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
    )
    print("Test email sent successfully!")
except Exception as e:
    print(f"Failed to send test email. Error: {type(e).__name__}: {e}")