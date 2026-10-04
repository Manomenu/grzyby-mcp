# Build context is the SOLUTION ROOT, matching the server image so both build from one
# place:
#
#   podman build -f grzyby_web/Dockerfile -t operat-web .

FROM docker.io/library/node:24-alpine AS builder

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

WORKDIR /app

# pnpm 11 reads its settings out of pnpm-workspace.yaml, so it belongs in the install
# layer alongside the manifest and the lockfile.
COPY grzyby_web/package.json grzyby_web/pnpm-lock.yaml grzyby_web/pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY grzyby_web/ ./
# `pnpm build` is `tsc --noEmit && vite build`: a type error fails the image rather than
# the deploy.
RUN pnpm build


FROM docker.io/nginxinc/nginx-unprivileged:1.29-alpine

# At container start the image's entrypoint runs envsubst over /etc/nginx/templates/ and
# writes the result to /etc/nginx/conf.d/ — which is how ${API_UPSTREAM} becomes a real
# address without rebuilding. The filter narrows that to a whitelist of two: without it
# envsubst expands every name present in the environment, and nginx's own $host and
# $scheme survive only as long as nothing is named after them.
ENV NGINX_ENVSUBST_FILTER="^(API_UPSTREAM|NGINX_LOCAL_RESOLVERS)$"
# Makes the entrypoint export NGINX_LOCAL_RESOLVERS: the nameservers from /etc/resolv.conf,
# which nginx needs to look the API's name up again after the server is recreated.
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1
# Matches the service name in compose; the cluster overrides it with the Service address.
ENV API_UPSTREAM="http://server:6210"

COPY --from=builder /app/dist /usr/share/nginx/html
COPY grzyby_web/nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080
