# Pull official base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Prevents Python from writing pyc files to disc
    # Prevents Python from buffering stdout and stderr
    DJANGO_SETTINGS_MODULE=config.settings.prod

# Install system dependencies
# netcat-openbsd is used for the entrypoint script (nc command)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Copy entrypoint.sh
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create a directory for static files
RUN mkdir -p /app/staticfiles && mkdir -p /app/mediafiles

# Create a non-root user 'django' and switch to it for security
RUN addgroup --system django && adduser --system --group django
RUN chown -R django:django /app

USER django

# Run entrypoint
ENTRYPOINT ["/entrypoint.sh"]