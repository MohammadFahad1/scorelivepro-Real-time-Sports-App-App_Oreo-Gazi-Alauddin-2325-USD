# apps/monitoring/tasks.py
import psutil
import redis
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg
from celery import shared_task
from django.conf import settings
from .models import ServerMetric, APILog

@shared_task
def collect_system_metrics():
    """
    Runs every 60s via Celery Beat.
    """
    # 1. System Stats
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    
    # 2. Calculate Avg Latency for the last minute
    one_minute_ago = timezone.now() - timedelta(minutes=1)
    avg_latency = APILog.objects.filter(
        created_at__gte=one_minute_ago
    ).aggregate(avg=Avg('response_time_ms'))['avg'] or 0.0

    # 3. Redis Stats
    hits = 0
    misses = 0
    try:
        r = redis.StrictRedis.from_url(settings.CELERY_BROKER_URL)
        info = r.info()
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
    except Exception:
        pass

    # 4. Save Unified Metric
    ServerMetric.objects.create(
        cpu_usage=cpu,
        ram_usage=ram,
        avg_response_time=avg_latency, # <--- Correlated Data
        cache_hits=hits,
        cache_misses=misses
    )
    
    return f"Saved: CPU {cpu}%, Latency {avg_latency}ms"