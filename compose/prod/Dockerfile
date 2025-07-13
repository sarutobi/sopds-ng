# Project image build
FROM python:3.13-slim

# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
#Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

ENV PGSERVICEFILE=/sopds/.pg_service
ENV PGPASSFILE=/sopds/.pgpass

# Requirements file
ARG REQUIREMENTS="requirements/prod.txt"

WORKDIR /sopds

COPY . /sopds/

RUN useradd --create-home sopds \
&& chown sopds:sopds -R /sopds \
&& pip install --upgrade pip \
&& pip install --no-cache-dir -r $REQUIREMENTS 

USER sopds

ENV USER="sopds"

EXPOSE 8008
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8008"]
