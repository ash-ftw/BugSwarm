FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic
COPY docker-entrypoint.sh /usr/local/bin/bugswarm-backend
RUN sed -i 's/\r$//' /usr/local/bin/bugswarm-backend && chmod +x /usr/local/bin/bugswarm-backend

EXPOSE 8000

ENTRYPOINT ["bugswarm-backend"]
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
