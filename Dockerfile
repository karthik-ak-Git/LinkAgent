FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Chromium and dependencies
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
    && rm -rf /var/lib/apt/lists/*

# Tell Chromium where to find the binary
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMIUM_BIN=/usr/bin/chromium

WORKDIR /app

# Install Python dependencies
COPY linkagent_mcp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the package
COPY linkagent_mcp/ /app/linkagent_mcp/

# Copy startup script
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# CDP port
EXPOSE 9222

# Chrome profile persistence (mount at runtime)
VOLUME /app/chrome-profile

ENTRYPOINT ["/app/start.sh"]
