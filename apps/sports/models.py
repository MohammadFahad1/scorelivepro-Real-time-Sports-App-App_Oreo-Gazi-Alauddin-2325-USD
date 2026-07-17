# apps/sports/models.py
from django.db import models
from django.conf import settings

class Timezone(models.Model):
    name = models.CharField(max_length=100, primary_key=True) 
    class Meta:
        ordering = ['name']
    def __str__(self): return self.name

class Country(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    code = models.CharField(max_length=10, blank=True, null=True)
    flag = models.URLField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Countries"
    def __str__(self): return self.name

class Season(models.Model):
    year = models.IntegerField(primary_key=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-year']
    def __str__(self): return str(self.year)

class League(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    logo = models.URLField(blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='leagues', null=True)
    season_year = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)
    has_standings = models.BooleanField(default=False)
    class Meta:
        ordering = ['country', 'name']
    def __str__(self): return self.name

class Venue(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f"{self.name} ({self.city})"

class Team(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    logo = models.URLField(blank=True, null=True)
    code = models.CharField(max_length=10, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True, related_name='teams')
    
    # Establish the relationship to Leagues
    leagues = models.ManyToManyField(League, related_name='teams', blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name

class Standing(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    data = models.JSONField(default=list) 
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('league', 'season')
        ordering = ['-season', 'league']
    def __str__(self): return f"Table: {self.league.name} ({self.season.year})"

class Fixture(models.Model):
    # All statuses considered "in play" by API-Football
    LIVE_STATUSES = ['1H', 'HT', '2H', 'ET', 'BT', 'P', 'INT', 'LIVE', 'SUSP', 'DELAYED', 'BREAK']
    FINISHED_STATUSES = ['FT', 'AET', 'PEN', 'ABD', 'AWD', 'WO']
    UPCOMING_STATUSES = ['NS', 'TBD', 'PST']

    id = models.IntegerField(primary_key=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='fixtures')
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_fixtures')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_fixtures')
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)
    
    referee = models.CharField(max_length=255, blank=True, null=True)
    timezone = models.CharField(max_length=50, default="UTC")
    date = models.DateTimeField(db_index=True) 
    timestamp = models.IntegerField()
    round = models.CharField(max_length=100, blank=True, null=True)

    status_long = models.CharField(max_length=100, blank=True, null=True) 
    status_short = models.CharField(max_length=10, blank=True, null=True, db_index=True) 
    elapsed = models.IntegerField(null=True, blank=True)
    
    periods = models.JSONField(default=dict, blank=True) 
    goals = models.JSONField(default=dict, blank=True)
    score = models.JSONField(default=dict, blank=True)
    events = models.JSONField(default=list, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'id']
        indexes = [
            models.Index(fields=['date', 'status_short']),
        ]

    def __str__(self):
        return f"{self.home_team.name} vs {self.away_team.name} ({self.status_short})"

class FixtureLineup(models.Model):
    fixture = models.OneToOneField(Fixture, on_delete=models.CASCADE, related_name='lineup')
    home = models.JSONField(default=list) 
    away = models.JSONField(default=list) 
    updated_at = models.DateTimeField(auto_now=True)

class FixtureStatistic(models.Model):
    fixture = models.OneToOneField(Fixture, on_delete=models.CASCADE, related_name='statistic')
    data = models.JSONField(default=list) 
    updated_at = models.DateTimeField(auto_now=True)

class HeadToHead(models.Model):
    team_1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='h2h_as_team1')
    team_2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='h2h_as_team2')
    team_1_wins = models.IntegerField(default=0)
    team_2_wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    total_played = models.IntegerField(default=0)
    history = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('team_1', 'team_2')
        indexes = [
            models.Index(fields=['team_1', 'team_2']),
        ]

    def __str__(self):
        return f"{self.team_1.name} vs {self.team_2.name}"

class FavoriteTeam(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_teams')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'team')
        verbose_name = "Favorite Team"
    
    def __str__(self):
        return f"{self.user} -> {self.team.name}"

class FavoriteLeague(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_leagues")
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'league')
        verbose_name = "Favorite League"
    
    def __str__(self):
        return f"{self.user} -> {self.league.name}"