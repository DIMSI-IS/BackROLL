# build stage
FROM node:14 as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install --no-optional
COPY . .
RUN npm run build

# production stage
FROM nginx as production-stage
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build-stage /app/dist /usr/share/nginx/html

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 80
CMD ["/bin/sh", "entrypoint.sh"]