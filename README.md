#### SimpleOPDS Catalog NG (new generation) - Simple OPDS Catalog NP (new generation)
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

## Quick start (ready-made image)

Ready-made multi-arch images (amd64/arm64) are published at [ghcr.io/sarutobi/sopds-ng](https://github.com/sarutobi/sopds-ng/pkgs/container/sopds-ng):

- `ghcr.io/sarutobi/sopds-ng:latest` — latest version from master
- `ghcr.io/sarutobi/sopds-ng:master` — master branch
- `ghcr.io/sarutobi/sopds-ng:sha-xxxxx` — specific commit

```bash
# 1. Download docker-compose.yml and base.env
wget https://raw.githubusercontent.com/sarutobi/sopds-ng/master/docker-compose.yml
wget https://raw.githubusercontent.com/sarutobi/sopds-ng/master/base.env
cp base.env data/.env
# Configure SECRET_KEY in data/.env

# 2. Edit docker-compose.yml: replace build: with image:
#   image: ghcr.io/sarutobi/sopds-ng:latest

# 3. Start
docker compose up -d
```

---

### Bare-metal install (systemd)

1. Create a system user:
   ```bash
   sudo useradd -r sopds
   ```

2. Unpack the release archive:
   ```bash
   sudo tar -xzf release_*.tar.gz -C /opt/sopds-ng
   sudo chown -R sopds:sopds /opt/sopds-ng
   ```

3. Prepare the data directory:
   ```bash
   sudo mkdir -p /opt/sopds-ng/data && sudo chown sopds:sopds /opt/sopds-ng/data
   sudo cp base.env /opt/sopds-ng/data/.env   # then edit .env
   ```

4. Install and start the systemd service:
   ```bash
   sudo cp etc/systemd/system/sopds.service /etc/systemd/system/sopds.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now sopds
   ```

5. Verify the installation:
   ```bash
   /opt/sopds-ng/check-systemd.sh
   ```

Detailed instructions are available in [docs/deploy.md](docs/deploy.md).
