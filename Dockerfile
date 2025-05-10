# syntax=docker/dockerfile:1

### ---- Builder Stage ---- ###
FROM python:3.10-slim AS builder

# Install dependencies for building Python packages and DB support
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential sqlite3 libpq-dev default-libmysqlclient-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy full app source code
COPY . .

### ---- Final Image ---- ###
FROM python:3.10-slim

WORKDIR /app

# Copy installed packages and app code from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

# Let Render handle dynamic port via $PORT
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

EXPOSE 8080

# ✅ Use shell so $PORT is expanded at runtime
CMD ["streamlit", "run", "src/app.py", "--server.port=$PORT", "--server.address=0.0.0.0"]
