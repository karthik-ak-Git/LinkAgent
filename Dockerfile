FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/*

ENV CHROME_BIN=/usr/bin/chromium \
    CHROMIUM_BIN=/usr/bin/chromium

WORKDIR /app

COPY linkagent_mcp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY linkagent_mcp/ /app/linkagent_mcp/
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 9222

VOLUME /app/chrome-profile

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=30 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=3)" || exit 1

ENTRYPOINT ["/app/start.sh"]
