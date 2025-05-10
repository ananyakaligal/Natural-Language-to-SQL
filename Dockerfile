# syntax=docker/dockerfile:1

FROM python:3.10-slim AS builder

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

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Let Render know we plan to bind to the port it injects
EXPOSE 10000

# ✅ This is the correct way: use the port Render gives us
CMD sh -c "streamlit run src/app.py --server.port=\${PORT:-8501} --server.address=0.0.0.0"
