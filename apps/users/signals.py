import requests
from django.core.files.base import ContentFile
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import FanProfile, AdminProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a FanProfile for new users.
    If the user is a superuser OR staff (admin), create an AdminProfile instead.
    """
    if created:
        # Check is_staff OR is_superuser to catch all types of admins
        if instance.is_superuser or instance.is_staff:
            admin_group, _ = Group.objects.get_or_create(name='Admin')
            instance.groups.add(admin_group)
            AdminProfile.objects.get_or_create(user=instance)
        else:
            # Default to Fan for all other registrations
            fan_group, _ = Group.objects.get_or_create(name='Fan')
            instance.groups.add(fan_group)
            FanProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure the profile is saved when the user is saved."""
    if hasattr(instance, 'fan_profile'):
        instance.fan_profile.save()
    elif hasattr(instance, 'admin_profile'):
        instance.admin_profile.save()


@receiver(pre_delete, sender=User)
def cleanup_firebase_on_user_delete(sender, instance, **kwargs):
    """
    Fires BEFORE a user is deleted (admin panel, API, bulk delete — all cases).
    Unsubscribes all of the user's FCM tokens from every Firebase topic they
    are subscribed to, so stale tokens don't linger in Firebase after deletion.
    The UserDevice records get CASCADE-deleted after this, so we must act first.
    """
    try:
        from notifications.services import NotificationService

        # Grab tokens BEFORE cascade wipes UserDevice
        tokens = list(
            instance.devices.filter(active=True).values_list('registration_id', flat=True)
        )
        if not tokens:
            return

        if hasattr(instance, 'fan_profile'):
            profile = instance.fan_profile

            # Unsubscribe from every followed team topic
            for team in profile.favorite_teams.all():
                NotificationService.unsubscribe_tokens_from_topic(tokens, f"team_{team.id}")

            # Unsubscribe from every followed league topic
            for league in profile.favorite_leagues.all():
                NotificationService.unsubscribe_tokens_from_topic(tokens, f"league_{league.id}")

        print(f"✅ Firebase cleanup complete for deleted user: {instance.email}")

    except Exception as e:
        # Never block the deletion — just warn
        print(f"⚠️ Firebase cleanup warning for {instance.email}: {e}")
