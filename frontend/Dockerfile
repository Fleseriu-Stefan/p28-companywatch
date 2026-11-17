FROM node:24-bookworm-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund && chown node:node /app
COPY --chown=node:node . .
USER node
CMD ["sh", "-c", "npm run lint && npm run typecheck && npm run build"]
