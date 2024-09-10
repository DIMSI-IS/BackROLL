cp /root/shared_ssh/* /root/.ssh/

# Ensure proper file permissions

# From ssh-keygen behavior
chmod 600 /root/.ssh/*
chmod 644 /root/.ssh/*.pub

# From OpenSSH man pages
chmod 644 /root/.ssh/config
