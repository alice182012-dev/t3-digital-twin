FROM node:22-alpine AS build
RUN apk add --no-cache git
WORKDIR /app
COPY package.json package-lock.json ./
# Upstream's lockfile isn't quite in sync with package.json as pinned (npm ci
# refuses); npm install tolerates that while still resolving from the lockfile.
RUN npm install
COPY . .
# webpack.common.js embeds `git rev-parse HEAD` in the build and this tree
# is vendored without a .git dir (see PINNED_COMMIT.md for the real commit).
RUN git init -q && git add -A && git -c user.email=build@local -c user.name=build commit -q -m vendor
# webpack.common.js swaps config.js for config-local.js automatically when present.
RUN cp config-local.js.example config-local.js
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
