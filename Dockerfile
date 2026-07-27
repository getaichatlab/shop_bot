FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist the database and logs outside the image layer.
RUN mkdir -p /data /app/logs
ENV DB_PATH=/data/shop.db \
    LOG_DIR=/app/logs
VOLUME ["/data"]

# Run as a non-root user.
RUN useradd --create-home --uid 1000 botuser \
    && chown -R botuser:botuser /app /data
USER botuser

# Only needed in webhook mode; harmless in polling mode.
EXPOSE 8080

# Graceful shutdown: bot.py handles SIGTERM and closes storage + session.
STOPSIGNAL SIGTERM

CMD ["python", "bot.py"]
