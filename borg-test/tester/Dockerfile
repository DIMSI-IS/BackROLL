FROM ubuntu:20.04

WORKDIR /app

RUN apt update -y && apt install -y \
    borgbackup \
    python3

COPY build/* ./build/

RUN mkdir tmp \
&& python3 build/test_plan.py \
#&& ls > tmp/ls.json \
#&& ls ./* > tmp/ls2.json
&& cat build/TestsFile.json > tmp/test_plan.json

CMD ["cat", "tmp/test_plan.json"]
#CMD ["cat", "tmp/ls.json"]
#CMD ["cat", "tmp/ls2.json"]
