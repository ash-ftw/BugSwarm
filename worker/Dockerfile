FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY bugswarm_worker ./bugswarm_worker

CMD ["celery", "-A", "bugswarm_worker.tasks", "worker", "--loglevel=INFO", "--concurrency=4"]
