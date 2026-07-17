from django.contrib import admin
from .models import (
    Timezone, Country, Season, League, Venue, Team, Standing, 
    Fixture, FixtureLineup, FixtureStatistic, HeadToHead,
    FavoriteTeam, FavoriteLeague
)

# --- INLINES ---
class FixtureLineupInline(admin.StackedInline):
    model = FixtureLineup
    can_delete = False
    verbose_name_plural = "Lineups"
    classes = ['collapse'] 

class FixtureStatisticInline(admin.StackedInline):
    model = FixtureStatistic
    can_delete = False
    verbose_name_plural = "Statistics"
    classes = ['collapse']

# --- MODEL ADMINS ---

@admin.register(FavoriteTeam)
class FavoriteTeamAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'created_at']
    search_fields = ['user__email', 'team__name']
    list_filter = ['created_at']
    autocomplete_fields = ['user', 'team'] 

@admin.register(FavoriteLeague)
class FavoriteLeagueAdmin(admin.ModelAdmin):
    list_display = ['user', 'league', 'created_at']
    search_fields = ['user__email', 'league__name']
    autocomplete_fields = ['user', 'league']

@admin.register(Timezone)
class TimezoneAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'updated_at']
    search_fields = ['name', 'code']

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ['year', 'updated_at']
    ordering = ['-year']
    # FIX: Added search_fields so autocomplete works
    search_fields = ['year'] 

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'country', 'season_year', 'type', 'has_standings']
    list_filter = ['type', 'season_year', 'has_standings', 'country']
    search_fields = ['name', 'country__name']
    autocomplete_fields = ['country']

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'city']
    search_fields = ['name', 'city']

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'country', 'code', 'venue']
    search_fields = ['name', 'country', 'code']
    autocomplete_fields = ['venue']

@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = ['league', 'season', 'updated_at']
    list_filter = ['season', 'league__country']
    search_fields = ['league__name']
    autocomplete_fields = ['league', 'season']

@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    inlines = [FixtureLineupInline, FixtureStatisticInline]
    list_display = [
        'id', 'date', 'status_short', 
        'home_team', 'away_team', 
        'league', 'score_display'
    ]
    list_filter = ['status_short', 'season', 'league__country']
    search_fields = ['home_team__name', 'away_team__name', 'league__name']
    
    # autocomplete works now because all related Admins have search_fields
    autocomplete_fields = ['league', 'season', 'home_team', 'away_team', 'venue']
    
    ordering = ['-date']

    def score_display(self, obj):
        h = obj.goals.get('home')
        a = obj.goals.get('away')
        if h is not None and a is not None:
            return f"{h}-{a}"
        return "vs"
    score_display.short_description = "Score"

@admin.register(HeadToHead)
class HeadToHeadAdmin(admin.ModelAdmin):
    list_display = ['team_1', 'team_2', 'team_1_wins', 'team_2_wins', 'draws', 'updated_at']
    search_fields = ['team_1__name', 'team_2__name']
    autocomplete_fields = ['team_1', 'team_2']

@admin.register(FixtureLineup)
class FixtureLineupAdmin(admin.ModelAdmin):
    list_display = ['fixture', 'updated_at']
    search_fields = ['fixture__home_team__name', 'fixture__away_team__name']
    autocomplete_fields = ['fixture']

@admin.register(FixtureStatistic)
class FixtureStatisticAdmin(admin.ModelAdmin):
    list_display = ['fixture', 'updated_at']
    search_fields = ['fixture__home_team__name', 'fixture__away_team__name']
    autocomplete_fields = ['fixture']