FROM python:3.9-slim

ARG USERNAME=flask
ARG UID=1000

RUN apt-get update && apt-get install -qqy \
    sudo 

RUN groupadd -g $UID $USERNAME && \
    useradd -u $UID -g $UID -m $USERNAME -s /bin/bash && \
    usermod -aG sudo $USERNAME && \
    echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME 

# you have to copy the requirements file first, if you want to install dependencies in the container, before it starts
# mounts happen after the container was succesfully built
WORKDIR /app
COPY ../docs/requirements.txt .
RUN pip install -r requirements.txt