FROM python:3.11-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    postgresql \
    postgresql-client \
    postgresql-common \
    postgis \
    postgresql-postgis \
    nginx \
    supervisor \
    gosu \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend /app/backend
COPY db /app/db
COPY docker /app/docker
COPY frontend /app/frontend
COPY scripts /app/scripts
COPY README.md /app/README.md
COPY .env.example /app/.env.example

RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf || true
COPY docker/nginx.conf /etc/nginx/nginx.conf

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

RUN chmod +x /app/docker/entrypoint.sh /app/docker/init-db.sh

EXPOSE 80

ENTRYPOINT ["/app/docker/entrypoint.sh"]