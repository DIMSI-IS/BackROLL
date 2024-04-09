FROM ubuntu:20.04

WORKDIR /app

RUN apt update -y && apt install -y \
    borgbackup \
    python3

COPY build/* ./build/

RUN mkdir tmp \
&& python3 build/test_plan.py > tmp/test_plan.csv

CMD ["cat", "tmp/test_plan.csv"]





#RUN mkdir restore \
#&& mkdir important_file \
#&& echo "This is an important file" > important_file/text.txt \
#&& borg init -e=none /app/borgrepo
