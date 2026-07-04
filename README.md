#### SimpleOPDS Catalog NG (new generation) — Простой OPDS Каталог НП (новое поколение)
#### Based on SimpleOPDS Catalog by Dmitry V.Shelepnev
#### Author: Valery A. Ilychev
#### Version 1.0.0RC1

[Russian README: README_RUS.md](README_RUS.md)
[Deploy documentation](docs/deploy.md) |
[Migration documentation](docs/migration.md)

This is a fork of the [SimpleOPDS Catalog](https://github.com/mitshel/sopds) project by Dmitry Shelepnev. The original project has been inactive since April 2019.
![Example](images/sopds-ng-1.jpg)

The following changes are planned relative to the original project:

1. PostgreSQL-only database support. Django supports other database engines and SOPDS-NG will likely work with mysql and sqlite as well, but this requires additional testing.

2. Base page layout redesign (work in progress).

3. Ability to run SOPDS-NG in a docker/podman container (work in progress).

The following changes have been applied so far:

1. Identified bugs have been fixed; changes from third-party contributors' pull requests for the original project have been applied.

2. The application now uses the gunicorn wsgi server. The built-in django server is not used.

3. Source code structure has been reorganized for easier management.

4. Modern tooling is used (uv, mypy, etc.)

All changes are being made in the dev branch of this repository.

#### Technical stack
#### Technical stack
- Python 3.13

- Django 5.2

- PostgreSQL 17

- gunicorn

- docker

---

#### Развёртывание

See [Deploy documentation](docs/deploy.md), including `DATA_ROOT` configuration for unified paths.
