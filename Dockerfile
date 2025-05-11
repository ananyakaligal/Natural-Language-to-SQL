# simple single-stage Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 1) Copy & install your Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy the rest of your source
COPY . .

# 3) Ensure your imports work
ENV PYTHONPATH=/app/src \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# 4) Run via shell form so $PORT expands
CMD sh -c "streamlit run src/app.py \
    --server.port \$PORT \
    --server.address 0.0.0.0"
