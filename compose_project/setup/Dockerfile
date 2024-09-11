FROM ubuntu:24.04
WORKDIR /app
RUN apt update && apt install -y openssh-client
COPY . .
CMD ["bash", "src/main.sh"]
