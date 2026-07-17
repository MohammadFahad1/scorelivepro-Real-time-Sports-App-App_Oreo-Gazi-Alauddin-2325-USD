import random
from django.core.mail import EmailMessage, send_mail
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.request import Request
from .models import OneTimePassword, UserActivity

User = get_user_model()

def send_verification_email(user):
    """
    Used for new user registration (Account Activation)
    """
    otp_code = str(random.randint(100000, 999999)) # generates 5 digits

    OneTimePassword.objects.update_or_create(
        user=user,
        defaults={'otp': otp_code}
    )

    # prepare email
    subject = "Verify your email address"
    email_body = f"Hi {user.first_name},\n\nYour verification code is: {otp_code}\n\nPlease enter this code to activate your account."
    from_email = getattr(settings, 'EMAIL_HOST_USER', 'noreply@scorelivepro.com')

    d_email = EmailMessage(subject=subject, body=email_body, from_email=from_email, to=[user.email])
    d_email.send(fail_silently=False)


def send_otp_via_email(email, purpose=None):
    """
    Used for Admin Login and Password Reset.
    'purpose' determines the email text.
    """
    otp_code = str(random.randint(100000, 999999))  # generated 5 digits
    
    user = User.objects.get(email=email)
    
    OneTimePassword.objects.update_or_create(
        user=user,
        defaults={'otp': otp_code}
    )
    
    # Dynamic Subject and Body based on purpose
    if purpose == 'password_reset':
        subject = "Reset Your Password - OTP"
        action_text = "reset your password"
    elif purpose == 'admin_login':
        subject = "Admin Login Verification - OTP"
        action_text = "complete your admin login"
    else:
        subject = "Your Security Code"
        action_text = "verify your identity"

    email_body = f"Hi {user.first_name},\n\nYour One Time Password (OTP) to {action_text} is: {otp_code}\n\nThis code is valid for 5 minutes."
    
    from_email = getattr(settings, 'EMAIL_HOST_USER', 'noreply@scorelivepro.com')
    
    d_email = EmailMessage(subject=subject, body=email_body, from_email=from_email, to=[email])
    d_email.send(fail_silently=False)


def log_activity(user, action, details=None, request=None):
    """
    Logs a user action to the database.
    """
    ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
    
    UserActivity.objects.create(
        user=user,
        action=action,
        details=details,
        ip_address=ip
    )