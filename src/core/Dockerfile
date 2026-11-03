FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Download latest listing of available packages=
RUN apt update -y
# # Upgrade already installed packages=
# RUN apt-get -y upgrade
# Install a new package=
RUN apt install -y \
    openssh-client \
    libvirt-dev \
    build-essential \
    nbd-client \
    qemu-utils \
    netcat-openbsd

ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

########################################################

# Based on the Borg documentation.

RUN apt install -y \
    python3 python3-dev python3-pip python3-virtualenv \
    libacl1-dev libacl1 \
    libssl-dev \
    liblz4-dev libzstd-dev libxxhash-dev \
    build-essential \
    pkg-config python3-pkgconfig

RUN virtualenv --python=python3 python-env
ENV PATH="/app/python-env/bin:$PATH"

RUN pip install -U pip setuptools wheel && \
    pip install pkgconfig

########################################################

COPY python_project/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

########################################################

# Reads the files of a VM disk without mounting it (file browser of the backups).
# The kernel is needed by the small virtual machine that libguestfs starts to read the disk.
RUN apt install -y --no-install-recommends     libguestfs-tools     python3-guestfs     linux-image-virtual
# Builds the appliance now rather than at the first use.
RUN update-guestfs-appliance || true
ENV LIBGUESTFS_BACKEND=direct

WORKDIR /app/src

COPY . .
