snapcraft clean &&\
snapcraft pack &&\
# Too brutal : data loss.
# snap remove backroll &&\
snap install --devmode backroll_0.1_amd64.snap &&\
snap logs -n=100 backroll
