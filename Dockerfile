FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV API=6949336800:AAF1Sjv-EXSbkkno1HKCGzA9HMtUhM7N5FE

CMD ["python", "bot.py"]
