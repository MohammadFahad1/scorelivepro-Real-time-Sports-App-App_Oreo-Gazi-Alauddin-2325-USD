import textwrap
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404
from rest_framework import generics, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny

# Swagger / Documentation Imports
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse, extend_schema_view
from drf_spectacular.types import OpenApiTypes

from users.permissions import IsOwnerOrAdmin
from users.utils import log_activity
from .tasks import fetch_and_update_h2h_record
from .models import (HeadToHead, Timezone, Season, Country, League, Team, Venue, Standing, 
                     Fixture, FixtureLineup, FixtureStatistic, FavoriteTeam, FavoriteLeague)
from .serializers import (HeadToHeadSerializer, TimezoneSerializer, SeasonSerializer, CountrySerializer, 
                          LeagueSerializer, TeamSerializer, VenueSerializer, 
                          StandingSerializer, FixtureSerializer, 
                          FixtureLineupSerializer, FixtureStatisticSerializer,
                          FavoriteTeamSerializer, FavoriteLeagueSerializer, FavoriteIDSerializer)

User = get_user_model()

# =========================================================
#                    PAGINATION CONFIG
# =========================================================

class StandardPagination(PageNumberPagination):
    """
    Standard pagination for returning 100 items per page.
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

# =========================================================
#                    ACTIVITY TRACKING MIXIN
# =========================================================

class ActivityLogMixin:
    """
    Mixin to automatically log when an authenticated user views a specific resource.
    """
    activity_action = "VIEW_RESOURCE"
    
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed resource ID: {kwargs.get('pk') or kwargs.get('league_id')}"

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        if request.user and request.user.is_authenticated:
            details = self.get_activity_details(request, *args, **kwargs)
            # Fire and forget logging
            log_activity(request.user, self.activity_action, details, request=request)
        return response


# =========================================================
#                    WEBSOCKET DOCS
# =========================================================

@extend_schema(
    tags=['Fixtures'],
    summary="🔴 WebSocket: Live Score Stream",
    description=textwrap.dedent("""
        **Connect via:** `wss://<base_url>/ws/live/`
        
        Establishes a real-time WebSocket connection for live match updates.
        
        **Protocol Flow:**
        1. **Connect:** Client establishes connection.
        2. **Initial State:** Server immediately sends the full list of currently live matches.
        3. **Updates:** Server pushes updates (JSON) whenever scores, time, or status change.
    """),
    request=None,
    responses={
        101: OpenApiResponse(description="Switching Protocols (Connection Accepted)"),
        426: OpenApiResponse(description="Upgrade Required (Use a WebSocket Client)")
    }
)
class FixtureWebSocketDocsView(APIView):
    permission_classes = [IsOwnerOrAdmin] 

    def get(self, request, *args, **kwargs):
        return Response(
            {"detail": "Please connect via WebSocket (ws://...)"}, 
            status=status.HTTP_426_UPGRADE_REQUIRED
        )


# =========================================================
#                    CORE RESOURCES
# =========================================================

@extend_schema(tags=['Core Resources'], summary="List Timezones")
class TimezoneListView(generics.ListAPIView):
    queryset = Timezone.objects.all()
    serializer_class = TimezoneSerializer
    @method_decorator(cache_page(60 * 60 * 24 * 7))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Core Resources'], summary="List Countries")
class CountryListView(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    search_fields = ['name', 'code']
    @method_decorator(cache_page(60 * 60 * 24))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Core Resources'], summary="List Available Seasons")
class SeasonListView(generics.ListAPIView):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    ordering = ['-year']
    @method_decorator(cache_page(60 * 60 * 24))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Core Resources'], summary="List Venues")
class VenueListView(generics.ListAPIView):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    search_fields = ['name', 'city']
    @method_decorator(cache_page(60 * 60 * 24))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)


# =========================================================
#                    LEAGUES & TEAMS
# =========================================================

@extend_schema(tags=['Leagues'], summary="List Leagues", description="Searchable list of leagues.")
class LeagueListView(generics.ListAPIView):
    queryset = League.objects.select_related('country').all()
    serializer_class = LeagueSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['country__name', 'type', 'has_standings']
    search_fields = ['name', 'country__name']
    
    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Leagues'], summary="Get League Details")
class LeagueDetailView(generics.RetrieveAPIView):
    queryset = League.objects.select_related('country').all()
    serializer_class = LeagueSerializer
    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(
    tags=['Teams'], 
    summary="List Teams", 
    description="Search teams or filter by country and league. Example: `?leagues=39` (Premier League)",
    parameters=[
        OpenApiParameter(name='leagues', description='Filter by League ID', required=False, type=int),
    ]
)
class TeamListView(generics.ListAPIView):
    serializer_class = TeamSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['country', 'leagues']  
    search_fields = ['name', 'country'] 
    ordering_fields = ['name', 'country']
    ordering = ['name']
    
    def get_queryset(self):
        return Team.objects.all()

    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Teams'], summary="Get Team Details")
class TeamDetailView(generics.RetrieveAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)


# =========================================================
#                    STANDINGS
# =========================================================

@extend_schema(tags=['Standings'], summary="List Standings")
class StandingListView(generics.ListAPIView):
    serializer_class = StandingSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['league', 'season']
    search_fields = ['league__name', 'league__country__name']
    ordering_fields = ['season', 'league__name']
    ordering = ['-season', 'league__name'] 

    def get_queryset(self): 
        return Standing.objects.select_related('league', 'season').all()

    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

@extend_schema(tags=['Standings'], summary="Get Standing Details")
class StandingDetailView(generics.RetrieveAPIView):
    serializer_class = StandingSerializer
    def get_object(self):
        return get_object_or_404(
            Standing.objects.select_related('league', 'season'),
            league_id=self.kwargs.get('league_id'),
            season_id=self.kwargs.get('season_year')
        )
    @method_decorator(cache_page(60 * 60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)


# =========================================================
#                    FIXTURES
# =========================================================
from django.utils import timezone
from datetime import timedelta
@extend_schema(
    tags=['Fixtures'], 
    summary="List Fixtures",
    description="Retrieve fixtures filtered by status and league. Pagination enabled (100 per page).",
    parameters=[
        OpenApiParameter(
            name='status', 
            description='Filter by match status group: "live", "finished", "upcoming"', 
            required=False, 
            type=str,
            enum=['live', 'finished', 'upcoming']
        ),
    ]
)
class FixtureListView(generics.ListAPIView):
    serializer_class = FixtureSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
 
    filterset_fields = ['league', 'season']
    search_fields = ['home_team__name', 'away_team__name', 'league__name']
 
    LIVE_STATUSES      = Fixture.LIVE_STATUSES
    FINISHED_STATUSES  = Fixture.FINISHED_STATUSES
    UPCOMING_STATUSES  = Fixture.UPCOMING_STATUSES
 
    def get_queryset(self):
        queryset = Fixture.objects.select_related(
            'league', 'league__country', 'season', 'home_team', 'away_team', 'venue'
        ).all()
 
        status_param = self.request.query_params.get('status')
        live_param   = self.request.query_params.get('live')
 
        if status_param == 'live' or live_param == 'true':
            queryset = queryset.filter(
                status_short__in=self.LIVE_STATUSES
            ).order_by('date')
 
        elif status_param == 'finished':
            queryset = queryset.filter(
                status_short__in=self.FINISHED_STATUSES
            ).order_by('-date')
 
        elif status_param == 'upcoming':
            now = timezone.now()
            queryset = queryset.filter(
                status_short__in=self.UPCOMING_STATUSES,
                date__gte=now - timedelta(hours=2),
            ).order_by('date')
 
        else:
            queryset = queryset.order_by('date')
 
        return queryset

@extend_schema(tags=['Fixtures'], summary="Get Fixture Details")
class FixtureDetailView(ActivityLogMixin, generics.RetrieveAPIView):
    queryset = Fixture.objects.select_related(
        'league', 'league__country', 'season', 'home_team', 'away_team', 'venue'
    ).all()
    serializer_class = FixtureSerializer
    activity_action = "VIEW_FIXTURE_DETAILS"
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed match overview for Fixture {kwargs.get('pk')}"

@extend_schema(tags=['Fixture Details'], summary="Get Lineups")
class FixtureLineupsView(ActivityLogMixin, generics.RetrieveAPIView):
    serializer_class = FixtureLineupSerializer
    activity_action = "VIEW_FIXTURE_LINEUPS"
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed lineups for Fixture {kwargs.get('pk')}"
    
    @method_decorator(cache_page(60 * 10))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

    def get_object(self):
        obj, _ = FixtureLineup.objects.get_or_create(fixture_id=self.kwargs['pk'])
        return obj

@extend_schema(tags=['Fixture Details'], summary="Get Statistics")
class FixtureStatisticsView(ActivityLogMixin, generics.RetrieveAPIView):
    serializer_class = FixtureStatisticSerializer
    activity_action = "VIEW_FIXTURE_STATS"
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed statistics for Fixture {kwargs.get('pk')}"

    @method_decorator(cache_page(60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)

    def get_object(self):
        obj, _ = FixtureStatistic.objects.get_or_create(fixture_id=self.kwargs['pk'])
        return obj

@extend_schema(tags=['Fixture Details'], summary="Get Head-to-Head")
class FixtureHeadToHeadView(ActivityLogMixin, generics.RetrieveAPIView):
    serializer_class = HeadToHeadSerializer
    activity_action = "VIEW_FIXTURE_H2H"
    def get_activity_details(self, request, *args, **kwargs):
        return f"Viewed Head-to-Head stats for Fixture {kwargs.get('pk')}"

    @method_decorator(cache_page(60))
    def dispatch(self, *args, **kwargs): return super().dispatch(*args, **kwargs)
    
    def get_object(self):
        fixture_id = self.kwargs['pk']
        fixture = get_object_or_404(Fixture, id=fixture_id)
        t1 = fixture.home_team
        t2 = fixture.away_team
        
        if t1.id < t2.id:
            team_1, team_2 = t1, t2
        else:
            team_1, team_2 = t2, t1

        try:
            return HeadToHead.objects.get(team_1=team_1, team_2=team_2)
        except HeadToHead.DoesNotExist:
            print(f"H2H missing for {team_1.name} vs {team_2.name}. Fetching now...")
            fetch_and_update_h2h_record(team_1, team_2)
            return get_object_or_404(HeadToHead, team_1=team_1, team_2=team_2)


# =========================================================
#                    USER FAVORITES
# =========================================================

@extend_schema_view(
    get=extend_schema(
        tags=['User Favorites'],
        summary="List User Favorites",
        description="Get a list of favorite 'teams' or 'leagues' for a specific user.",
        parameters=[
            OpenApiParameter(
                name='type', 
                location=OpenApiParameter.PATH, 
                description="Type of favorite to retrieve ('teams' or 'leagues')", 
                required=True, 
                type=str, 
                enum=['teams', 'leagues']
            )
        ],
        responses={
            200: OpenApiResponse(
                description="List of favorites (Format depends on 'type' parameter)",
                examples=[
                    OpenApiExample("Teams Example", value=[{"id": 1, "team_details": {"name": "Arsenal"}}]),
                    OpenApiExample("Leagues Example", value=[{"id": 1, "league_details": {"name": "Premier League"}}])
                ]
            )
        }
    ),
    post=extend_schema(
        tags=['User Favorites'],
        summary="Add to Favorites",
        description="Add a specific Team ID or League ID to the user's favorites.",
        request=FavoriteIDSerializer,
        parameters=[
            OpenApiParameter(
                name='type', 
                location=OpenApiParameter.PATH, 
                enum=['teams', 'leagues']
            )
        ],
        responses={
            201: OpenApiResponse(description="Successfully added"),
            400: OpenApiResponse(description="Invalid ID or Type")
        }
    ),
    delete=extend_schema(
        tags=['User Favorites'],
        summary="Remove from Favorites",
        description="Delete a favorite item by the Item ID (Team ID or League ID), NOT the favorite record ID.",
        parameters=[
            OpenApiParameter(name='type', location=OpenApiParameter.PATH, enum=['teams', 'leagues']),
            OpenApiParameter(name='item_id', location=OpenApiParameter.PATH, type=int, description="The ID of the Team or League to remove")
        ],
        responses={
            204: OpenApiResponse(description="Successfully deleted"),
            404: OpenApiResponse(description="Favorite not found")
        }
    )
)
class ManageUserFavoritesView(APIView):
    permission_classes = [IsOwnerOrAdmin]

    def _get_type_config(self, type_name):
        if type_name == 'teams':
            return {
                'model': FavoriteTeam,
                'target_model': Team,
                'serializer': FavoriteTeamSerializer,
                'field': 'team' 
            }
        elif type_name == 'leagues':
            return {
                'model': FavoriteLeague,
                'target_model': League,
                'serializer': FavoriteLeagueSerializer,
                'field': 'league'
            }
        return None

    def get(self, request, user_id, type):
        config = self._get_type_config(type)
        if not config:
            return Response({"error": "Invalid type. Use 'teams' or 'leagues'."}, status=400)

        target_user = get_object_or_404(User, pk=user_id)
        queryset = config['model'].objects.filter(user=target_user)
        serializer = config['serializer'](queryset, many=True)
        return Response(serializer.data)

    def post(self, request, user_id, type):
        config = self._get_type_config(type)
        if not config:
            return Response({"error": "Invalid type"}, status=400)
        
        target_user = get_object_or_404(User, pk=user_id)

        serializer = FavoriteIDSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        obj_id = serializer.validated_data['id']
        target_obj = get_object_or_404(config['target_model'], pk=obj_id)

        create_kwargs = {'user': target_user, config['field']: target_obj}
        obj, created = config['model'].objects.get_or_create(**create_kwargs)

        if created:
            # Log this action to the request user
            log_activity(request.user, "ADD_FAVORITE", f"Added {type[:-1].capitalize()} ID {obj_id} to favorites", request)
            return Response({"status": "Added", "id": obj_id}, status=status.HTTP_201_CREATED)
        return Response({"status": "Already exists", "id": obj_id}, status=status.HTTP_200_OK)

    def delete(self, request, user_id, type, item_id):
        config = self._get_type_config(type)
        if not config:
            return Response({"error": "Invalid type"}, status=400)
        
        target_user = get_object_or_404(User, pk=user_id)

        filter_kwargs = {'user': target_user, f"{config['field']}_id": item_id}
        deleted_count, _ = config['model'].objects.filter(**filter_kwargs).delete()

        if deleted_count > 0:
            # Log this action to the request user
            log_activity(request.user, "REMOVE_FAVORITE", f"Removed {type[:-1].capitalize()} ID {item_id} from favorites", request)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)