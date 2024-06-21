cp /root/shared_ssh/* /root/.ssh/
chmod 644 /root/.ssh/config
chmod 400 /root/.ssh/id_*
eval "$(ssh-agent -s)"
ssh-add /root/.ssh/id_*
