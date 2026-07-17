# Deployment Guide

## Prerequisites

### 1. Firebase Credentials Setup

Push notifications require Firebase Cloud Messaging (FCM) credentials.

**Steps:**

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** → **Service Accounts**
4. Click **Generate New Private Key**
5. Download the JSON file
6. Rename it to `firebase-credentials.json`
7. Place it in the project root directory (same level as `docker-compose.yml`)

**Important:** This file contains sensitive credentials and is automatically ignored by Git. Each deployment environment (dev, staging, production) needs its own copy.

### 2. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Django secret key
- `API_FOOTBALL_KEY` - API-Football subscription key
- `CELERY_BROKER_URL` - Redis URL for Celery
- `CLOUDINARY_*` - Cloudinary credentials for media storage
- Firebase credentials are loaded from `firebase-credentials.json` file

## Deployment Steps

### Initial Setup

```bash
# 1. Ensure firebase-credentials.json exists
ls -la firebase-credentials.json

# 2. Build and start services
docker compose up -d --build

# 3. Run migrations (only on web service)
docker compose exec web python manage.py migrate

# 4. Create superuser (optional)
docker compose exec web python manage.py createsuperuser

# 5. Trigger initial data sync
docker compose exec web python manage.py shell -c "from sports.tasks import initial_boot_sequence; initial_boot_sequence.delay()"
```

### Verify Deployment

```bash
# Check all services are running
docker compose ps

# Check logs
docker compose logs web
docker compose logs celery
docker compose logs celery-beat

# Verify Firebase is initialized
docker compose logs web | grep Firebase
# Should see: "Firebase Admin SDK Initialized" (not "Firebase Initialization Failed")

# Check data was fetched
docker compose exec web python manage.py shell -c "
from sports.models import Country, League, Fixture
print(f'Countries: {Country.objects.count()}')
print(f'Leagues: {League.objects.count()}')
print(f'Fixtures: {Fixture.objects.count()}')
"
```

## Troubleshooting

### Firebase Credentials Not Found

**Symptom:** Logs show `Firebase Initialization Failed: [Errno 2] No such file or directory: '/app/firebase-credentials.json'`

**Solution:**
1. Verify file exists: `ls -la firebase-credentials.json`
2. Check file is readable: `cat firebase-credentials.json` (should show JSON)
3. Restart containers: `docker compose restart`
4. Check inside container: `docker compose exec web ls -la /app/firebase-credentials.json`

### Database Connection Issues

**Symptom:** `Connection refused` or `could not translate host name "db" to address`

**Solution:**
- Verify `SQL_HOST=db` and `SQL_PORT=5432` in `.env`
- Containers use internal Docker network ports, not host-mapped ports
- Ensure `DATABASE_URL` uses `db:5432` not `localhost:5433`

### No Fixture Data

**Symptom:** APIs return empty results despite running successfully

**Solution:**
1. Check if boot sequence ran: `docker compose logs celery | grep "Boot sequence"`
2. Manually trigger: `docker compose exec web python manage.py shell -c "from sports.tasks import fetch_upcoming_fixtures; fetch_upcoming_fixtures.delay(days=7)"`
3. Wait a few minutes for Celery to process the task
4. Check logs: `docker compose logs -f celery | grep fetch_upcoming`

### Notifications Not Sending

**Symptom:** Notifications logged to database but not received on devices

**Causes:**
1. Firebase credentials missing → runs in simulator mode
2. Devices not registered → no FCM tokens in database
3. Users not subscribed to topics → check UserDevice model

**Solution:**
- Fix Firebase credentials (see above)
- Register device via `/notifications/devices/register/` endpoint
- Subscribe to topics: teams, leagues, matches

## Production Checklist

- [ ] `firebase-credentials.json` uploaded to server
- [ ] `.env` configured with production values
- [ ] `DEBUG=False` in `.env`
- [ ] `ALLOWED_HOSTS` set correctly
- [ ] Database backups configured
- [ ] SSL/TLS certificates installed (nginx)
- [ ] Firewall rules configured
- [ ] Monitoring/logging enabled
- [ ] Auto-restart on failure (systemd or docker restart policy)

## Maintenance

### Update Application Code

```bash
git pull
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
```

### View Logs

```bash
docker compose logs -f              # All services
docker compose logs -f web          # Just web
docker compose logs -f celery       # Just celery worker
docker compose logs -f celery-beat  # Just celery scheduler
```

### Restart Services

```bash
docker compose restart              # All services
docker compose restart web          # Just web
docker compose restart celery       # Just celery
```

### Database Backup

```bash
docker compose exec db pg_dump -U postgres scorelivepro > backup_$(date +%Y%m%d).sql
```

### Clear Redis Cache

```bash
docker compose exec redis redis-cli FLUSHALL
```
