FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq && \
    apt-get install -y python3 python3-pip aria2 -qq && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip3 install --no-cache-dir kurigram tgcrypto aiohttp nest_asyncio

COPY . /app

EXPOSE 8080

CMD ["python3", "bot.py"]
