FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY src/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src .

ENTRYPOINT ["python", "main.py"]
