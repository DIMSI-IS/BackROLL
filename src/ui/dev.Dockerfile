# # build stage
# FROM node:14 as build-stage
# WORKDIR /app
# COPY package*.json ./
# RUN npm install --no-optional

# # copy & replace stage
# FROM ubuntu as copyreplace-stage
# RUN rm /bin/sh && ln -s /bin/bash /bin/sh
# RUN apt update -y
# RUN apt install -y gettext-base
# RUN mkdir /app
# WORKDIR /app
# COPY --from=build-stage /app .
# COPY . .
# RUN chmod +x dev.entrypoint.sh
# ENTRYPOINT ["../../development/common/config/ui/env"]
# CMD ["/bin/sh", "dev.entrypoint.sh"]
# # RUN /bin/sh dev.entrypoint.sh

# # serve stage
# FROM node:14 as serve-stage
# RUN mkdir /app
# COPY --from=copyreplace-stage /app /app
# WORKDIR /app
# EXPOSE 8080
# CMD ["npm", "run", "serve"]

# build stage
FROM node:16 as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install --no-optional

# # copy & replace stage
FROM ubuntu:latest
USER root
WORKDIR /home/app
COPY --from=build-stage /app .
RUN rm /bin/sh && ln -s /bin/bash /bin/sh
RUN apt-get update
RUN apt-get -y install curl gnupg gettext-base
RUN curl -sL https://deb.nodesource.com/setup_16.x  | bash -
RUN apt-get -y install nodejs

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8080

CMD ["/bin/sh", "dev.entrypoint.sh"]