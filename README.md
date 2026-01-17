#### SimpleOPDS Catalog NG (new generation)
#### Based on SimpleOPDS Catalog by Dmitry V.Shelepnev
#### Author: Valery A. Ilychev
#### Version 0.47-devel

[Инструкция на русском языке: README_RUS.md](README_RUS.md)

Based on source code [SimpleOPDS Catalog](https://github.com/mitshel/sopds) by Dmitry V.Shelepnev.
![Example 1](images/sopds-ng-1.jpg)

Notable changes:

1. Database engine is postgresql only. Django supports other DB engines and probably sqlite or mysql can be used, but compatibility is not tested.

2. Base page layouts has been changed (work in progress).

3. Can be run in docker/podman containers.

Currently applied next changes:

1. Bug fixes, apply pathes to origianl project by contributors.

2. Now project works under wsgi-server gunicorn. Embedded in Django development server is out of work.

3. Project files layout has been modified.

4. Project management tools has been changed to actual (uv, mypy etc.)

All changes are present in dev branch in current repository

#### Technical stack

- Python 3.19

- Django 5.1

- PostgreSQL 17

- gunicorn

- docker

