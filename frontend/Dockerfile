FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:stable-alpine
# static files
COPY --from=build /app/build /usr/share/nginx/html
# 🔑 copy the SPA-proxy config
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
