from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from users.models import FanProfile 
from notifications.services import NotificationService

@receiver(m2m_changed, sender=FanProfile.favorite_teams.through)
def update_team_topic_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Syncs FCM topic subscriptions when a user favorites/unfavorites a team.
    """
    if action not in ["post_add", "post_remove"]:
        return

    # Check user settings
    if not instance.receive_live_notifications:
        return

    # Get user's active device tokens
    user_devices = instance.user.devices.filter(active=True).values_list('registration_id', flat=True)
    tokens = list(user_devices)
    
    if not tokens:
        return

    for team_id in pk_set:
        topic = f"team_{team_id}"
        if action == "post_add":
            NotificationService.subscribe_tokens_to_topic(tokens, topic)
        elif action == "post_remove":
            NotificationService.unsubscribe_tokens_from_topic(tokens, topic)

@receiver(m2m_changed, sender=FanProfile.favorite_leagues.through)
def update_league_topic_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return

    if not instance.receive_news_updates:
        return

    user_devices = instance.user.devices.filter(active=True).values_list('registration_id', flat=True)
    tokens = list(user_devices)
    
    if not tokens:
        return

    for league_id in pk_set:
        topic = f"league_{league_id}"
        if action == "post_add":
            NotificationService.subscribe_tokens_to_topic(tokens, topic)
        elif action == "post_remove":
            NotificationService.unsubscribe_tokens_from_topic(tokens, topic)