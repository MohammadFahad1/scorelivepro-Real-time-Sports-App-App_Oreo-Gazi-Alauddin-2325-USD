# apps/monitoring/views.py
import time
import redis
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from drf_spectacular.utils import extend_schema

from .models import APILog, ErrorLog, ServerMetric, GuestDevice
from .serializers import (
    AdminDashboardStatsSerializer, 
    ServerHistorySerializer, 
    UserEngagementSerializer # [FIX] Matches serializers.py now
)
from django.contrib.auth import get_user_model

User = get_user_model()

# Initialize Redis with Error Handling
try:
    redis_client = redis.StrictRedis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
except Exception as e:
    print(f"❌ View Redis Init Error: {e}")
    redis_client = None

class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Get System Health & Analytics",
        responses={200: AdminDashboardStatsSerializer}
    )
    def get(self, request):
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)
        
        # --- 1. Real-Time (Redis) ---
        active_reg = 0
        active_guest = 0
        
        if redis_client:
            try:
                min_score = time.time() - 300
                active_reg = redis_client.zcount('active_users:registered', min_score, "+inf")
                active_guest = redis_client.zcount('active_users:guests', min_score, "+inf")
                
                # DEBUG: Print to Docker logs to verify data exists
                print(f"🔍 [Dashboard] Registered: {active_reg}, Guests: {active_guest}")
            except Exception as e:
                print(f"❌ [Dashboard] Redis Read Error: {e}")

        # --- 2. Engagement (Summary) ---
        dau_registered = APILog.objects.filter(
            created_at__gte=last_24h, user__isnull=False
        ).values('user').distinct().count()
        
        dau_guests = APILog.objects.filter(
            created_at__gte=last_24h, device_id__isnull=False, user__isnull=True
        ).values('device_id').distinct().count()
        
        avg_session = APILog.objects.filter(
            created_at__gte=last_24h, method='WS'
        ).aggregate(avg=Avg('response_time_ms'))['avg']
        avg_session_min = round((avg_session or 0) / 60000, 2)

        # --- 3. Totals (DB) ---
        total_reg = User.objects.count()
        total_guest = GuestDevice.objects.count()

        # --- 4. Performance ---
        avg_latency = APILog.objects.filter(
            created_at__gte=one_hour_ago, 
            method__in=['GET', 'POST']
        ).aggregate(avg=Avg('response_time_ms'))['avg'] or 0

        latest_metric = ServerMetric.objects.last()
        
        # Calculate Cache Hit Rate safely
        hit_rate = 0.0
        if latest_metric:
            total_ops = latest_metric.cache_hits + latest_metric.cache_misses
            if total_ops > 0:
                hit_rate = (latest_metric.cache_hits / total_ops) * 100

        # --- 5. Endpoints & Errors ---
        endpoint_stats = APILog.objects.filter(
            created_at__gte=one_hour_ago
        ).values('endpoint').annotate(
            avg_time=Avg('response_time_ms'),
            hits=Count('id')
        ).order_by('-hits')[:10]

        recent_errors = ErrorLog.objects.filter(
            is_resolved=False
        ).order_by('-updated_at')[:5]

        # Construct Data
        data = {
            "real_time": {
                "active_registered": active_reg,
                "active_guests": active_guest,
                "total_active": active_reg + active_guest
            },
            "engagement": {
                "dau_total": dau_registered + dau_guests,
                "avg_session_duration_min": avg_session_min
            },
            "totals": {
                "registered_users": total_reg,
                "guest_devices": total_guest,
            },
            "performance_1h": {
                "avg_api_latency_ms": round(avg_latency, 2),
                "cpu_load_percent": latest_metric.cpu_usage if latest_metric else 0,
                "ram_usage_percent": latest_metric.ram_usage if latest_metric else 0,
                "cache_hit_rate": round(hit_rate, 1)
            },
            "endpoints": list(endpoint_stats),
            "errors": recent_errors
        }
        
        serializer = AdminDashboardStatsSerializer(instance=data)
        return Response(serializer.data)

class ServerHistoryView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(summary="Get 24h Server Load History (Graph Data)")
    def get(self, request):
        last_24h = timezone.now() - timedelta(hours=24)
        metrics = ServerMetric.objects.filter(timestamp__gte=last_24h).order_by('timestamp')
        
        data = []
        for i, m in enumerate(metrics):
            if i % 10 == 0: 
                data.append({
                    "timestamp": m.timestamp,
                    "cpu_usage": m.cpu_usage,
                    "ram_usage": m.ram_usage,
                    "avg_response_time": m.avg_response_time
                })
        return Response(data)

class EngagementHistoryView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Get 7-Day Engagement History (Graph Data)",
        responses={200: UserEngagementSerializer(many=True)}
    )
    def get(self, request):
        now = timezone.now()
        last_7_days = now - timedelta(days=6)
        
        # 1. Fetch from DB
        stats_query = APILog.objects.filter(created_at__gte=last_7_days)\
            .annotate(date=TruncDate('created_at'))\
            .values('date')\
            .annotate(
                distinct_users=Count('user', distinct=True),
                distinct_devices=Count('device_id', distinct=True),
                avg_ws_duration=Avg('response_time_ms', filter=Q(method='WS'))
            ).order_by('date')

        # 2. Convert to Dictionary for fast lookup
        stats_map = {str(item['date']): item for item in stats_query}

        # 3. Backfill missing days with 0
        final_data = []
        for i in range(7):
            day = last_7_days + timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            day_label = day.strftime("%a") 
            
            if day_str in stats_map:
                stat = stats_map[day_str]
                dau = stat['distinct_users'] + stat['distinct_devices']
                avg_min = round((stat['avg_ws_duration'] or 0) / 60000, 2)
            else:
                dau = 0
                avg_min = 0

            final_data.append({
                "date": day_label, 
                "daily_active_users": dau,
                "avg_session_min": avg_min
            })
            
        return Response(final_data)