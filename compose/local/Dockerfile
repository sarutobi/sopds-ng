# Project dev image build

FROM python:3.13-slim

# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
#Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Requirements file
ARG REQUIREMENTS="local.txt"

WORKDIR /sopds-ng

RUN apt update && apt install -y gettext
COPY . .
RUN pip install --upgrade pip
RUN pip install -r requirements/$REQUIREMENTS
RUN useradd sopds-ng && chown sopds-ng:sopds-ng -R /sopds-ng 

USER sopds-ng

ENV USER="sopds-ng"

EXPOSE 8008
CMD ["./bootstrap.sh"]
