# # apps/sports/consumers.py
# import json
# import time
# import asyncio
# import redis
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from django.conf import settings

# # Initialize Redis
# try:
#     redis_client = redis.StrictRedis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
#     redis_client.ping()
#     print("✅ WebSocket Redis Connection Established")
# except Exception as e:
#     print(f"❌ WebSocket Redis Connection Failed: {e}")

# class LiveScoreConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.group_name = "live_scores"
#         self.start_time = time.time()
        
#         # 1. Identity Extraction
#         headers = dict(self.scope['headers'])
#         self.device_id = None
        
#         for key, value in headers.items():
#             if key.lower() == b'x-device-id':
#                 self.device_id = value.decode()
#                 break

#         if not self.device_id and self.scope.get('client'):
#              self.device_id = f"ip_{self.scope['client'][0]}"
        
#         if not self.device_id:
#             self.device_id = "unknown_device"

#         print(f"🔌 Connection Attempt: Device={self.device_id}")

#         self.user = self.scope.get('user')

#         # 2. Register Guest DB
#         is_auth = self.user and self.user.is_authenticated
#         if self.device_id and not is_auth:
#             await self.register_guest_db()

#         # 3. Track Presence (Redis)
#         await self.track_presence(is_connected=True)
        
#         self.keep_alive_task = asyncio.create_task(self.heartbeat())

#         await self.channel_layer.group_add(self.group_name, self.channel_name)
#         await self.accept()
        
#         # Log the WS connection for authenticated users
#         await self.log_ws_activity()
        
#         await self.send_initial_data()

#     async def disconnect(self, close_code):
#         if hasattr(self, 'keep_alive_task'):
#             self.keep_alive_task.cancel()

#         duration_ms = (time.time() - self.start_time) * 1000
#         await self.log_session(duration_ms)
#         await self.track_presence(is_connected=False)
#         await self.channel_layer.group_discard(self.group_name, self.channel_name)

#     async def heartbeat(self):
#         try:
#             while True:
#                 await asyncio.sleep(60)
#                 await self.track_presence(is_connected=True)
#         except asyncio.CancelledError:
#             pass

#     async def track_presence(self, is_connected):
#         timestamp = time.time()
#         try:
#             if self.user and self.user.is_authenticated:
#                 key = 'active_users:registered'
#                 member = str(self.user.id)
#             else:
#                 key = 'active_users:guests'
#                 member = str(self.device_id)

#             if is_connected:
#                 redis_client.zadd(key, {member: timestamp})
#                 print(f"✅ Redis Updated: {key} -> {member}")
#             else:
#                 redis_client.zrem(key, member)
#         except Exception as e:
#             print(f"❌ Redis Track Error: {e}")

#     @database_sync_to_async
#     def register_guest_db(self):
#         from monitoring.models import GuestDevice
#         try:
#             GuestDevice.objects.get_or_create(device_id=self.device_id)
#         except Exception as e:
#             print(f"⚠️ DB Register Error: {e}")

#     @database_sync_to_async
#     def log_session(self, duration_ms):
#         from monitoring.models import APILog
#         try:
#             APILog.objects.create(
#                 endpoint="WS /ws/live/",
#                 method="WS",
#                 response_time_ms=duration_ms,
#                 status_code=101, 
#                 device_id=self.device_id,
#                 user=self.user if (self.user and self.user.is_authenticated) else None
#             )
#         except Exception as e:
#             print(f"⚠️ Log Session Error: {e}")

#     @database_sync_to_async
#     def log_ws_activity(self):
#         from users.utils import log_activity
#         if self.user and self.user.is_authenticated:
#             log_activity(
#                 user=self.user, 
#                 action="WATCH_LIVE_SCORES", 
#                 details="Connected to Live WebSocket stream", 
#                 request=None 
#             )

#     async def live_score_update(self, event):
#         await self.send(text_data=json.dumps(event, ensure_ascii=False))

#     async def send_initial_data(self):
#         data = await self.get_live_matches()
#         await self.send(text_data=json.dumps({
#             "type": "live_score_update",
#             "data": data
#         }, ensure_ascii=False))

#     @database_sync_to_async
#     def get_live_matches(self):
#         from .models import Fixture
#         from .serializers import FixtureSerializer
#         live_statuses = ['1H', 'HT', '2H', 'ET', 'BT', 'P', 'INT', 'LIVE']
#         fixtures = Fixture.objects.filter(status_short__in=live_statuses).select_related(
#             'league', 'league__country', 'season', 'home_team', 'away_team', 'venue'
#         ).order_by('date')
#         return FixtureSerializer(fixtures, many=True).data


# apps/sports/consumers.py
import json
import time
import asyncio
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings

# Initialize Redis
try:
    redis_client = redis.StrictRedis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
    redis_client.ping()
    print("✅ WebSocket Redis Connection Established")
except Exception as e:
    print(f"❌ WebSocket Redis Connection Failed: {e}")

class LiveScoreConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "live_scores"
        self.start_time = time.time()

        # 1. Identity Extraction
        headers = dict(self.scope['headers'])
        self.device_id = None

        for key, value in headers.items():
            if key.lower() == b'x-device-id':
                self.device_id = value.decode()
                break

        if not self.device_id and self.scope.get('client'):
             self.device_id = f"ip_{self.scope['client'][0]}"

        if not self.device_id:
            self.device_id = "unknown_device"

        print(f"🔌 Connection Attempt: Device={self.device_id}")

        self.user = self.scope.get('user')

        # 2. Register Guest DB
        is_auth = self.user and self.user.is_authenticated
        if self.device_id and not is_auth:
            await self.register_guest_db()

        # 3. Track Presence (Redis)
        await self.track_presence(is_connected=True)

        self.keep_alive_task = asyncio.create_task(self.heartbeat())

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Log the WS connection for authenticated users
        await self.log_ws_activity()

        await self.send_initial_data()

    async def disconnect(self, close_code):
        if hasattr(self, 'keep_alive_task'):
            self.keep_alive_task.cancel()

        duration_ms = (time.time() - self.start_time) * 1000
        await self.log_session(duration_ms)
        await self.track_presence(is_connected=False)
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def heartbeat(self):
        try:
            while True:
                await asyncio.sleep(60)
                await self.track_presence(is_connected=True)
        except asyncio.CancelledError:
            pass

    async def track_presence(self, is_connected):
        timestamp = time.time()
        try:
            if self.user and self.user.is_authenticated:
                key = 'active_users:registered'
                member = str(self.user.id)
            else:
                key = 'active_users:guests'
                member = str(self.device_id)

            if is_connected:
                redis_client.zadd(key, {member: timestamp})
                print(f"✅ Redis Updated: {key} -> {member}")
            else:
                redis_client.zrem(key, member)
        except Exception as e:
            print(f"❌ Redis Track Error: {e}")

    @database_sync_to_async
    def register_guest_db(self):
        from monitoring.models import GuestDevice
        try:
            GuestDevice.objects.get_or_create(device_id=self.device_id)
        except Exception as e:
            print(f"⚠️ DB Register Error: {e}")

    @database_sync_to_async
    def log_session(self, duration_ms):
        from monitoring.models import APILog
        try:
            APILog.objects.create(
                endpoint="WS /ws/live/",
                method="WS",
                response_time_ms=duration_ms,
                status_code=101,
                device_id=self.device_id,
                user=self.user if (self.user and self.user.is_authenticated) else None
            )
        except Exception as e:
            print(f"⚠️ Log Session Error: {e}")

    @database_sync_to_async
    def log_ws_activity(self):
        from users.utils import log_activity
        if self.user and self.user.is_authenticated:
            log_activity(
                user=self.user,
                action="WATCH_LIVE_SCORES",
                details="Connected to Live WebSocket stream",
                request=None
            )

    async def live_score_update(self, event):
        await self.send(text_data=json.dumps(event, ensure_ascii=False))

    async def send_initial_data(self):
        data = await self.get_live_matches()
        await self.send(text_data=json.dumps({
            "type": "live_score_update",
            "data": data
        }, ensure_ascii=False))

    @database_sync_to_async
    def get_live_matches(self):
        from .models import Fixture
        from .serializers import FixtureSerializer

        live_statuses = Fixture.LIVE_STATUSES

        fixtures = Fixture.objects.filter(
            status_short__in=live_statuses
        ).select_related(
            'league', 'league__country', 'season', 'home_team', 'away_team', 'venue'
        ).order_by('date')
        return FixtureSerializer(fixtures, many=True).data