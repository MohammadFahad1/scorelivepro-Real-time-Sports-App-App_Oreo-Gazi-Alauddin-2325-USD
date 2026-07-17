from rest_framework import serializers
from .models import (Season, Country, League, Team, Venue, Standing, 
                     Fixture, Timezone, FixtureLineup, FixtureStatistic, HeadToHead,
                     FavoriteTeam, FavoriteLeague)

class TimezoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timezone
        fields = ['name']

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'city']

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'logo']

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['name', 'code', 'flag']

class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ['year']

class LeagueSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    class Meta:
        model = League
        fields = ['id', 'name', 'country', 'logo', 'season_year']

class StandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Standing
        fields = ['league', 'season', 'data', 'updated_at']

# --- FIXTURE SERIALIZERS ---

class FixtureSerializer(serializers.ModelSerializer):
    """
    Lightweight Serializer for Lists & WebSocket.
    """
    league = LeagueSerializer(read_only=True)
    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)
    venue = VenueSerializer(read_only=True)
    season = SeasonSerializer(read_only=True)

    class Meta:
        model = Fixture
        fields = [
            'id', 'date', 'timestamp', 'timezone', 'referee', 'round',
            'status_long', 'status_short', 'elapsed',
            'venue', 'league', 'season', 'home_team', 'away_team',
            'goals', 'score', 'periods', 'events'
        ]

class FixtureLineupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixtureLineup
        fields = ['home', 'away', 'updated_at']

class FixtureStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixtureStatistic
        fields = ['data', 'updated_at']

class HeadToHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeadToHead
        fields = [
            'team_1', 'team_2', 
            'team_1_wins', 'team_2_wins', 'draws', 
            'total_played', 'history', 'updated_at'
        ]


#############
class FavoriteIDSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="The ID of the Team or League you want to favorite.")


class FavoriteTeamSerializer(serializers.ModelSerializer):
    team_details = TeamSerializer(source='team', read_only=True)

    class Meta:
        model = FavoriteTeam
        fields = ['id', 'user', 'team_details', 'created_at']


class FavoriteLeagueSerializer(serializers.ModelSerializer):
    league_details = LeagueSerializer(source='league', read_only=True)

    class Meta:
        model = FavoriteLeague
        fields = ['id', 'user', 'league_details', 'created_at']