#!/usr/bin/env python
"""
Quick test script to verify API-Football connection and fetch basic data.
Run: docker compose exec web python test_api_fetch.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()

import requests
from django.conf import settings
from sports.models import Country, League, Fixture

def test_api_connection():
    """Test if API key works"""
    url = "https://v3.football.api-sports.io/status"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-apisports-key': settings.API_FOOTBALL_KEY
    }
    
    print("Testing API connection...")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("✅ API Key Valid")
        print(f"   Plan: {data['response']['subscription']['plan']}")
        print(f"   Calls today: {data['response']['requests']['current']}/{data['response']['requests']['limit_day']}")
        return True
    else:
        print(f"❌ API Error: {response.status_code}")
        return False

def check_database():
    """Check if data exists in database"""
    print("\nChecking database...")
    countries = Country.objects.count()
    leagues = League.objects.count()
    fixtures = Fixture.objects.count()
    
    print(f"   Countries: {countries}")
    print(f"   Leagues: {leagues}")
    print(f"   Fixtures: {fixtures}")
    
    if countries == 0 and leagues == 0 and fixtures == 0:
        print("❌ Database is empty - boot sequence hasn't run")
        return False
    else:
        print("✅ Data exists in database")
        return True

def fetch_sample_countries():
    """Try fetching countries from API"""
    url = "https://v3.football.api-sports.io/countries"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-apisports-key': settings.API_FOOTBALL_KEY
    }
    
    print("\nFetching sample countries from API...")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json().get('response', [])
        print(f"✅ Fetched {len(data)} countries")
        if data:
            print(f"   Sample: {data[0]['name']}, {data[1]['name']}, {data[2]['name']}...")
        return True
    else:
        print(f"❌ Failed to fetch: {response.status_code}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("API-Football Connection Test")
    print("="*60)
    
    test_api_connection()
    check_database()
    fetch_sample_countries()
    
    print("\n" + "="*60)
    print("To manually trigger data sync, run:")
    print("docker compose exec web python manage.py shell")
    print(">>> from sports.tasks import initial_boot_sequence")
    print(">>> initial_boot_sequence.delay()")
    print("="*60)
