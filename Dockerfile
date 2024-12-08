FROM python:3.10-slim

WORKDIR /app

COPY production/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY production/ .

ARG DISCORD_TOKEN
ARG DISCORD_CHANNEL_ID
ARG XTB_USER_ID
ARG XTB_PASSWORD
ENV DISCORD_TOKEN=$DISCORD_TOKEN
ENV DISCORD_CHANNEL_ID=$DISCORD_CHANNEL_ID
ENV XTB_USER_ID=$XTB_USER_ID
ENV XTB_PASSWORD=$XTB_PASSWORD

CMD ["python", "claude.py"]
