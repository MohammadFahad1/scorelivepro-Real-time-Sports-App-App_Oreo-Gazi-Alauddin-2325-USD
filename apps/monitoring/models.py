# apps/monitoring/models.py
from django.db import models
from django.conf import settings

class GuestDevice(models.Model):
    """
    Tracks unregistered users via unique device ID (UUID).
    """
    device_id = models.CharField(max_length=255, unique=True, db_index=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    platform = models.CharField(max_length=100, blank=True, null=True) # e.g. iOS, Android

    def __str__(self):
        return f"Device {self.device_id}"

class ServerMetric(models.Model):
    """
    Snapshots of system health every minute.
    Now includes API Latency to correlate Load vs Performance.
    """
    cpu_usage = models.FloatField(help_text="Percentage")
    ram_usage = models.FloatField(help_text="Percentage")
    active_connections = models.IntegerField(default=0)
    
    # Correlation Metric
    avg_response_time = models.FloatField(default=0.0, help_text="Avg API Latency in ms for this minute")
    
    cache_hits = models.BigIntegerField(default=0)
    cache_misses = models.BigIntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        get_latest_by = 'timestamp'
        
class APILog(models.Model):
    """
    Log of every API and WebSocket interaction.
    """
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10) # GET, POST, WS
    response_time_ms = models.FloatField()
    status_code = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='api_logs'
    )
    # Store Device ID directly for fast aggregation without joins
    device_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at', 'status_code']),
            models.Index(fields=['endpoint']),
        ]

class ErrorLog(models.Model):
    message = models.TextField()
    path = models.CharField(max_length=255)
    level = models.CharField(max_length=20, default='medium')
    count = models.IntegerField(default=1)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)