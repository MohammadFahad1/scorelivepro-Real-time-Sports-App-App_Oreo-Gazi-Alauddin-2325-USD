from rest_framework import generics, permissions, status, filters, views
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from .models import UserDevice, ScheduledNotification, NotificationLog, UserHiddenNotification
from .serializers import UserDeviceSerializer, ScheduledNotificationSerializer, NotificationLogSerializer

# =========================================================
#                    PAGINATION CONFIG
# =========================================================

class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

# =========================================================
#                  MOBILE USER VIEWS
# =========================================================

class NotificationInboxView(generics.ListAPIView):
    """
    Returns a personalized feed of notifications based on the user's
    Favorite Teams and Leagues, EXCLUDING ones the user removed.
    """
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'fan_profile'):
            return NotificationLog.objects.none()

        profile = user.fan_profile

        # 1. Get IDs of favorites
        fav_team_ids = profile.favorite_teams.values_list('id', flat=True)
        fav_league_ids = profile.favorite_leagues.values_list('id', flat=True)

        # 2. Build Topic List
        topics = [f"team_{tid}" for tid in fav_team_ids]
        topics += [f"league_{lid}" for lid in fav_league_ids]
        
        # 3. Add User-specific topic and GLOBAL admin topic
        topics.append(f"user_{user.id}")
        topics.append("global")

        # 4. Get IDs of notifications the user hid/removed
        hidden_ids = UserHiddenNotification.objects.filter(user=user).values_list('notification_id', flat=True)

        # 5. Fetch Logs matching topics AND excluding hidden
        return NotificationLog.objects.filter(
            topic__in=topics,
            status='SENT' 
        ).exclude(id__in=hidden_ids).order_by('-created_at')


class UnreadCountView(views.APIView):
    """
    Returns the count of notifications since the last check, excluding hidden ones.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: {"unread_count": 5}})
    def get(self, request):
        user = request.user
        if not hasattr(user, 'fan_profile'):
            return Response({"unread_count": 0})

        profile = user.fan_profile
        last_check = profile.last_inbox_check

        # Re-calculate topics
        fav_team_ids = profile.favorite_teams.values_list('id', flat=True)
        fav_league_ids = profile.favorite_leagues.values_list('id', flat=True)
        topics = [f"team_{tid}" for tid in fav_team_ids] + [f"league_{lid}" for lid in fav_league_ids]
        topics.append(f"user_{user.id}")
        topics.append("global")

        hidden_ids = UserHiddenNotification.objects.filter(user=user).values_list('notification_id', flat=True)

        qs = NotificationLog.objects.filter(topic__in=topics, status='SENT').exclude(id__in=hidden_ids)
        
        if last_check:
            qs = qs.filter(created_at__gt=last_check)
        
        count = qs.count()
        return Response({"unread_count": count})


class MarkAllReadView(views.APIView):
    """
    Updates the 'last_inbox_check' timestamp to NOW.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if hasattr(user, 'fan_profile'):
            user.fan_profile.last_inbox_check = timezone.now()
            user.fan_profile.save()
            return Response({"message": "Marked as read"}, status=status.HTTP_200_OK)
        return Response({"error": "No profile"}, status=400)


class HideNotificationView(views.APIView):
    """
    'Removes' a single notification from the user's inbox by marking it as hidden.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        notification = get_object_or_404(NotificationLog, pk=pk)
        UserHiddenNotification.objects.get_or_create(user=request.user, notification=notification)
        return Response({"message": "Notification removed"}, status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Notifications'])
class FCMDeviceView(generics.CreateAPIView):
    """
    Register or update a device FCM token.
    """
    serializer_class = UserDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        registration_id = request.data.get('registration_id')
        device_type = request.data.get('type', 'android')
        
        if not registration_id:
            return Response({"error": "registration_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        device, created = UserDevice.objects.update_or_create(
            registration_id=registration_id,
            defaults={
                'user': request.user,
                'type': device_type,
                'active': True
            }
        )
        
        return Response({'status': 'Device registered', 'device_id': device.id}, status=status.HTTP_201_CREATED)

class TestPushNotificationView(views.APIView):
    """
    TEMPORARY TESTING ENDPOINT: Sends a test push notification directly to a device FCM token.
    Allows testing FCM configuration without relying on celery or topics.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({"error": "FCM 'token' is required in the body."}, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get('title', '🧪 ScoreLivePro Test')
        body = request.data.get('body', 'This is a test notification hitting your device directly!')
        
        from .services import NotificationService
        result = NotificationService.send_push_to_token(token, title, body, data={"type": "TEST"})
        
        if result.get("success"):
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


# =========================================================
#                  ADMIN DASHBOARD VIEWS
# =========================================================

@extend_schema(tags=['Notifications - Admin'], summary="List or Schedule Notifications")
class ScheduledNotificationListView(generics.ListCreateAPIView):
    queryset = ScheduledNotification.objects.all().order_by('-scheduled_time')
    serializer_class = ScheduledNotificationSerializer
    permission_classes = [permissions.IsAdminUser] 
    pagination_class = StandardPagination
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_sent']
    ordering_fields = ['scheduled_time', 'created_at']

@extend_schema(tags=['Notifications - Admin'], summary="Edit or Delete Scheduled Notification")
class ScheduledNotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduledNotification.objects.all()
    serializer_class = ScheduledNotificationSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_update(self, serializer):
        # Prevent editing if the notification has already been sent
        if self.get_object().is_sent:
            raise ValidationError("You cannot edit a notification that has already been sent.")
        serializer.save()

    def perform_destroy(self, instance):
        # Prevent deleting if it's already sent (preserves historical record)
        if instance.is_sent:
            raise ValidationError("You cannot delete a notification that has already been sent.")
        instance.delete()

@extend_schema(tags=['Notifications - Admin'], summary="View Notification Logs")
class NotificationLogListView(generics.ListAPIView):
    queryset = NotificationLog.objects.all().order_by('-created_at')
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAdminUser] 
    pagination_class = StandardPagination
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'topic']
    search_fields = ['title', 'body', 'error_message']