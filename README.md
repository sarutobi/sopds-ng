# SimpleOPDS Catalog NG (New Generation)

Based on SimpleOPDS Catalog by Dmitry V. Shelepnev
Author: Valery A. Ilychev
Version 1.0.0

[Russian version: README_RUS.md](README_RUS.md)
[Deployment documentation](docs/deploy.md) | [Migration documentation](docs/migration.md)

This is a fork of the [SimpleOPDS Catalog](https://github.com/mitshel/sopds) project by Dmitry Shelepnev. The original project has been inactive since April 2019.
![Example](images/sopds-ng-1.jpg)

The following changes have been made relative to the original project:

1. Tested and optimized for PostgreSQL. While Django supports other databases and SOPDS-NG may work with MySQL or SQLite, these require additional testing.
2. Base layout redesign.
3. Added support for running SOPDS-NG in Docker/Podman containers.
4. Fixed identified bugs and integrated changes from third-party contributors via pull requests to the original project.
5. Uses gunicorn as the WSGI server; the built-in Django development server is not used.
6. Reorganized source code structure for better maintainability.
7. Integrated modern development tools (uv, mypy, etc.).

All changes are developed in the `dev` branch of this repository.

#### Technical Stack

- Python 3.13
- Django 5.2
- PostgreSQL 17
- gunicorn
- docker

---

## Docker Image

Ready-to-use multi-arch images (amd64/arm64) are published at [ghcr.io/sarutobi/sopds-ng](https://github.com/sarutobi/sopds-ng/pkgs/container/sopds-ng):

- `ghcr.io/sarutobi/sopds-ng:latest` — latest version from master
- `ghcr.io/sarutobi/sopds-ng:master` — master branch

---

## Quick Start

See the [Quick Start Guide](docs/quickstart.md) for instructions.
