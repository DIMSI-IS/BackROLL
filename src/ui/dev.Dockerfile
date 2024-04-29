FROM node:14
WORKDIR /app

COPY package*.json ./
RUN npm install --no-optional

COPY . .
CMD ["npm", "run", "serve"]
