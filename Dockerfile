FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    INVENTORY_DB_PATH=/data/inventory.db

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data && chown -R app:app /app /data

USER app

EXPOSE 5003

CMD ["gunicorn", "--bind", "0.0.0.0:5003", "app:app"]
