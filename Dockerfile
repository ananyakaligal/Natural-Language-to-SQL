# at the very top of your Dockerfile:
# enable BuildKit features
# syntax=docker/dockerfile:1.4

FROM python:3.10-slim AS builder
WORKDIR /app

# copy only requirements, so they’re cached separately
COPY requirements.txt .

# use a pip cache mount (requires DOCKER_BUILDKIT=1)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.10-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin           /usr/local/bin
COPY . .

ENV PYTHONPATH=/app/src \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 10000
CMD sh -c "streamlit run src/app.py --server.port \$PORT --server.address 0.0.0.0"