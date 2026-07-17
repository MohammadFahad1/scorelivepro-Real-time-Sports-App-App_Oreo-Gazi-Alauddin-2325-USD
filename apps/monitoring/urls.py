# apps/monitoring/urls.py
from django.urls import path
from .views import AdminDashboardStatsView, ServerHistoryView, EngagementHistoryView

urlpatterns = [
    path('dashboard/stats/', AdminDashboardStatsView.as_view(), name='admin-stats'),
    # For the "System Load" chart
    path('dashboard/history/server/', ServerHistoryView.as_view(), name='admin-server-history'),
    # For the "User Engagement" chart
    path('dashboard/history/engagement/', EngagementHistoryView.as_view(), name='admin-engagement-history'),
]