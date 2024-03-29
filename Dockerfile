FROM python:3.10.12-bullseye

ARG BOT_TOKEN
ARG REDIS_IP
ARG REDIS_PORT
ARG REDIS_PASSWORD
ARG API_KEY
ARG WSS_URL
ARG API_URL

ENV BOT_TOKEN=${BOT_TOKEN}
ENV REDIS_IP=${REDIS_IP}
ENV REDIS_PORT=${REDIS_PORT}
ENV REDIS_PASSWORD=${REDIS_PASSWORD}
ENV API_KEY=${API_KEY}
ENV WSS_URL=${WSS_URL}
ENV API_URL=${API_URL}

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

CMD ["python", "/app/main.py"]
