FROM lscr.io/linuxserver/openssh-server:latest

RUN sed -i 's/AllowTcpForwarding no/AllowTcpForwarding yes/g' /etc/ssh/sshd_config &&\
    sed -i 's/#PermitTunnel no/PermitTunnel yes/g' /etc/ssh/sshd_config

# Trying to keep the same fingerprint across container deletion and creation.
#VOLUME /etc/ssh