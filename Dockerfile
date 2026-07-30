FROM python:3.12-slim

ENV SUPERCRONIC_VERSION=v0.2.33

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
       -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

RUN useradd -m -u 1000 -s /bin/bash scheduler

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x scripts/*.sh run.sh && \
    chown -R scheduler:scheduler /app

USER scheduler

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:5000/auth/login || exit 1

CMD ["python", "-c", "from app import create_app; app = create_app(); app.run(host='0.0.0.0', port=5000)"]
