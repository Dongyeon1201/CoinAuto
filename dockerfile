FROM python:3.8

WORKDIR /usr/src/app
RUN mkdir ./logs

COPY ./requirements.txt ./
COPY ./coin_auto.py ./
COPY ./util.py ./

RUN apt update && apt -y upgrade && apt -y install python3-pip
RUN pip3 install --upgrade pip
RUN pip3 uninstall --yes jwt
RUN pip3 install -r requirements.txt
RUN pip3 install PyJWT