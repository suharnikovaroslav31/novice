FROM node:20-alpine

WORKDIR /app

COPY . .

RUN mkdir -p /app/data
ENV DATA_DIR=/app/data

EXPOSE 8000

CMD ["node", "main.py"]