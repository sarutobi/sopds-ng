# Project dev image build

FROM python:3.13-slim

# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
#Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

ENV PGSERVICEFILE=/home/sopds/.pg_service.conf
ENV PGPASSFILE=/home/sopds/.pgpass

# Requirements file
ARG REQUIREMENTS="local.txt"

WORKDIR /sopds

RUN apt update && apt install -y gettext
COPY ./requirements /sopds/
#COPY .pgpass /.pgpass
#COPY .pg_service.conf /.pg_service.conf

RUN useradd --create-home sopds \
&& chown sopds:sopds -R /sopds \
#&& mv /.pg* /home/sopds/ && chmod 0600 /home/sopds/.pgpass && chown -R sopds:sopds /home/sopds \
&& pip install --upgrade pip \
&& pip install --no-cache-dir -r $REQUIREMENTS 

USER sopds

ENV USER="sopds"


EXPOSE 8008
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8008"]
