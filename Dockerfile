FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
ENV CONFIG_DIR=/app/config

WORKDIR /app

RUN --mount=src=src/requirements.txt,target=/app/requirements.txt \
    pip install --no-cache-dir -r requirements.txt

COPY src .

ENTRYPOINT ["python", "main.py"]
