FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY web/package.json ./
RUN npm install

COPY web/ .

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

RUN useradd -m -u 1000 app && chown -R app:app /app
USER app

ENV NODE_ENV=production
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:3000/api/health || exit 1

CMD ["npm", "start"]
