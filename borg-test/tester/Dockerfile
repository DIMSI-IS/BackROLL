FROM ubuntu:20.04

WORKDIR /app

RUN apt update -y && apt install -y \
    borgbackup \
    python3

COPY build/* ./build/
COPY src/* ./src/

RUN mkdir tmp \
&& python3 src/main.py '12' 'CHDN' 3 'build/' 'TestsFile' \
&& cat build/TestsFile.json > tmp/test_plan.json

CMD ["cat", "tmp/test_plan.json"]
