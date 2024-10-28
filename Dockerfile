FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV API=<your_telegram_bot_token>

CMD ["python", "bot.py"]
