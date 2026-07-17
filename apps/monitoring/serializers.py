# apps/monitoring/serializers.py
from rest_framework import serializers
from .models import ErrorLog, ServerMetric

# --- Helper Serializers for the Dashboard Structure ---

class RealTimeStatsSerializer(serializers.Serializer):
    active_registered = serializers.IntegerField(help_text="Registered users active in last 5 min")
    active_guests = serializers.IntegerField(help_text="Guest devices active in last 5 min")
    total_active = serializers.IntegerField(help_text="Total active users")

class EngagementSerializer(serializers.Serializer):
    """ Used for the Summary Card (Total DAU) """
    dau_total = serializers.IntegerField(help_text="Distinct users/devices in last 24h")
    avg_session_duration_min = serializers.FloatField(help_text="Avg WebSocket session length in minutes")

class TotalsSerializer(serializers.Serializer):
    registered_users = serializers.IntegerField()
    guest_devices = serializers.IntegerField()

class PerformanceSerializer(serializers.Serializer):
    avg_api_latency_ms = serializers.FloatField(help_text="Average across all endpoints (last 1h)")
    cpu_load_percent = serializers.FloatField()
    ram_usage_percent = serializers.FloatField()
    cache_hit_rate = serializers.FloatField(help_text="Redis Hit Ratio %")

class EndpointStatSerializer(serializers.Serializer):
    endpoint = serializers.CharField()
    avg_time = serializers.FloatField()
    hits = serializers.IntegerField()

class ErrorLogSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorLog
        fields = ['path', 'message', 'count', 'level']

# --- Main Dashboard Serializer ---

class AdminDashboardStatsSerializer(serializers.Serializer):
    """
    Complete structure of the /dashboard/stats/ endpoint.
    """
    real_time = RealTimeStatsSerializer()
    engagement = EngagementSerializer()
    totals = TotalsSerializer()
    performance_1h = PerformanceSerializer()
    endpoints = EndpointStatSerializer(many=True)
    errors = ErrorLogSummarySerializer(many=True)

# --- Graph Serializers ---

class ServerHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServerMetric
        fields = ['timestamp', 'cpu_usage', 'ram_usage', 'avg_response_time']

# [FIX] This class was missing or named incorrectly before
class UserEngagementSerializer(serializers.Serializer):
    date = serializers.CharField(help_text="Day label (e.g., Mon, Tue)")
    daily_active_users = serializers.IntegerField()
    avg_session_min = serializers.FloatField()