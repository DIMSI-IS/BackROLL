FROM ubuntu:24.10

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Download latest listing of available packages=
RUN apt update -y
# # Upgrade already installed packages=
# RUN apt-get -y upgrade
# Install a new package=
RUN apt install -y \
    libssl-dev \
    openssh-client \
    libvirt-dev \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    libacl1-dev \
    libacl1 \
    libb2-dev \
    liblz4-dev \
    libzstd-dev \
    build-essential \
    pkg-config \
    python3-pkgconfig \
    nbd-client \
    qemu-utils \
    netcat-openbsd \
    borgbackup

ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN python3 -m venv ./venv
RUN ./venv/bin/python3 -m pip install pip==24.0

COPY requirements.txt ./
RUN ./venv/bin/pip3 install --no-cache-dir -r requirements.txt

# Set up the ssh folder
RUN mkdir -p /root/.ssh
RUN mkdir -p /root/flower

WORKDIR /app/src

COPY . .

CMD ["uvicorn", "run=app"]
