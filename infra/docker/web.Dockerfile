FROM node:22-bookworm-slim

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /workspace/apps/web
RUN npm install --global pnpm@10.34.5
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY apps/web/ ./
EXPOSE 3000
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]
