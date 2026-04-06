# Build stage
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# Accept default locale at build time so it gets embedded into the static bundle.
ARG DEFAULT_LOCALE=de
ENV DEFAULT_LOCALE=$DEFAULT_LOCALE

RUN npm run generate

# Production stage
FROM nginx:alpine

COPY --from=builder /app/.output/public /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
