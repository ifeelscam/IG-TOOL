FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV API=7043515654:AAHpJPrcHoh9v0MlOjEgRoT3uwKwIz6ayso

CMD ["python", "bot.py"]
