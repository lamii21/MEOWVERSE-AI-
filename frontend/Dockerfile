FROM node:22-slim AS base
WORKDIR /app
RUN corepack enable

FROM base AS deps
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# --- Development target (unchanged from before Phase 17) ---
# docker-compose.yml's `frontend` service builds this target and bind-
# mounts the source over it — `next dev` with hot reload.
FROM base AS dev
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["pnpm", "dev"]

# --- Production build stage ---
# `NEXT_PUBLIC_*` variables are inlined into the client JS bundle at
# *build* time, not read at container startup — so the real backend URL
# has to be supplied as a build arg, not just a runtime `-e`/env_file
# entry (see docker-compose.prod.yml and README.md's deployment
# section).
FROM base AS builder
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

# --- Production runtime ---
# Next.js's `output: "standalone"` (next.config.ts) traces only the
# node_modules files each page actually needs into
# `.next/standalone/`, so this stage never installs the full
# node_modules tree — a real image-size optimization, not just fewer
# build layers.
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

# `node:22-slim` already ships a non-root `node` user (uid 1000) —
# reused rather than creating a second one, which fails with "UID 1000
# is not unique" (found by actually building this image, not assumed).
COPY --from=builder /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
USER node

EXPOSE 3000
ENV PORT=3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/', r => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
