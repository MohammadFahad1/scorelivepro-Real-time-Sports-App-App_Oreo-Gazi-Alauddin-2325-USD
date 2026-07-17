# apps/monitoring/admin.py
from django.contrib import admin
from .models import APILog, ErrorLog, ServerMetric, GuestDevice

@admin.register(GuestDevice)
class GuestDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'platform', 'ip_address', 'first_seen', 'last_seen')
    search_fields = ('device_id', 'ip_address')
    list_filter = ('platform', 'first_seen')
    readonly_fields = ('first_seen', 'last_seen')

@admin.register(ServerMetric)
class ServerMetricAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'cpu_usage', 'ram_usage', 'active_connections', 'cache_hits')
    list_filter = ('timestamp',)
    # Metrics are read-only history
    def has_add_permission(self, request):
        return False

@admin.register(APILog)
class APILogAdmin(admin.ModelAdmin):
    list_display = ('method', 'endpoint', 'status_code', 'response_time_ms', 'created_at', 'user_or_device')
    list_filter = ('method', 'status_code', 'created_at')
    search_fields = ('endpoint', 'ip_address', 'user__email', 'device_id')
    
    def user_or_device(self, obj):
        return obj.user.email if obj.user else f"Device: {obj.device_id}"
    user_or_device.short_description = "User / Device"

@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ('path', 'level', 'count', 'is_resolved', 'updated_at')
    list_filter = ('is_resolved', 'level', 'updated_at')
    search_fields = ('path', 'message')
    actions = ['mark_as_resolved']

    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
    mark_as_resolved.short_description = "Mark selected errors as resolved"