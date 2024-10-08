FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

ENV CONFIG_DIR=/app/config

WORKDIR /app

COPY src/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src .

ENTRYPOINT ["python", "main.py"]
