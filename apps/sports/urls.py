from django.urls import path
from .views import (
    FixtureHeadToHeadView, FixtureWebSocketDocsView, TimezoneListView, SeasonListView, CountryListView, LeagueListView, LeagueDetailView,
    TeamListView, TeamDetailView, VenueListView, StandingListView, StandingDetailView,
    FixtureListView, FixtureDetailView, FixtureLineupsView, FixtureStatisticsView
)

urlpatterns = [
    # DOCUMENTATION ONLY ROUTE
    path('ws/live/', FixtureWebSocketDocsView.as_view(), name='ws-live-docs'),

    path('timezones/', TimezoneListView.as_view(), name='timezone-list'),   
    path('countries/', CountryListView.as_view(), name='country-list'),
    path('seasons/', SeasonListView.as_view(), name='season-list'),
    
    path('leagues/', LeagueListView.as_view(), name='league-list'),
    path('leagues/<int:pk>/', LeagueDetailView.as_view(), name='league-detail'),
    
    path('teams/', TeamListView.as_view(), name='team-list'),
    path('teams/<int:pk>/', TeamDetailView.as_view(), name='team-detail'),
    
    path('venues/', VenueListView.as_view(), name='venue-list'),
    
    path('standings/', StandingListView.as_view(), name='standing-list'),
    path('standings/<int:league_id>/<int:season_year>/', StandingDetailView.as_view(), name='standing-detail'),

    # Fixtures
    path('fixtures/', FixtureListView.as_view(), name='fixture-list'),
    path('fixtures/<int:pk>/', FixtureDetailView.as_view(), name='fixture-detail'),
    
    path('fixtures/<int:pk>/lineups/', FixtureLineupsView.as_view(), name='fixture-lineups'),
    path('fixtures/<int:pk>/statistics/', FixtureStatisticsView.as_view(), name='fixture-statistics'),
    path('fixtures/<int:pk>/h2h/', FixtureHeadToHeadView.as_view(), name='fixture-h2h'),
]