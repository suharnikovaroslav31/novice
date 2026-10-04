FROM node:20-alpine

# /app is replaced by a git mount at runtime, so the server lives outside it.
WORKDIR /usr/src/app

COPY . .

RUN npm install --prefix /opt/novice telegram@2.26.22 --omit=dev --ignore-scripts \
  && mkdir -p /app/data
ENV NODE_PATH=/opt/novice/node_modules
ENV DATA_DIR=/app/data

EXPOSE 8000

ENTRYPOINT ["node", "/usr/src/app/main.py"]
CMD ["node", "/usr/src/app/main.py"]