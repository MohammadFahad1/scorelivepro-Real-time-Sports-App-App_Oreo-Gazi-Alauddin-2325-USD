from django.db import models
from django.conf import settings

class NotificationLog(models.Model):
    # e.g., "team_33", "league_39", "user_101", "global"
    topic = models.CharField(max_length=255, db_index=True)
    
    title = models.CharField(max_length=255)
    body = models.TextField()
    
    # JSON payload (match_id, type="GOAL", reason="Favorites", etc.)
    data = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=50, default='PENDING') # SENT, FAILED
    event_type = models.CharField(max_length=50, default='CUSTOM') # GOAL, FT, LINEUPS
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['topic', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.topic}: {self.title}"


class UserDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devices')
    registration_id = models.CharField(max_length=512, unique=True)
    type = models.CharField(max_length=10, choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')], default='android')
    active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.type}"


class UserHiddenNotification(models.Model):
    """
    Tracks notifications a specific user has chosen to 'remove' from their feed.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hidden_notifications')
    notification = models.ForeignKey(NotificationLog, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'notification')


class ScheduledNotification(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    
    # Changed to a free-text string field without choices
    event_type = models.CharField(max_length=50, default='CUSTOM', help_text="A string identifier for the app to parse (e.g. NEWS, UPDATE, CUSTOM)")
    
    scheduled_time = models.DateTimeField()
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scheduled: {self.title} (Global)"