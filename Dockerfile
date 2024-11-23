FROM python:3.10-slim

WORKDIR /app

COPY production/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY production/ .

ARG DISCORD_TOKEN
ARG DISCORD_CHANNEL_ID
ENV DISCORD_TOKEN=$DISCORD_TOKEN
ENV DISCORD_CHANNEL_ID=$DISCORD_CHANNEL_ID

CMD ["python", "live_trading_discord_bot.py"]
