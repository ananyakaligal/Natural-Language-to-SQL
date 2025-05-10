# syntax=docker/dockerfile:1

FROM python:3.10-slim AS builder

# Install Node.js (needed for pydeck and some frontend rendering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential sqlite3 libpq-dev default-libmysqlclient-dev gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

FROM python:3.10-slim

WORKDIR /app

# Copy packages
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

# Let Render inject port
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

EXPOSE 8080

# Use $PORT injected by Render
CMD ["streamlit", "run", "src/app.py", "--server.port=$PORT", "--server.address=0.0.0.0"]
