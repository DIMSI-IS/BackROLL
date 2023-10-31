FROM node:14
WORKDIR /app

COPY package.json package-lock.json ./
# In case of the "vue-cli-service: not found",
# remove "--no-optional" and build to reset some caches
# and then you can undo this change.
RUN npm install --no-optional

COPY . ./

EXPOSE 8080

CMD ["/bin/bash", "dev.entrypoint.sh"]
