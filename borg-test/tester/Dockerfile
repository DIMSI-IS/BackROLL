FROM ubuntu:20.04

WORKDIR /app

RUN apt update -y && apt install -y \
    borgbackup \
    python3

COPY build/* ./build/
COPY src/* ./src/

RUN mkdir tmp \
#&& echo 'Test' > tmp/test.txt \
#&& str="Hello World!" \
#&& len=${#str} \
#&& for (i = 0; i < len; i++); do char"${str:i:1}";echo "$i: $char" >> tmp/test.txt; done
&& python3 src/main.py '12' 'CHDN' 3 'build/' 'TestsFile.json' \
&& cat build/TestsFile.json > tmp/test_plan.json

CMD ["cat", "tmp/test_plan.json"]
#CMD ["cat", "tmp/test.txt"]