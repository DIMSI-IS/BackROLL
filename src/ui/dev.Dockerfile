FROM node:14
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --no-optional

COPY . ./

EXPOSE 8080

CMD ["/bin/bash", "dev.entrypoint.sh"]
