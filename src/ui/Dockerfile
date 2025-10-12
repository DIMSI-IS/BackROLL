# build stage
FROM node:14 as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install --no-optional
COPY . .
RUN npm run build

# production stage
FROM nginx as production-stage
WORKDIR /app
COPY --from=build-stage /app/dist ./ui
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh .
CMD ["/bin/sh", "entrypoint.sh", "ui", "/usr/share/nginx/html"]
