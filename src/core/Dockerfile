FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /usr/src/app

COPY requirements.txt ./

# Download latest listing of available packages=
RUN apt update -y
# # Upgrade already installed packages=
# RUN apt-get -y upgrade
# Install a new package=
RUN apt install -y  libssl-dev \
                        openssh-client \
                        libvirt-dev \
                        python3-pip \
                        python3 \
                        python3-dev \
                        python3-pip \
                        libacl1-dev \
                        libacl1 \
                        libssl-dev \
                        libb2-dev \
                        liblz4-dev \
                        libzstd-dev \
                        build-essential \
                        pkg-config \
                        python3-pkgconfig \
                        nbd-client \
                        qemu-utils \
                        netcat

ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN python3 -m pip install --upgrade pip && \
    pip3 install -U pip setuptools wheel && \
    pip3 install --no-cache-dir borgbackup && \
    pip3 install --no-cache-dir -r requirements.txt

# Set up the ssh folder
RUN mkdir -p /root/.ssh
RUN mkdir -p /root/flower

COPY . .

CMD ["uvicorn", "run=app"]