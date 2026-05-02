FROM python:3.11-slim

ARG CHROME_VERSION=147.0.7727.138
ARG CHROME_VERSION_MAIN=147
ARG TARGETARCH

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    CHROME_BINARY_PATH=/opt/chrome/chrome-linux64/chrome \
    CHROME_VERSION_MAIN=${CHROME_VERSION_MAIN} \
    SCRAPER_HEADLESS=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcairo2 \
        libcups2 \
        libdbus-1-3 \
        libexpat1 \
        libgbm1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnss3 \
        libpango-1.0-0 \
        libu2f-udev \
        libx11-6 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        unzip \
        wget \
        xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN if [ "$TARGETARCH" = "arm64" ]; then \
        echo "Chrome for Testing Linux builds are only published for amd64." >&2; \
        exit 1; \
    fi \
    && curl -fsSL "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip" -o /tmp/chrome.zip \
    && curl -fsSL "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" -o /tmp/chromedriver.zip \
    && unzip -q /tmp/chrome.zip -d /opt/chrome \
    && unzip -q /tmp/chromedriver.zip -d /opt/chromedriver \
    && ln -s /opt/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && rm /tmp/chrome.zip /tmp/chromedriver.zip \
    && google_major="$("$CHROME_BINARY_PATH" --version | sed -E 's/.* ([0-9]+)\..*/\1/')" \
    && driver_major="$(chromedriver --version | sed -E 's/.* ([0-9]+)\..*/\1/')" \
    && test "$google_major" = "$driver_major"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

ENTRYPOINT ["python", "-m", "loan_scraper"]
