FROM python:3.11-slim

# Bothost монтирует исходники в /app, поэтому код и запуск держим вне /app.
WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "main.py"]