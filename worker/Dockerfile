FROM python:3.12-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY bugswarm_worker ./bugswarm_worker
COPY docker-entrypoint.sh /usr/local/bin/bugswarm-worker
RUN sed -i 's/\r$//' /usr/local/bin/bugswarm-worker && chmod +x /usr/local/bin/bugswarm-worker

CMD ["bugswarm-worker"]
