# syntax=docker/dockerfile:1

### 1) Builder stage ###
FROM python:3.10-slim AS builder

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential sqlite3 libpq-dev default-libmysqlclient-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy & install pinned deps
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

### 2) Final image ###
FROM python:3.10-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app code
COPY . .

# Use Render’s default port
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=$PORT

EXPOSE $PORT

CMD ["streamlit", "run", "src/app.py", "--server.port=$PORT", "--server.address=0.0.0.0"]