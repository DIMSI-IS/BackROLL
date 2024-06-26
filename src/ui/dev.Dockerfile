FROM node:14
WORKDIR /app

COPY package*.json ./
RUN npm install --no-optional

COPY . .
CMD [ "bash", "dev.entrypoint.sh"  ]
