FROM node:14
WORKDIR /app

# TODO package-lock.json shouldn’t be need but it works better with it.
COPY package*.json ./
RUN npm install --no-optional

COPY . ./

EXPOSE 8080

CMD ["/bin/bash", "dev.entrypoint.sh"]
